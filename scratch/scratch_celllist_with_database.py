""" """
from pathlib import Path
import polars as pl

import crosscosmos as xc
from crosscosmos import LaFargeWord
from crosscosmos.refine import Refiner

################################################################################################
# Setup
################################################################################################

sunday = xc.constants.NYT_SUNDAY_SIZE
cols = ["word", "score", "length"]

df_orig = xc.Query(db=LaFargeWord, default=False, q=0, limit=None).df()

grid_path = Path("test_auto.json").resolve()
# grid = xc.grid.Grid.load(grid_path, corpus=xc.corpus.Corpus.from_lafarge())
grid = xc.grid.Grid.load(grid_path)

cl = grid.get_word("1A")

df = xc.Query(default=False, alpha_only=False).limit(10).match("T???").order_by_score().df()