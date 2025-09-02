from pathlib import Path

import crosscosmos as xc
from crosscosmos.wordlists.crossword_tracker import XwordWord
from crosscosmos.wordlists.lafarge import LaFargeWord
from crosscosmos.archive import grid_gui, query


def run_gui():
    grid_path = Path(__file__).parent / 'ad_hoc.json'
    xc_grid = xc.grid.Grid.load(grid_path)
    # xc_grid.corpus = xc.corpus.Corpus.from_lafarge()
    grid_gui.run_default(xc_grid)

if __name__ == "__main__":
    # run_gui()


    dfl = query.contains_str_and_removed_str(LaFargeWord, "HOC", 0)
    # dfd = query.contains_str_and_removed_str(XwordWord, "HOC", 0)
    # dfc = query.contains_str_and_removed_str(CollabWordListWord, "HOC", 0)
    # dft = query.contains_str_and_removed_str(TestWord, "HOC", 0)
    dfx = query.contains_str_and_removed_str(XwordWord, "HOC", 0)
