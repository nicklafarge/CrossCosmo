from pathlib import Path
import arcade
from crosscosmos.gui.new_grid import CrossCosmosGui, LayoutConfig
import crosscosmos as xc

grids_path = xc.grids_root / "oops_again"

# Create grid backend
grid_path = Path(grids_path / "oops_again1.json")
grid = xc.grid.Grid.load(grid_path)

# word_ids=["6A", "21A", "24A", "27A"] + [f"{x}D" for x in range(6, 17)]
# sg = grid.make_subgrid_from_words(word_ids=word_ids)

# xc.gui.grid_gui.run_default(sg)
es = grid.entry_starts

df = xc.Query(default=False, q=1, limit=None).max_length(max(grid.grid.shape)).order_by_score().df()

config = LayoutConfig()

layout_view = CrossCosmosGui(sg, config, df=df)
# layout_view = CrossCosmosGui(grid, config, df=df)
# arcade.run()

