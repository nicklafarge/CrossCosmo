from pathlib import Path

import crosscosmos as xc
from crosscosmos.gui import grid_gui


grid_path = Path(__file__).parent / "famous_last_words.json"
xc_grid = xc.grid.Grid.load(grid_path)
# xc_grid.corpus = xc.corpus.Corpus.from_lafarge()

grid_gui.run_default(xc_grid)


df = xc_grid.to_dataframe()
word_lengths = xc_grid.word_lengths()
