"""
Cell constraint solver for crossword grids.

This module implements an algorithm to identify valid letters for each cell
in a crossword grid based on a word database, using constraint propagation
to iteratively refine possibilities.
"""

from collections import deque
import logging

import polars as pl

from crosscosmos import refine, constants
from crosscosmos.enums import CellStatus, WordDirection
from crosscosmos.grid import Entry, Grid

logger = logging.getLogger(__name__)


class CellConstraintSolver:
    """Identifies valid letters for each crossword cell using constraint propagation.

    Uses an iterative refinement approach where database queries for each entry
    constrain the possible letters in cells, which then triggers re-evaluation
    of crossing entries until convergence.

    Parameters
    ----------
    grid : Grid
        The crossword grid to solve
    db : type
        Pony ORM database model (default: LaFargeWord)
    min_score : float
        Minimum word quality score (0-100)
    use_dataframe_cache : bool
        If True, loads entire database into memory for faster repeated queries
    """

    def __init__(self, grid: Grid, df: pl.DataFrame, min_score: int = 20, use_dataframe_cache: bool = True,  db=LaFargeWord):
        self.grid = grid
        self.db= db
        self._df_cache = df
        self.min_score = min_score
        self.use_dataframe_cache = use_dataframe_cache

        # Track which entries have been processed
        self.processed_entries = set()

        # Queue of entries to process
        self.entry_queue = deque()

        # Initialize cell possibilities (A-Z for non-black cells)
        self._initialize_cell_possibilities()

    def _initialize_cell_possibilities(self):
        """Initialize possible letters for each cell."""
        for cell in self.grid.grid.flatten():
            if cell.status == CellStatus.BLACK:
                cell.possible_letters = set()
            elif cell.status in (CellStatus.SET, CellStatus.LOCKED):
                # Fixed cells only have their current value as possibility
                cell.possible_letters = {cell.value}
            else:
                # Empty cells can be any letter initially
                cell.possible_letters = set(constants.ALPHABET)

    def _get_valid_words(self, entry: Entry) -> list[str]:
        """Query database for words matching entry pattern and constraints.

        Parameters
        ----------
        entry : Entry
            The entry to find valid words for

        Returns
        -------
        list[str]
            List of valid words from database
        """
        # Build pattern from current cell possibilities
        pattern_parts = []
        fixed_letters = {}

        for i, cell in enumerate(entry):
            if cell.status in (CellStatus.SET, CellStatus.LOCKED):
                # Fixed letter
                pattern_parts.append(cell.value)
                fixed_letters[i] = cell.value
            else:
                # Use wildcard
                pattern_parts.append("?")

        pattern = "".join(pattern_parts)

        if self.use_dataframe_cache:
            # Use cached dataframe with refiner
            result_df = refine(
                self._df_cache,
                match_term=pattern,
                fixed_letters=fixed_letters,
                length=len(entry),
                min_score=self.min_score,
                default=False,
            )
        else:
            # Query database directly
            q = query.Query(db=self.db, default=False)
            q.match(pattern).min_score(self.min_score).limit(None)

            # Apply fixed letter constraints
            for idx, letter in fixed_letters.items():
                q.fix_letters(idx, letter)

            result_df = q.df()

        return result_df["word"].to_list() if len(result_df) > 0 else []

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
        if not valid_words:
            # No valid words means this configuration is impossible
            logger.warning(f"No valid words for entry {entry.entry_id}")
            return []

        entries_to_requeue = []

        # For each position in the entry
        for i, cell in enumerate(entry):
            if cell.status in (CellStatus.SET, CellStatus.LOCKED):
                continue  # Skip fixed cells

            # Find all letters that appear at this position in valid words
            valid_letters_at_position = {word[i] for word in valid_words}

            # Intersect with current possibilities
            old_possibilities = cell.possible_letters.copy()
            cell.possible_letters &= valid_letters_at_position

            # If possibilities changed, queue crossing entry
            if old_possibilities != cell.possible_letters:
                # Get crossing entry
                cross_dir = WordDirection.flip(entry.direction)
                crossing_entry = self.grid.cell_to_entry(cell.x, cell.y, cross_dir)

                if crossing_entry:  # Check for None
                    crossing_id = crossing_entry.entry_id
                    # Only requeue if not already processed this iteration
                    if crossing_id not in self.processed_entries and crossing_entry not in entries_to_requeue:
                        entries_to_requeue.append(crossing_entry)

        return entries_to_requeue

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
        # Initialize queue with all entries
        all_entries = []
        for start in self.grid.h_starts.rows(named=True):
            entry = self.grid.cell_to_entry(start["x"], start["y"], WordDirection.HORIZONTAL)
            if entry:  # Check for None
                all_entries.append(entry)

        for start in self.grid.v_starts.rows(named=True):
            entry = self.grid.cell_to_entry(start["x"], start["y"], WordDirection.VERTICAL)
            if entry:  # Check for None
                all_entries.append(entry)

        self.entry_queue = deque(all_entries)

        iteration = 0
        total_queries = 0

        while self.entry_queue and iteration < max_iterations:
            iteration += 1
            current_queue_size = len(self.entry_queue)
            logger.debug(f"Iteration {iteration}: Processing {current_queue_size} entries")

            # Clear processed set for new iteration
            self.processed_entries.clear()

            # Process all entries currently in queue
            for _ in range(current_queue_size):
                entry = self.entry_queue.popleft()
                entry_id = entry.entry_id

                if entry_id in self.processed_entries:
                    continue  # Skip if already processed this iteration

                # Query for valid words
                valid_words = self._get_valid_words(entry)
                total_queries += 1

                # Update cells and get entries to requeue
                entries_to_requeue = self._update_cell_possibilities(entry, valid_words)

                # Add to queue
                for e in entries_to_requeue:
                    if e.entry_id not in self.processed_entries:
                        self.entry_queue.append(e)

                self.processed_entries.add(entry_id)

        # Compute statistics
        stats = self._compute_statistics()
        stats.update({"iterations": iteration, "total_queries": total_queries, "converged": len(self.entry_queue) == 0})

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
                len(c.possible_letters) for c in self.grid.grid.flatten() if c.status != CellStatus.BLACK
            )
            / max(total_cells, 1),
        }

    def cell_possibilities(self, x: int, y: int) -> set[str]:
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



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    """Test the constraint solver with a simple grid."""
    print("Testing Cell Constraint Solver")
    print("=" * 50)

    logger.info("Loading database into memory...")
    db = LaFargeWord
    min_score = 40
    _df = Query(db=db, default=False, limit=None).min_score(min_score).df()
    logger.info(f"Loaded {len(_df)} words into cache")

    test_grid = Grid((3, 3))
    test_grid[0, 1].update("B")  # Black square

    # Create a simple 5x5 test grid
    # test_grid = Grid((5, 5))

    # # Set some black squares to create a pattern
    # test_grid[0, 4].update(None)  # Black square
    # test_grid[1, 4].update(None)  # Black square
    # test_grid[4, 0].update(None)  # Black square
    # test_grid[4, 1].update(None)  # Black square
    #
    # # Set a few letters as constraints
    # test_grid[0, 0].update("T")
    # test_grid[2, 2].update("E")
    # test_grid[3, 0].update("G")
    # test_grid[3, 1].update("L")

    print("Initial Grid:")
    test_grid.print()

    # Initialize solver
    solver = CellConstraintSolver(
        grid=test_grid,
        df=_df,
        min_score=40,  # Use higher quality words
        use_dataframe_cache=True,
        db=LaFargeWord,
    )

    # Run constraint propagation
    print("\nRunning constraint propagation...")
    stats = solver.solve()

    # Print results
    print("\nSolver Statistics:")
    print(f"  Iterations: {stats['iterations']}")
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Converged: {stats['converged']}")
    print(f"  Fully determined cells: {stats['fully_determined']}/{stats['total_cells']}")
    print(f"  Constrained cells: {stats['constrained_cells']}/{stats['total_cells']}")
    print(f"  Impossible cells: {stats['impossible_cells']}")
    print(f"  Average possibilities per cell: {stats['avg_possibilities']:.1f}")

    # Show possibilities grid
    solver.print_possibilities_grid()

    # Show specific cell possibilities
    print("\nSample cell possibilities:")
    for i in range(3):
        for j in range(3):
            if test_grid[i, j].status not in (CellStatus.BLACK, CellStatus.SET, CellStatus.LOCKED):
                poss = solver.cell_possibilities(i, j)
                if len(poss) <= 10:
                    print(f"  Cell ({i},{j}): {sorted(poss)}")
                else:
                    print(f"  Cell ({i},{j}): {len(poss)} possibilities")
