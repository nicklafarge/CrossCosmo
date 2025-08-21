"""
Constraint-based crossword solver using python-constraint library.
Integrates with existing Grid and query infrastructure.
"""

import logging
from collections import defaultdict

from constraint import Problem, AllDifferentConstraint

from crosscosmos import query
from crosscosmos.grid import Grid, Entry
from crosscosmos.enums import WordDirection, CellStatus
from crosscosmos.wordlists.lafarge import LaFargeWord

logger = logging.getLogger(__name__)


class CrosswordConstraintSolver:
    """
    Constraint-based solver for crossword puzzles.

    Uses python-constraint to find valid solutions for partially filled grids,
    prioritizing words with higher scores from the database.
    """

    def __init__(
        self,
        grid: Grid,
        db=LaFargeWord,
        min_score: float = 0,
        max_candidates: int = 100
    ):
        """
        Initialize the constraint solver.

        Parameters
        ----------
        grid : Grid
            The crossword grid to solve
        db : Database model
            Word database to use (default: LaFargeWord)
        min_score : float
            Minimum word score to consider (default: 0)
        max_candidates : int
            Maximum candidate words per slot to consider (default: 100)
        """
        self.grid = grid
        self.db = db
        self.min_score = min_score
        self.max_candidates = max_candidates

        # Cache for word queries
        self._word_cache: dict[str, list[str]] = {}

        # Entry tracking
        self.entries: list[tuple[str, Entry]] = []
        self.entry_to_cells: dict[str, list[tuple[int, int]]] = {}
        self.cell_to_entries: dict[tuple[int, int], list[str]] = defaultdict(list)

    def solve(self, require_unique: bool = True) -> bool:
        """
        Solve the crossword puzzle.

        Parameters
        ----------
        require_unique : bool
            Whether to require all words to be unique

        Returns
        -------
        bool
            True if a solution was found, False otherwise
        """
        # Extract entries and build mappings
        self._extract_entries()

        # Create constraint problem
        problem = Problem()

        # Track which entries have candidates
        active_entries = []
        no_candidates = []

        # Add variables for each entry
        for entry_id, cell_list in self.entries:
            candidates = self._get_candidates(cell_list)
            if not candidates:
                no_candidates.append((entry_id, str(cell_list)))
                logger.warning(f"No candidates found for {entry_id}: {cell_list}")
            else:
                problem.addVariable(entry_id, candidates)
                active_entries.append(entry_id)
                logger.debug(f"{entry_id}: {len(candidates)} candidates")

        # Check if we have enough entries to solve
        if not active_entries:
            logger.error("No entries have valid candidates")
            return False

        if no_candidates:
            logger.error(f"Cannot solve - {len(no_candidates)} entries have no valid words")
            return False

        # Add intersection constraints (only for active entries)
        self._add_intersection_constraints(problem, active_entries)

        # Add uniqueness constraint if requested
        if require_unique and len(active_entries) > 1:
            problem.addConstraint(AllDifferentConstraint(), active_entries)

        # Find solution
        logger.info(f"Searching for solution with {len(active_entries)} entries...")
        solution = problem.getSolution()

        if solution:
            logger.info(f"Found solution with {len(solution)} entries")
            return self._apply_solution(solution)
        else:
            logger.info("No solution found")
            return False

    def _extract_entries(self) -> None:
        """Extract all word entries from the grid."""
        self.entries.clear()
        self.entry_to_cells.clear()
        self.cell_to_entries.clear()

        # Get all horizontal entries
        for row in self.grid.h_starts.iter_rows(named=True):
            x, y = row['x'], row['y']
            cell_list = self.grid.cell_to_entry(x, y, WordDirection.HORIZONTAL)
            if len(cell_list) >= 3:
                entry_id = f"{row['answer_number']}A"
                self._add_entry(entry_id, cell_list)

        # Get all vertical entries
        for row in self.grid.v_starts.iter_rows(named=True):
            x, y = row['x'], row['y']
            cell_list = self.grid.cell_to_entry(x, y, WordDirection.VERTICAL)
            if len(cell_list) >= 3:
                entry_id = f"{row['answer_number']}D"
                self._add_entry(entry_id, cell_list)

        logger.debug(f"Extracted {len(self.entries)} entries")

    def _add_entry(self, entry_id: str, cell_list: Entry) -> None:
        """Add an entry and update mappings."""
        self.entries.append((entry_id, cell_list))
        cells = [(c.x, c.y) for c in cell_list]
        self.entry_to_cells[entry_id] = cells
        for cell_pos in cells:
            self.cell_to_entries[cell_pos].append(entry_id)

    def _get_candidates(self, cell_list: Entry) -> list[str]:
        """Get candidate words for an entry."""
        pattern = str(cell_list)

        # Return fixed word if entry is complete
        if all(c.status in (CellStatus.SET, CellStatus.LOCKED) for c in cell_list):
            return [pattern]

        # Check cache
        cache_key = f"{pattern}_{self.min_score}_{self.max_candidates}"
        if cache_key in self._word_cache:
            return self._word_cache[cache_key]

        # Query database
        candidates = (query.Query(db=self.db, default=False)
                     .match(pattern)
                     .min_score(self.min_score)
                     .limit(self.max_candidates)
                     .order_by_score()
                     .words())

        # Cache and return
        self._word_cache[cache_key] = candidates
        return candidates

    def _add_intersection_constraints(self, problem: Problem, active_entries: list[str] = None) -> None:
        """Add constraints for intersecting entries.

        Parameters
        ----------
        problem : Problem
            The constraint problem
        active_entries : list[str], optional
            list of entries that have candidates. If provided, only add constraints
            between active entries.
        """
        active_set = set(active_entries) if active_entries else None

        for cell_pos, entry_ids in self.cell_to_entries.items():
            if len(entry_ids) == 2:
                entry1_id, entry2_id = entry_ids

                # Skip if either entry is not active
                if active_set:
                    if entry1_id not in active_set or entry2_id not in active_set:
                        continue

                pos1 = self.entry_to_cells[entry1_id].index(cell_pos)
                pos2 = self.entry_to_cells[entry2_id].index(cell_pos)

                def intersection_constraint(word1, word2, p1=pos1, p2=pos2):
                    return word1[p1] == word2[p2]

                problem.addConstraint(intersection_constraint, (entry1_id, entry2_id))

    def _apply_solution(self, solution: dict[str, str]) -> bool:
        """Apply the solution to the grid."""
        for entry_id, word in solution.items():
            cell_list = next(cl for eid, cl in self.entries if eid == entry_id)

            # Skip already complete entries
            if all(c.status in (CellStatus.SET, CellStatus.LOCKED) for c in cell_list):
                continue

            # Set the word
            direction = WordDirection.HORIZONTAL if entry_id[-1] == 'A' else WordDirection.VERTICAL
            start_cell = cell_list[0]
            self.grid.set_word(word, start_cell.x, start_cell.y, direction)
            logger.debug(f"Set {entry_id}: {word}")

        return True


def solve_grid(
    grid: Grid,
    min_score: float = 20,
    max_candidates: int = 100,
    require_unique: bool = True,
    progressive: bool = True
) -> bool:
    """
    Solve a crossword grid.

    Parameters
    ----------
    grid : Grid
        The grid to solve
    min_score : float
        Minimum word score
    max_candidates : int
        Maximum candidates per slot
    require_unique : bool
        Whether to require unique words
    progressive : bool
        Whether to try progressively relaxed constraints

    Returns
    -------
    bool
        True if solved successfully
    """
    solver = CrosswordConstraintSolver(
        grid=grid,
        min_score=min_score,
        max_candidates=max_candidates
    )

    # Try with given parameters
    if solver.solve(require_unique=require_unique):
        return True

    if not progressive:
        return False

    # Try without uniqueness constraint
    if require_unique:
        logger.info("Retrying without uniqueness constraint...")
        if solver.solve(require_unique=False):
            return True

    # Try with lower score threshold
    if min_score > 0:
        logger.info("Retrying with min_score=0...")
        solver.min_score = 0
        if solver.solve(require_unique=False):
            return True

    # Try with more candidates
    if max_candidates < 500:
        logger.info("Retrying with more candidates...")
        solver.max_candidates = 500
        if solver.solve(require_unique=False):
            return True

    return False


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create test grid
    grid = Grid((4, 4))
    grid[0,1] = "B"
    # grid_path = "/Users/lafarnb1/Projects/GitHub/CrossCosmos/scratch/past_nyt_test.json"
    # full_grid = Grid.load(grid_path)
    # grid = full_grid.make_subgrid_from_words(word_ids=["5D", "6D", "7D", "8D", "9D", "28A"])

    logger.info("Initial grid:")
    logger.info("\n" + grid.to_str())

    # Solve
    if solve_grid(grid, min_score=20, max_candidates=1000):
        logger.info("Solution found:")
        logger.info("\n" + grid.to_str())
    else:
        logger.error("No solution found")
