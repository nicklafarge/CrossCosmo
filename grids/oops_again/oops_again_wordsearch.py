""" """

import polars as pl

import crosscosmos as xc
from crosscosmos import LaFargeWord
from crosscosmos.df_filter import DfFilter

sunday = xc.constants.NYT_SUNDAY_SIZE

df = xc.Query(default=False, q=0, limit=None).df()

def print_matchess(_df):
    for row in _df.iter_rows(named=True):
        itit = row["word"].replace("IT", "ITIT")
        print(len(itit))
        print(row["score"])
        print(f"{itit}")
        print(f"{row['word']}\n")


dfititit = DfFilter(df, default=False).max_length(sunday - 6).match("*IT*IT*IT*").by_score()
dfitit = DfFilter(df, default=False).max_length(sunday - 4).match("*IT*IT*").by_score()
dfit = DfFilter(df, default=False).max_length(sunday - 2).match("*IT*").by_score()

dfititit_21 = DfFilter(dfititit, default=False).length(sunday-4).df()
dfitit_21 = DfFilter(dfitit, default=False).length(sunday-4).df()
dfit_21 = DfFilter(dfit, default=False).length(sunday-2).df()




from crosscosmos.wordlists.lafarge import LaFargeWord, orm
LaFargeWord(word="CITYWITHINACITY", score=80, sources=["manual"])
orm.commit()