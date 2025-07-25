from pathlib import Path

import crosscosmos as xc
from crosscosmos.wordlists import LaFargeWord

grid_path = Path(__file__).parent / "flw2.json"



q=1

#####################################################################################################################
# Middle left
####################################################################################
xc_grid = xc.grid.Grid.load(grid_path)

#####################################################################################################################
# Top right
####################################################################################
xc_grid = xc.grid.Grid.load(grid_path)
df10d = xc_grid.get_possible_words(LaFargeWord, "10D", q=q)
df11d = xc_grid.get_possible_words(LaFargeWord, "11D", q=q)
df12d = xc_grid.get_possible_words(LaFargeWord, "12D", q=q)
df13d = xc_grid.get_possible_words(LaFargeWord, "13D", q=q)

df10a = xc_grid.get_possible_words(LaFargeWord, "10A", q=q)
df16a = xc_grid.get_possible_words(LaFargeWord, "16A", q=q)
df22a = xc_grid.get_possible_words(LaFargeWord, "22A", q=q)


# xc_grid = xc.grid.Grid.load(grid_path)
# df07d = xc_grid.get_possible_words(LaFargeWord, "7D", q=q)
# df08d = xc_grid.get_possible_words(LaFargeWord, "8D", q=q)
# df09d = xc_grid.get_possible_words(LaFargeWord, "9D", q=q)
#
# df19d = xc_grid.get_possible_words(LaFargeWord, "19D", q=q)
#
#
# df05a = xc_grid.get_possible_words(LaFargeWord, "5A", q=q)
# df15a = xc_grid.get_possible_words(LaFargeWord, "15A", q=q)
# df27a = xc_grid.get_possible_words(LaFargeWord, "27A", q=q)
# df28a = xc_grid.get_possible_words(LaFargeWord, "28A", q=q)