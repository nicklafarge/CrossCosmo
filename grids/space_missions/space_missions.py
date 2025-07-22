from pathlib import Path
from crosscosmos.gui import grid_gui
import crosscosmos as xc

from crosscosmos.wordlists import LaFargeWord

grid_path = Path(__file__).parent / 'space_missions.json'
xc_grid = xc.grid.Grid.load(grid_path)
# xc_grid.corpus = xc.corpus.Corpus.from_lafarge()



df = xc_grid.to_dataframe()
word_lengths = xc_grid.word_lengths()
n_words = word_lengths['wcount'].sum()
print(f"{n_words=}")

for x in word_lengths.iter_rows(named=True):
    print(f"{x['word_len']:02}  |  {x['wcount']:02}")
    print(f"   {', '.join(x['dir_answer_list'])}")


grid_gui.run_default(xc_grid)