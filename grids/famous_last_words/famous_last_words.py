from pathlib import Path

import crosscosmos as xc
from crosscosmos.wordlists import LaFargeWord

grid_path = Path(__file__).parent / "famous_last_words.json"
xc_grid = xc.grid.Grid.load(grid_path)

# xc_grid.corpus = xc.corpus.Corpus.from_lafarge()

# grid_gui.run_default(xc_grid)

# word = xc_grid.get_word("51A")
# crossers = xc_grid.get_crossers("51A")
# match_strs = [str(w) for w in crossers]

q = 1
# df45d = xc_grid.get_possible_words("45D", q=q, exclude = {1: "Y"})
#
#
# df38d = xc_grid.get_possible_words("38D", q=q)
#
# # KODOS (simpsons alien)
# df44d = xc_grid.get_possible_words("44D", q=q)
# df47d = xc_grid.get_possible_words("47D", q=q)
# df48d = xc_grid.get_possible_words("48D", q=q)
# df64a = xc_grid.get_possible_words("64A", q=q)
# #
# df51a = xc_grid.get_possible_words("51A", q=q,
#                                    exclude = {1:"GM", 2:"G"}
#                                    # exclude = {0:"AE", 1:"GM", 2:"G"}
#                                    )
# # df51a = xc.query.set_df_letter(df51a, 1, "A")
#
# xc_grid.get_word("60A")[0].value = "D"
# xc_grid.get_word("60A")[1].value = "R"
# xc_grid.get_word("60A")[2].value = "E"
#
#
# df61a = xc_grid.get_possible_words("61A", q=q)
#
# df55d = xc_grid.get_possible_words("55D", q=q)
# df56d = xc_grid.get_possible_words("56D", q=q)
# df57d = xc_grid.get_possible_words("57D", q=q)
#
# xc_grid.get_word("60A")

#####################################################################################################################
# Middle left
####################################################################################
xc_grid = xc.grid.Grid.load(grid_path)

df28a = xc_grid.get_possible_words("28A", q=0)
df30a = xc_grid.get_possible_words("30A", q=q)
df40a = xc_grid.get_possible_words("40A", q=q)
df42a = xc_grid.get_possible_words("42A", q=q)


df21d = xc_grid.get_possible_words("21D", q=q)
df24d = xc_grid.get_possible_words("24D", q=q)
df30d = xc_grid.get_possible_words("30D", q=q)
df31d = xc_grid.get_possible_words("31D", q=q)
df32d = xc_grid.get_possible_words("32D", q=q)
df33d = xc_grid.get_possible_words("33D", q=q)

####################################################################################
# Upper middle
####################################################################################
xc_grid = xc.grid.Grid.load(grid_path)

# df5a = xc_grid.get_possible_words("5A", q=q)
# df15a = xc_grid.get_possible_words("15A", q=q)
# df18a = xc_grid.get_possible_words("18A", q=q)
# df22a = xc_grid.get_possible_words("22A", q=q, exclude={3:"A"})
# df28a = xc_grid.get_possible_words("28A", q=q)
# df30a = xc_grid.get_possible_words("30A", q=q)
#
# df5d = xc_grid.get_possible_words("5D", q=q)
# df6d = xc_grid.get_possible_words("6D", q=q)
# df7d = xc_grid.get_possible_words("7D", q=q)
# df8d = xc_grid.get_possible_words("8D", q=q)
####################################################################################
# Lower left
####################################################################################
# xc_grid = xc.grid.Grid.load(grid_path)
# df60a = xc_grid.get_possible_words("60A", q=q)
# df63a = xc_grid.get_possible_words("63A", q=q)

# df55d = xc_grid.get_possible_words("55D", q=q)
# df56d = xc_grid.get_possible_words("56D", q=q)
# df57d = xc_grid.get_possible_words("57D", q=q)

####################################################################################
# Lower right
####################################################################################
# xc_grid = xc.grid.Grid.load(grid_path)
# df49d = xc_grid.get_possible_words("49D", q=q)
# df50d = xc_grid.get_possible_words("50D", q=q)
# df53d = xc_grid.get_possible_words("53D", q=q)
# df54d = xc_grid.get_possible_words("54D", q=q)

# df52a = xc_grid.get_possible_words("52A", q=q)
# df59a = xc_grid.get_possible_words("59A", q=q)
# df62a = xc_grid.get_possible_words("62A", q=q)
# df65a = xc_grid.get_possible_words("65A", q=q)
#
#
# from crosscosmos.filter import Filter
# f = Filter(df55d)
# dfm = f.fix_letter(0, "M").apply()
# # grid_gui.run_default(xc_grid)
