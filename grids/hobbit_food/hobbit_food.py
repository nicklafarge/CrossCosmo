import crosscosmos as xc

grid = xc.Grid.load("hobbit_food.json")
df = xc.Query(q=2, limit=None).df()

xc.run_gui(grid=grid, df=df)