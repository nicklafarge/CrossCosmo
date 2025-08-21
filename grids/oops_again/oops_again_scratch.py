from pathlib import Path
import numpy as np
import crosscosmos as xc

# Maximum word counts differ depending on the editor. From tough to tougher:
#   - Stan Newman - 146
#   - everyone not mentioned above or below - 144
#   - Mel Rosen - 142
#   - Will Shortz and Susan West (Games) -140


grid_path = Path(__file__).parent / "oops_again1.json"
grid = xc.grid.Grid.load(grid_path)

sg = grid.make_subgrid_from_words(["1D", "2D", "3D", "4D", "5D", "37A"])

# Theme entries
theme_entries = [grid.get_entry(e) for e in ["24A", "32A", "57A", "99A", "110A", "3D", "13D", "52D", "69D"]]
theme_lengths = [len(e) for e in theme_entries]

n_total_entries = len(grid.entries_df())
n_theme_entries = len(theme_lengths)
avg_length = np.mean(theme_lengths)
n_cells = sum(theme_lengths)

print(f"{n_total_entries=}")
print(f"{n_theme_entries=}")
print(f"{avg_length=:.2f}")
print(f"{n_cells=}")


df = xc.Query(db=xc.LaFargeWord, default=False, limit=None).min_score(80).df()
gui = xc.run_gui(grid=grid, df=df)