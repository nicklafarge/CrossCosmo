from pathlib import Path
from crosscosmos.gui import grid_gui
import crosscosmos as xc

grids_path = Path(__file__).parent / 'grids'

# Create grid backend
# grid_path = Path(grids_path / "famous_last_words2.json")
# grid_path = Path(grids_path / "famous_last_words_main.json")
grid_path = Path(grids_path / "flw_lower_left.json")
xc_grid = xc.grid.Grid.load(grid_path)
xc_grid.corpus = xc.corpus.Corpus.from_test()
# xc_grid.corpus = xc.corpus.Corpus.from_lafarge()

grid_gui.run_default(xc_grid)