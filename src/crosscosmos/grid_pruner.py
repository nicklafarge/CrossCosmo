"""
Cell constraint solver for crossword grids.

This module implements an algorithm to identify valid letters for each cell
in a crossword grid based on a word database, using constraint propagation
to iteratively refine possibilities.
"""

import logging
from collections import deque
from typing import overload

import polars as pl

from crosscosmos import constants, query, refine, scoring
from crosscosmos.enums import CellStatus, WordDirection
from crosscosmos.grid import Grid, Entry, Cell
from crosscosmos.wordlists import LaFargeWord
from crosscosmos.corpus import WordMap

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class GridPruningSolver:
    """Identifies valid letters for each crossword cell using constraint propagation.

    Uses an iterative refinement approach where database queries for each entry
    constrain the possible letters in cells, which then triggers re-evaluation
    of crossing entries until convergence.

    Parameters
    ----------
    grid : Grid
        The crossword grid to solve
    word_df : pl.DataFrame
        DataFrame containing valid words with 'word' and 'score' columns
    min_score : float
        Minimum word quality score (0-100)
    """

    def __init__(
        self,
        grid: Grid,
        word_df: pl.DataFrame,
        min_score: float = 20,
    ):
        self.grid = grid
        self.word_df = word_df
        self.min_score = min_score

        self.word_map = WordMap(self.word_df)

        self.cell_letters: dict[tuple[int, int], set[str]] = {}

        # Track which entries have been processed
        self.processed_entries = set()

        # Queue of entries to process
        self.entry_queue = deque()

        # Cache entries for others to use
        self.entry_cache: dict[str, pl.DataFrame] = {}

        # Initialize cell possibilities (A-Z for non-black cells)
        self.reset_possibilities()

        # Entries to requeue
        self.requeue_entries: set[str] = set()


    @overload
    def possible_letters(self, x: int, y: int) -> set[str]: ...

    @overload
    def possible_letters(self, cell: Cell) -> set[str]: ...

    def possible_letters(self, cell_or_x: int | Cell, y: int | None = None) -> set[str]:
        """ Get the set of possible letters for a given Cell, or (x,y) location in the grid
        """
        if isinstance(cell_or_x, Cell):
            return self.cell_letters[(cell_or_x.x, cell_or_x.y)]
        elif isinstance(cell_or_x, int) and y is not None:
            return self.cell_letters[(cell_or_x, y)]
        else:
            raise TypeError("Invalid arguments: expected (int, int) or Cell")

    @overload
    def set_possible_letters(self, x: int, y: int, letters: set[str]) -> None: ...

    @overload
    def set_possible_letters(self, cell: Cell, letters: set[str]) -> None: ...

    def set_possible_letters(self, cell_or_x: int | Cell, letters_or_y: int | set[str], letters: set[str] | None = None) -> None:
        """ Sets the set of possible letters for a given Cell, or (x,y) location in the grid
        """
        if isinstance(cell_or_x, Cell) and isinstance(letters_or_y, set):
            self.cell_letters[(cell_or_x.x, cell_or_x.y)] = letters_or_y
        elif isinstance(cell_or_x, int) and isinstance(isinstance(letters_or_y, int), int) and letters is not None:
            self.cell_letters[(cell_or_x, letters_or_y)] = letters
        else:
            raise TypeError("Invalid arguments: expected (int, int, str) or (Cell, str)")

    def get_valid_entries(self, entry: Entry | str, from_cache: bool = False, update_cache: bool = True) -> pl.DataFrame | None:
        """Query database for words matching entry pattern and constraints.

        Parameters
        ----------
        entry : Entry or str
            The entry to find valid words for
        from_cache : bool
            If true, initialize it from the cache
        update_cache : bool
            If true, store the result of the
        Returns
        -------
        pl.DataFrame or None
            List of valid words from database
        """
        if from_cache and update_cache:
            raise ValueError("Cannot specify both 'from_cache' and 'update_cache'")

        if isinstance(entry, str):
            entry = self.grid.get_entry(entry)
        # Build pattern from current cell possibilities and constraints
        fixed_letters = {}
        for i, cell in enumerate(entry):
            possible_letters = self.possible_letters(cell)
            if len(possible_letters) >= 0:
                fixed_letters[i] = possible_letters
            else:
                # No possibilities - no valid words can exist
                return None

        if from_cache:
            if entry.entry_id not in self.entry_cache:
                return None
            df = self.entry_cache[entry.entry_id]
        else:
            df = self.word_df
        entries = refine(df, length=len(entry), fixed_letters=fixed_letters)

        if entry.entry_id not in self.entry_cache or update_cache:
            self.entry_cache[entry.entry_id] = entries
        return entries

    def update_entry_cache(self, entry: Entry | str | None = None) -> None:
        """
        Updates the entry cache for a specific entry, or for the entire grid.

        Parameters
        ----------
        entry : Entry or str, optional
            Specific entry to update the cache. If not specified, the cache is updated for every entry in the grid

        """
        if not entry:
            entries = self.grid.entries()
        elif isinstance(entry, str):
            entries = [self.grid.get_entry(entry)]
        else:
            entries = [entry]

        for e in entries:
            valid_entries = self.get_valid_entries(e)
            self.update_entry_possibilities(e, valid_entries)

    def update_entry_possibilities(self, entry: Entry, valid_entries: pl.DataFrame | None = None) -> list[Entry]:
        """Update possible letters for cells based on valid words.

        Parameters
        ----------
        entry : Entry
            The entry whose cells to update
        valid_entries : pl.DataFrame or None
            Valid words for this entry

        Returns
        -------
        list[Entry]
            Crossing entries that need reprocessing due to changes
        """
        entries_to_requeue = []
        logger.info(f"Updating possibilities for {entry.entry_id}...")

        if valid_entries is None:
            valid_entries = self.get_valid_entries(entry)

        if valid_entries is None or valid_entries.is_empty():
            # No valid words found - but don't mark cells as impossible yet
            # They might still be valid through other crossing words
            logger.warning(f"No valid words found for entry {entry.entry_id} with current constraints")
            return []

            # Still need to check crossings as they might provide more constraints
            for cell in entry:
                if cell.status != CellStatus.EMPTY:
                    continue
                cross_dir = WordDirection.flip(entry.direction)
                crossing_entry = self.grid.cell_to_entry(cell.x, cell.y, cross_dir)
                if crossing_entry and crossing_entry.entry_id not in self.processed_entries:
                    entries_to_requeue.append(crossing_entry)
            return entries_to_requeue

        # For each position in the entry
        for i, cell in enumerate(entry):
            if cell.status != CellStatus.EMPTY:
                logger.debug(f"({cell.x},{cell.y}): Skipping ({cell.status})")
                continue  # Skip fixed cells

            # Find all letters that appear at this position in valid words
            valid_letters_at_position = {word[i] for word in valid_entries["word"]}

            # Intersect with current possibilities
            old_possibilities = self.possible_letters(cell).copy()
            intersection = self.possible_letters(cell) & valid_letters_at_position

            self.set_possible_letters(cell, intersection)
            new_possibilities = self.possible_letters(cell)

            cross_dir = WordDirection.flip(entry.direction)
            crossing_entry = self.grid.cell_to_entry(cell.x, cell.y, cross_dir)

            logger.debug(f"({cell.x},{cell.y}): Checking possibilities (crosser={crossing_entry.entry_id})")
            # If possibilities changed, queue crossing entry
            if old_possibilities == new_possibilities:
                pass
                # logger.debug(f"  No change.")
            else:
                # Get crossing entry
                logger.info(
                    f"  Reduced possibilities from {len(old_possibilities)} to {len(new_possibilities)}."
                )
                before_letters = ''.join(sorted(old_possibilities))
                after_letters = ''.join(sorted(new_possibilities))
                removed_letters = ''.join(sorted(c for c in old_possibilities if c not in new_possibilities))
                logger.debug(f"    * Before:  {before_letters}")
                logger.debug(f"    * After:   {after_letters}")
                logger.debug(f"    * Removed: {removed_letters}")


                cross_dir = WordDirection.flip(entry.direction)
                crossing_entry = self.grid.cell_to_entry(cell.x, cell.y, cross_dir)

                if not crossing_entry:
                    raise RuntimeError(f"Failed to find crossing entry for {cell}")

                # Only requeue if not already processed this iteration
                entry_added = self._add_to_requeue_list(entry, entries_to_requeue)
                crosser_added = self._add_to_requeue_list(crossing_entry, entries_to_requeue)

                if entry_added:
                    logger.info(f"  {entry.entry_id} (current entry) added back into the queue")
                if crosser_added:
                    logger.info(f"  {crossing_entry.entry_id} (crosser) added back into the queue")
                if entry_added or crosser_added:
                    logger.info(f" Updated entries to re-queue: {','.join(x.entry_id for x in entries_to_requeue)}")
        if entries_to_requeue:
            entries_added = ','.join(sorted(x.entry_id for x in entries_to_requeue))
            logger.debug(
                f"Adding {len(entries_to_requeue)} entries back to queue: {entries_added}\n"
            )
        else:
            logger.debug("No entries added back to queue")
        return entries_to_requeue

    def _add_to_requeue_list(self, entry: Entry, entries_to_requeue: list[Entry]) -> bool:
        """ Add a given entry into a re-queue list, checking if it is already there, and if this
        entry has been evaluated yet this iteration

        Parameters
        ----------
        entry : Entry
            Entry to re-add
        entries_to_requeue : list[Entry]
            List of entries to re-queue

        Returns
        -------
        bool
            Whether the entry was re-queued.
        """
        # Only requeue if not already processed this iteration
        # if entry.entry_id not in self.processed_entries:
        #     logger.debug(f"  {entry.entry_id} not added (not yet processed this iteration)")
        #     return False

        if entry in entries_to_requeue:
            logger.debug(f"  {entry.entry_id} not added (already in re-queue list)")
            return False

        entries_to_requeue.append(entry)
        return True


    def solve(self, **kwargs) -> dict:
        """Run constraint propagation from scratch to identify valid letters for each cell.
        """
        # Initialize queue with all entries
        all_entries = []
        for start in self.grid.h_starts.rows(named=True):
            entry = self.grid.cell_to_entry(start["x"], start["y"], WordDirection.HORIZONTAL)

            if entry and not entry.is_complete:  # Check for None
                all_entries.append(entry)

        for start in self.grid.v_starts.rows(named=True):
            entry = self.grid.cell_to_entry(start["x"], start["y"], WordDirection.VERTICAL)
            if entry and not entry.is_complete:   # Check for None
                all_entries.append(entry)

        self.entry_queue = deque(all_entries)
        logger.info(f"Initialized entry queue: {','.join(sorted(x.entry_id for x in self.entry_queue))}")
        return self.prune_grid(**kwargs)

    def re_solve(self, **kwargs) -> dict:
        """ Re-solves the grid only using the entries that already exist in the queue
        """

        # Reset the re-queued entries
        self.reset_possibilities()

        if len(self.requeue_entries) == 0:
            logger.info("Re-solve queue empty: Nothing to solve")
            return {}

        for entry_id in self.requeue_entries:
            # Reset the entry cache
            if entry_id in self.entry_cache:
                self.entry_cache.pop(entry_id)

            # Get the entry
            entry = self.grid.get_entry(entry_id)

            # Reset the cell letters for the cells in all entries
            for c in self.grid.get_entry(entry_id):
                self.reset_letters_for_cell(c)

            self.add_to_queue(entry)

        self.requeue_entries = set()
        logger.info(f"Re-solving for entries: {','.join(sorted(x.entry_id for x in self.entry_queue))}")
        return self.prune_grid(**kwargs)


    # def update_from_entries(self, *entry_ids, **kwargs):
    #     logger.info(f"Updating possibilities given new values for {','.join([e.entry_id for e in entry_ids])}")
    #     self.entry_queue = deque(entry_ids)
    #     return self.prune_grid(**kwargs)

    # def update_from_cell(self, cell: Cell, **kwargs):
    #     for word_dir in [WordDirection.HORIZONTAL, WordDirection.VERTICAL]:
    #         entry = self.grid.cell_to_entry(cell.x, cell.y, word_dir)
    #         for c in entry:
    #             self.cell_letters[(c.x, c.y)] = set(constants.ALPHABET) if c.status==CellStatus.EMPTY else c.value
    #         self.update_entry_possibilities(entry, **kwargs)

    def prune_grid(self, max_iterations: int = 100) -> dict:
        """Run constraint propagation to identify valid letters for each cell.

        Parameters
        ----------
        max_iterations : int
            Maximum refinement iterations (prevents infinite loops)

        Returns
        -------
        dict
            Statistics about the solving process and results
        """
        logger.info(f"Beginning solver (max_iterations={max_iterations})")

        iteration = 0
        total_queries = 0
        solution_exists = True
        while solution_exists and self.entry_queue and iteration < max_iterations:
            iteration += 1
            current_queue_size = len(self.entry_queue)
            logger.info(f"{'='*50}")
            logger.debug(f"Iteration {iteration}: Processing {current_queue_size} entries")
            logger.info(f"{'='*50}")
            logger.info(f"Current queue: {','.join(x.entry_id for x in self.entry_queue)}")

            # Clear processed set for new iteration
            self.processed_entries.clear()

            # Process all entries currently in queue
            for _ in range(current_queue_size):
                entry = self.entry_queue.popleft()
                entry_id = entry.entry_id
                logger.info(f"{entry_id}: Beginning pruning")

                if entry_id in self.processed_entries:
                    logger.info("Already processed. Skipping.")
                    continue  # Skip if already processed this iteration

                # Query for valid words
                valid_words_df = self.get_valid_entries(entry)
                total_queries += 1

                if valid_words_df is None or valid_words_df.is_empty():
                    logger.error(f"No valid words found for {entry_id}: {entry}")
                    solution_exists = False
                    break

                logger.info(f"{len(valid_words_df)} valid entries found")

                # Update cells and get entries to re-queue
                entries_to_requeue = self.update_entry_possibilities(entry, valid_words_df)
                self.add_to_queue(entries_to_requeue)
                self.processed_entries.add(entry_id)

        if not solution_exists:
            for c in self.grid.grid.flatten():
                if c.status==CellStatus.EMPTY:
                    self.set_possible_letters(c, set())

        # Compute statistics
        stats = self._compute_statistics()
        stats.update({
            "iterations": iteration,
            "total_queries": total_queries,
            "converged": len(self.entry_queue) == 0
        })

        # Update the cache
        for entry in self.grid.entries_df()["entry_id"]:
            self.update_entry_cache(entry)

        return stats

    def _compute_statistics(self) -> dict:
        """Compute statistics about cell possibilities."""
        total_cells = 0
        constrained_cells = 0
        fully_determined = 0
        impossible_cells = 0

        for cell in self.grid.grid.flatten():
            if cell.status == CellStatus.BLACK:
                continue

            total_cells += 1
            num_possibilities = len(self.possible_letters(cell))

            if num_possibilities == 0:
                impossible_cells += 1
            elif num_possibilities == 1:
                fully_determined += 1
            elif num_possibilities < 26:
                constrained_cells += 1

        return {
            "total_cells": total_cells,
            "fully_determined": fully_determined,
            "constrained_cells": constrained_cells,
            "impossible_cells": impossible_cells,
            "avg_possibilities": sum(
                len(self.possible_letters(c)) for c in self.grid.grid.flatten()
                if c.status != CellStatus.BLACK
            ) / max(total_cells, 1)
        }

    def add_to_queue(self, entries: Entry | str | list[Entry] | list[str]):
        """ Add entry (or entries) to the queue

        Parameters
        ----------
        entries : str, Entry, list[str], list[Entry]
            Entry (or entries) to add to the queue
        """

        # Ensure it's a list
        if not isinstance(entries, list):
            entries = [entries]

        # Parse any entry ID strings into entries
        for i, e in enumerate(entries):
            if isinstance(e, str):
                entries[i] = self.grid.get_entry(e)

        # Add to queue
        self.entry_queue.extend(entries)

    def add_to_requeue(self, entry_id: str):
        """ Adds an entry id to the list of entries to re-queue
        """
        if entry_id not in self.requeue_entries:
            logger.info(f"Re-queueing {entry_id}")
            self.requeue_entries.add(entry_id)
        else:
            logger.info(f"{entry_id} already in the re-queue")


    def print_possibilities_grid(self):
        """Print grid showing number of possibilities for each cell."""
        print("\nCell Possibilities Count:")
        print("-" * (self.grid.col_count * 4))

        for i in range(self.grid.row_count):
            row_str = []
            for j in range(self.grid.col_count):
                cell = self.grid[i, j]
                if cell.status == CellStatus.BLACK:
                    row_str.append(" ■ ")
                elif cell.status in (CellStatus.SET, CellStatus.LOCKED):
                    row_str.append(f" {cell.value} ")
                else:
                    count = len(self.possible_letters(cell))
                    if count == 0:
                        row_str.append(" X ")
                    elif count < 10:
                        row_str.append(f" {count} ")
                    else:
                        row_str.append(f"{count} ")
            print(" ".join(row_str))

    def reset_possibilities(self):
        """Initialize possible letters for each cell."""
        self.cell_letters = {}
        self.processed_entries = set()
        self.entry_queue = deque()
        self.entry_cache = {}
        # self.requeue_entries = set()

        for cell in self.grid.grid.flatten():
            self.reset_letters_for_cell(cell)


    def reset_letters_for_cell(self, cell: Cell):
        """ Resets the cached valid letters set for a given cell
        """
        if cell.status == CellStatus.BLACK:
            # Nothing is valid for a black cell
            self.cell_letters[(cell.x, cell.y)] = set()
        elif cell.status in (CellStatus.SET, CellStatus.LOCKED):
            # Fixed cells only have their current value as possibility
            self.cell_letters[(cell.x, cell.y)] = {cell.value}
        else:
            # Empty cells can be any letter initially
            self.cell_letters[(cell.x, cell.y)] = set(constants.ALPHABET)

    def get_scored_words(self, entry_id: str | Entry, **kwargs):
        scoring_settings = {
            "use_quality_scores": True,
            "frequency_weight": 0.2,
            "quality_weight": 0.2,
            "scarcity_weight": 0.6,
            "scarcity_penalty_power": 2.0
        }

        main_entry = self.grid.get_entry(entry_id)
        main_valid_entries = self.get_valid_entries(main_entry.entry_id, **kwargs)

        position_scores = {}
        for i, c in enumerate(main_entry):
            if c.status != CellStatus.EMPTY:
                position_scores[i] = pl.DataFrame({
                    "letter": c.value, "score": 100, "count1": 1, "count2": 1, "excluded1": 0, "excluded2": 0
                })
                continue


            x_entry_id = c.vertical_entry_id if main_entry.direction == WordDirection.HORIZONTAL else c.horizontal_entry_id
            x_entry_index = c.vertical_index if main_entry.direction == WordDirection.HORIZONTAL else c.horizontal_index
            x_valid_entries = self.get_valid_entries(x_entry_id, **kwargs)
            x_distribution = scoring.get_letter_distribution_at_position(x_valid_entries, position=x_entry_index)

            main_distribution = scoring.get_letter_distribution_at_position(main_valid_entries, position=i)

            score = scoring.compute_letter_scores(main_distribution, x_distribution, **scoring_settings)
            position_scores[i] = score

        return scoring.apply_multi_position_scores(main_valid_entries, position_scores, aggregation="mean")

if __name__ == "__main__":
    """Test the constraint solver with a simple grid."""
    logging.basicConfig(level=logging.DEBUG)

    print("Testing Cell Constraint Solver")
    print("=" * 50)

    # Load word database into dataframe
    print("\nLoading word database...")
    min_score = 40  # Lower threshold for more words
    word_df = query.Query(db=LaFargeWord, default=False, limit=None).min_score(min_score).df()
    print(f"Loaded {len(word_df)} words with score >= {min_score}")

    # Create a simple 5x5 test grid
    grid = Grid((5, 5))

    # Set some black squares to create a pattern
    grid[0, 4] = None
    grid[1, 4] = None
    grid[4, 0] = None
    grid[4, 1] = None

    # Set a few letters as constraints for testing
    # This creates "T??G" as 1D entry (column 0)
    grid[0, 0] = "T"
    grid[3, 0] = "G"
    grid[2, 1] = "Q"
    # grid[3, 2] = "Q"
    grid.update_length_and_head_data()

    # grid = Grid((3, 3))
    # grid[0, 1].update("Z")  # Black square
    # grid[1,0].update("Q")  # Black square
    # grid[2, 1].update("O")  # Black square

    print("Initial Grid:")
    grid.print()


    # Initialize solver
    solver = GridPruningSolver(
        grid=grid,
        word_df=word_df,
        min_score=min_score
    )

    # Run constraint propagation
    print("\nRunning constraint propagation...")
    stats = solver.solve()
    solver.print_possibilities_grid()

    print("Updating from cell")
    grid[3, 2] = "P"
    solver.update_from_cell(grid[3,2])
    solver.print_possibilities_grid()
