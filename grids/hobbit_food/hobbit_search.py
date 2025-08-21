import polars as pl
import numpy as np

import crosscosmos as xc
from crosscosmos import WordDirection
from crosscosmos.scoring import *

grid = xc.Grid.load("hobbit_food.json")
df = xc.Query(q=2, limit=None).df()
print(grid)

gps = xc.GridPruningSolver(grid=grid, word_df=df)
gps.solve()


test_entry_id = "12D"
n_solve = 55

all_entry_words = gps.get_scored_words(test_entry_id)
crosser_entries = [c.entry_id for c in gps.grid.get_crossers(test_entry_id)]
re_queue_entries = [test_entry_id, *crosser_entries]

test_entry_words = all_entry_words.filter(pl.col("score") > 40)

test_entry_results = []
i = 0
for row in test_entry_words.iter_rows(named=True):
    if i == n_solve:
        break
    # temp_grid = grid.clone()
    gps.grid.set_entry(test_entry_id, row["word"])
    gps.add_to_requeue(test_entry_id)
    # gps = xc.GridPruningSolver(grid=temp_grid, word_df=df)
    solve_result = gps.re_solve()
    solve_result.update(row)
    test_entry_results.append(solve_result)
    i = i + 1

test_results = pl.DataFrame(test_entry_results)
test_results = test_results["word", "score", "total_score", "converged"]

conv_results = test_results.filter(pl.col("converged"))

# --------12D---------
# """AMATORIA"""
# """ANATOLIA"""
# """ZOOTOPIA"""
# """ECOTOPIA"""
# """PRETORIA"""
# """VICTORIA"""
# """EVALORIA"""
# """SENSORIA"""
# """APOLOGIA"""
# """AIRTOSEA"""
# """KOINONIA"""
# """DYSTOPIA"""
# """HARMONIA"""
# """EASTONPA"""
# """MAGNOLIA"""
# """LONGORIA"""
# """MONROVIA"""
