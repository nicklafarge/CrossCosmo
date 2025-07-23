from pathlib import Path

import crosscosmos as xc
from crosscosmos.wordlists import LaFargeWord

grid_path = Path(__file__).parent / "famous_last_words.json"
xc_grid = xc.grid.Grid.load(grid_path)
# xc_grid.corpus = xc.corpus.Corpus.from_lafarge()

# grid_gui.run_default(xc_grid)

# word = xc_grid.get_word("51A")
crossers = xc_grid.get_crossers("51A")
match_strs = [str(w) for w in crossers]

score_threshold = 10
df45d = xc_grid.get_possible_words(LaFargeWord, "45D", score_threshold, exclude = {1: "Y"})


df38d = xc_grid.get_possible_words(LaFargeWord, "38D", score_threshold)

# KODOS (simpsons alien)
df44d = xc_grid.get_possible_words(LaFargeWord, "44D", score_threshold)
df47d = xc_grid.get_possible_words(LaFargeWord, "47D", score_threshold)
df48d = xc_grid.get_possible_words(LaFargeWord, "48D", score_threshold)
df64a = xc_grid.get_possible_words(LaFargeWord, "64A", score_threshold)
#
df51a = xc_grid.get_possible_words(LaFargeWord, "51A", score_threshold,
                                   exclude = {1:"GM", 2:"G"}
                                   # exclude = {0:"AE", 1:"GM", 2:"G"}
                                   )
# df51a = xc.query.set_df_letter(df51a, 1, "A")

xc_grid.get_word("60A")[0].value = "D"
xc_grid.get_word("60A")[1].value = "R"
xc_grid.get_word("60A")[2].value = "E"


df60a = xc_grid.get_possible_words(LaFargeWord, "60A", score_threshold)
df61a = xc_grid.get_possible_words(LaFargeWord, "61A", score_threshold)
df63a = xc_grid.get_possible_words(LaFargeWord, "63A", score_threshold)

df55d = xc_grid.get_possible_words(LaFargeWord, "55D", score_threshold)
df56d = xc_grid.get_possible_words(LaFargeWord, "56D", score_threshold)
df57d = xc_grid.get_possible_words(LaFargeWord, "57D", score_threshold)

xc_grid.get_word("60A")
#
#
#
# from crosscosmos.filter import Filter
# f = Filter(df55d)
# dfm = f.fix_letter(0, "M").apply()
# # grid_gui.run_default(xc_grid)
