"""
Cell constraint solver for crossword grids.

This module implements an algorithm to identify valid letters for each cell
in a crossword grid based on a word database, using constraint propagation
to iteratively refine possibilities.
"""

import logging
from collections import deque

import polars as pl

from crosscosmos import constants, query, refine
from crosscosmos.enums import CellStatus, WordDirection
from crosscosmos.grid import Grid, Entry
from crosscosmos.wordlists import LaFargeWord

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        min_score: float = 20
    ):
        self.grid = grid
        self.word_df = word_df
        self.min_score = min_score

        self.cell_letters: dict[tuple[int, int], set[str]] = {}

        # Track which entries have been processed
        self.processed_entries = set()

        # Queue of entries to process
        self.entry_queue = deque()

        # Initialize cell possibilities (A-Z for non-black cells)
        self._initialize_cell_possibilities()

    def get_valid_words(self, entry: Entry) -> pl.DataFrame | None:
        """Query database for words matching entry pattern and constraints.

        Parameters
        ----------
        entry : Entry
            The entry to find valid words for

        Returns
        -------
        pl.DataFrame or None
            List of valid words from database
        """
        # Build pattern from current cell possibilities and constraints
        fixed_letters = {}
        for i, cell in enumerate(entry):
            if len(cell.possible_letters) >= 0:
                fixed_letters[i] = cell.possible_letters
            else:
                # No possibilities - no valid words can exist
                return None

        return refine(self.word_df, length=len(entry), fixed_letters=fixed_letters)

    def _update_cell_possibilities(self, entry: Entry, valid_words: list[str]) -> list[Entry]:
        """Update possible letters for cells based on valid words.

        Parameters
        ----------
        entry : Entry
            The entry whose cells to update
        valid_words : list[str]
            Valid words for this entry

        Returns
        -------
        list[Entry]
            Crossing entries that need reprocessing due to changes
        """
        entries_to_requeue = []
        logger.info(f"Updating possibilities...")

        if not valid_words:
            # No valid words found - but don't mark cells as impossible yet
            # They might still be valid through other crossing words
            logger.warning(f"No valid words found for entry {entry.entry_id} with current constraints")
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
            valid_letters_at_position = {word[i] for word in valid_words}

            # Intersect with current possibilities
            old_possibilities = cell.possible_letters.copy()
            cell.possible_letters &= valid_letters_at_position

            cross_dir = WordDirection.flip(entry.direction)
            crossing_entry = self.grid.cell_to_entry(cell.x, cell.y, cross_dir)

            logger.info(f"({cell.x},{cell.y}): Checking possibilities (crosser={crossing_entry.entry_id})")
            # If possibilities changed, queue crossing entry
            if old_possibilities == cell.possible_letters:
                logger.info(f"  No change.")
            else:
                # Get crossing entry
                logger.info(
                    f"  Reduced possibilities from {len(old_possibilities)} to {len(cell.possible_letters)}."
                )
                before_letters = ''.join(sorted(old_possibilities))
                after_letters = ''.join(sorted(cell.possible_letters))
                removed_letters = ''.join(sorted(c for c in old_possibilities if c not in cell.possible_letters))
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

        if entries_to_requeue:
            entries_added = ','.join(sorted(x.entry_id for x in entries_to_requeue))
            logger.info(
                f"Adding {len(entries_to_requeue)} entries back to queue ({entries_added})\n"
            )
        else:
            logger.info("No entries added back to queue")
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
        if entry.entry_id not in self.processed_entries:
            logger.debug(f"  {entry.entry_id} not added (not yet processed this iteration)")
            return False

        if entry in entries_to_requeue:
            logger.debug(f"  {entry.entry_id} not added (already in re-queue list)")
            return False

        entries_to_requeue.append(entry)
        return True


    def solve(self, max_iterations: int = 100) -> dict:
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

        iteration = 0
        total_queries = 0
        solution_exists = True
        while solution_exists and self.entry_queue and iteration < max_iterations:
            iteration += 1
            current_queue_size = len(self.entry_queue)
            logger.info(f"{'='*50}")
            logger.debug(f"Iteration {iteration}: Processing {current_queue_size} entries")
            logger.info(f"{'='*50}")

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
                valid_words_df = self.get_valid_words(entry)
                total_queries += 1

                if valid_words_df is None or valid_words_df.is_empty():
                    logger.error(f"No valid words found for {entry_id}: {entry}")
                    solution_exists = False
                    break

                logger.info(f"{len(valid_words_df)} valid entries found")

                # Update cells and get entries to requeue
                valid_words_list = valid_words_df["word"].to_list()
                entries_to_requeue = self._update_cell_possibilities(entry, valid_words_list)
                self.entry_queue.extend(entries_to_requeue)
                # # Add to queue
                # for e in entries_to_requeue:
                #     if e.entry_id in self.processed_entries:
                #         self.entry_queue.append(e)
                #     else:
                #         logger.info("")

                self.processed_entries.add(entry_id)

        if not solution_exists:
            for c in self.grid.grid.flatten():
                if c.status==CellStatus.EMPTY:
                    c.possible_letters = []

        # Compute statistics
        stats = self._compute_statistics()
        stats.update({
            "iterations": iteration,
            "total_queries": total_queries,
            "converged": len(self.entry_queue) == 0
        })

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
            num_possibilities = len(cell.possible_letters)

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
                len(c.possible_letters) for c in self.grid.grid.flatten()
                if c.status != CellStatus.BLACK
            ) / max(total_cells, 1)
        }

    def get_cell_possibilities(self, x: int, y: int) -> set[str]:
        """Get possible letters for a specific cell.

        Parameters
        ----------
        x : int
            Row coordinate
        y : int
            Column coordinate

        Returns
        -------
        set[str]
            Set of possible letters for the cell
        """
        return self.grid[x, y].possible_letters

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
                    count = len(cell.possible_letters)
                    if count == 0:
                        row_str.append(" X ")
                    elif count < 10:
                        row_str.append(f" {count} ")
                    else:
                        row_str.append(f"{count} ")
            print(" ".join(row_str))

    def _initialize_cell_possibilities(self):
        """Initialize possible letters for each cell."""
        for cell in self.grid.grid.flatten():
            if cell.status == CellStatus.BLACK:
                self.cell_letters[(cell.x, cell.y)] = set()
                cell.possible_letters = set()
            elif cell.status in (CellStatus.SET, CellStatus.LOCKED):
                # Fixed cells only have their current value as possibility
                cell.possible_letters = {cell.value}
            else:
                # Empty cells can be any letter initially
                cell.possible_letters = set(constants.ALPHABET)


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

    # Print results
    print(f"\nSolver Statistics:")
    print(f"  Iterations: {stats['iterations']}")
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Converged: {stats['converged']}")
    print(f"  Fully determined cells: {stats['fully_determined']}/{stats['total_cells']}")
    print(f"  Constrained cells: {stats['constrained_cells']}/{stats['total_cells']}")
    print(f"  Impossible cells: {stats['impossible_cells']}")
    print(f"  Average possibilities per cell: {stats['avg_possibilities']:.1f}")

    # Show possibilities grid
    solver.print_possibilities_grid()

    # Verify constraint propagation worked
    cell_1_0_poss = solver.get_cell_possibilities(1, 0)
    cell_2_0_poss = solver.get_cell_possibilities(2, 0)
