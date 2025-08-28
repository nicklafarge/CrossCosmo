""" """
import crosscosmos as xc

sunday = xc.constants.NYT_SUNDAY_SIZE
cols = ["word", "score", "length"]

df = xc.Query(db=xc.LaFargeWord, default=False, q=0, limit=None).df()


not1_end = xc.refine(df, "*NOT", min_score=40, max_length=12)
not1_start = xc.refine(df, "NOT*", min_score=40, max_length=12)

not1_end = xc.refine(df, "*NOT", min_score=40, max_length=12)


not1 = xc.refine(df, "*NOT*", min_score=60, max_length=7)

df_knot = xc.refine(df, "*KNOT*", min_score=30, max_length=8)

# NO TNOTE