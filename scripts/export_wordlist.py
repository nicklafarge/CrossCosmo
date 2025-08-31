import crosscosmos as xc

df = xc.Query(db=xc.LaFargeWord, q=2).df()

df2 = df["word", "score"]
df2.write_csv("lafarge_word_list.csv")