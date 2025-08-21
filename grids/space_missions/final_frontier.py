""" 
"""

import crosscosmos as xc

df = xc.Query(q=2).df()
grid = xc.Grid.load("final_frontier.json")
xc.run_gui(grid, df=df)