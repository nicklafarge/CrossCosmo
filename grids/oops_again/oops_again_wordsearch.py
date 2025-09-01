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

grid_path = Path(__file__).parent / "oops_again1.json"
grid = xc.grid.Grid.load(grid_path, corpus=xc.corpus.TrieCorpus.from_lafarge())


################################################################################################
# Helper functions
################################################################################################

def print_matches(_df):
    for row in _df.iter_rows(named=True):
        itit = row["word"].replace("IT", "ITIT")
        print(len(itit))
        print(row["score"])
        print(f"{itit}")
        print(f"{row['word']}\n")

def process_it_df(_df):
    _df_it = _df.with_columns(
        pl.col("word").str.replace_all("IT", "ITIT").alias("word_itit"),
    )
    _df_it = _df_it.with_columns(word_itit_len=pl.col("word_itit").str.len_chars())
    return _df_it

################################################################################################
# Load ITIT words into dataframe
################################################################################################

new_data = []
df_orig = df_orig.with_columns(doubled=False)
df_it = process_it_df(Refiner(df_orig, default=False).max_length(sunday - 4).match("*IT*").by_score())
for it_word in df_it.iter_rows(named=True):
    new_word = it_word
    new_word['word'] = new_word.pop("word_itit")
    new_word.pop("word_itit_len")
    new_word['length'] = len(new_word['word'])
    new_word['doubled'] = True
    new_data.append(new_word)

df_all = pl.concat([df_orig, pl.DataFrame(new_data)])

################################################################################################
# GET "IT" x3, x2, and x1 values
################################################################################################
df3 = xc.refine(df_all, match_term="*IT"*6 +"*", sunday=True).filter(doubled=True)
df2 = xc.refine(df_all, match_term="*IT"*4 +"*", sunday=True).filter(doubled=True)
df1 = xc.refine(df_all, match_term="*IT"*2 +"*", sunday=True).filter(doubled=True)


################################################################################################
# Query helpers
################################################################################################
def middle_intersect(n_before_positivity: int, letters_str: str, df=df2):
    letters = letters_str.upper().split(",")
    return xc.refine(
        df,
        fixed_letters={n_before_positivity: letters[0], n_before_positivity + 6:letters[1]},
        sunday=True
    )[cols]


def left_intersect(n_before_oops: int, letters_str: str, df=df2):
    letters = letters_str.upper().split(",")
    return xc.refine(
        df,
        fixed_letters={n_before_oops: letters[0], n_before_oops + 3:letters[1]},
        sunday=True
    )[cols]

################################################################################################
# Theme pairs
################################################################################################
hoity_toity_pair = xc.refine(df2, fixed_letters={9: "I"}, length=14)

################################################################################################
# Sandbox
################################################################################################



upper = middle_intersect(2, "N,T", df2)
lower = middle_intersect(0, "R,Y", df2)

upper = middle_intersect(1, "I,O", df2)
lower = xc.refine(
    middle_intersect(7, "T,T", df2),
    fixed_letters={3: "D"}
)

left = left_intersect(3,"S,I", df2)

right = xc.refine(df2, fixed_letters={6:"O"})[cols]

top = xc.refine(df2,"*I??????")[cols]
bottom =xc.refine(df2,"??????I*")[cols]

left = xc.refine(df2, "??????I????")[cols]
right = xc.refine(df2, "????T??????")[cols]

topleft = xc.refine(df2, "????I*", max_length=11)[cols]
lowerright = xc.refine(df2, "*I????", max_length=11)[cols]
lowerright2 = xc.refine(df2, "I???????I????")[cols]

"WAIT IT ITI TI"
x = grid.get_possible_words("1A")

df1a = xc.search("LAW??")
df20a = xc.search("OVA??")
df23a = xc.search("WEI??")

################################################################################################
# Bot
################################################################################################
# grid_path = Path(__file__).parent / "oops_again1.json"
# grid = xc.grid.Grid.load(grid_path, corpus=xc.corpus.Corpus(df2, xc.ModelSource.LaFarge))
# grid.build_tries(21)
# sg = grid.make_subgrid_from_words([ "25A", "37A", "43A", "53A", "15D", "35D", "32D"])
# sg.build_tries(21)
# xc.grid_gui.run_default(sg)
# solver = xc.bot.DepthFirstSolver()
# solver.solve(sg)

# sg = xc.grid.Grid.load(grid_path,corpus=grid.corpus)
# topleft = sg.make_subgrid_from_words(["1D", "2D", "3D", "4D", "5D"])
# solver = xc.bot.DepthFirstSolver()
# solver.solve(topleft, print_frequency=1000, max_time=60)

# df18_len = dfitit.filter(pl.col("word_itit").str.len_chars()==18)[cols]
# df18_lent =  df18_len.filter(pl.col("word_itit").str.slice(4, 1) == "T")
# df18_lent =  df18_lent.filter(pl.col("word_itit").str.contains("A"))
#
# # dfit = process_it_df(
# #     Refiner(df, default=False).max_length(sunday - 2).match("*IT*").by_score()
# # )
#
# left_pairs = [(grid[7+i, 7].value, grid[7+i, 13].value) for i in range(7)]
#
# def middle_intersect(n_before_nittygritty: int, letter1: str, letter2: str, df=dfitit):
#     return (df
#         .filter(pl.col("word_itit").str.slice(n_before_nittygritty, 1) == letter1)
#         .filter(pl.col("word_itit").str.slice(n_before_nittygritty+6, 1) == letter2)
#     )[cols]
#
# def left_intersect(n_before_oops: int, letter1: str, letter2: str, df=dfitit):
#     return (df
#         .filter(pl.col("word_itit").str.slice(n_before_oops, 1) == letter1)
#         .filter(pl.col("word_itit").str.slice(n_before_oops+4, 1) == letter2)
#     )[cols]
#
#
#
# df_pt = left_intersect(3, "P", "T")
# df_si = left_intersect(1, "S", "I", df=dfit)
#
#
# df_iya = middle_intersect(6, "I", "Y")
# df_gt = middle_intersect(0, "G", "T")
#
# df_iya = middle_intersect(6, "I", "Y")
# df_gt = middle_intersect(0, "G", "T")
#
# df_tt = (dfitit
#     .filter(pl.col("word_itit").str.slice(2, 1) == "I")
#     .filter(pl.col("word_itit").str.slice(8, 1) == "Y")
# )[cols]
# df_yi = (dfitit
#     .filter(pl.col("word_itit").str.slice(2, 1) == "Y")
#     .filter(pl.col("word_itit").str.slice(8, 1) == "I")
# )[cols]
#
#
# # df_tta = (dfitit
# #     .filter(pl.col("word_itit").str.slice(7, 1) == "T")
# #     .filter(pl.col("word_itit").str.slice(13, 1) == "T")
# # )[cols]
# # df_ioa = (dfitit
# #     .filter(pl.col("word_itit").str.slice(7, 1) == "I")
# #     .filter(pl.col("word_itit").str.slice(13, 1) == "O")
# # )[cols]
# #
# #
# # df51a = (dfitit
# #     .filter(pl.col("word_itit").str.slice(3, 1) == "Y")
# #     .filter(pl.col("word_itit").str.slice(13, 1) == "I")
# # )[cols]
# #
# #
# # dfititit_21 = Refiner(dfititit, default=False).length(sunday-6).df()
# # dfitit_21 = Refiner(dfitit, default=False).length(sunday-4).df()
# # dfitit_17 = Refiner(dfitit, default=False).length(17-4).df()
# # dfit_21 = Refiner(dfit, default=False).length(sunday-2).df()
# #
# #
# # df3d = (dfitit
# #     .filter(pl.col("word_itit").str.slice(4, 1) == "D")
# #     .filter(pl.col("word_itit").str.len_chars() < 20)
# # )
