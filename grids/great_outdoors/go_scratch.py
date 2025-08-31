import crosscosmos as xc

f24 = xc.Query(q=2, limit=1000).match("?F??").df()
f34 = xc.Query(q=2, limit=1000).match("??F?").df()

f27 = xc.Query(q=2, limit=1000).match("?F?????").df()
f37= xc.Query(q=2, limit=1000).match("??F????").df()


f56 = xc.Query(q=2, limit=1000).match("????F?").df()
f46 = xc.Query(q=2, limit=1000).match("???F??").df()
