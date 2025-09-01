import crosscosmos as xc
from crosscosmos.bot import DepthFirstSolver

grid_path = xc.project_root / "scratch" / "sub_grid_main.json"


corpus = xc.corpus.TrieCorpus.from_lafarge(max_length=4, q=1)
grid = xc.grid.Grid.load(grid_path, corpus=corpus)


subgrid = grid.make_subgrid_from_words(["1A", "8A", "10A", "4D"])
#
# # grid = xc.grid.Grid(grid_size=(8,8), save_path=grid_path, auto_symmetry=True)
#
#
# # grid_gui.run_default(grid)
# # grid.save(grid_path)
#
#
#
# cell_lists = [grid.get_word(w) for w in ["1A", "8A", "10A", "4D"]]
#
# xmin = min([w.x_range[0] for w in cell_lists])
# xmax = max([w.x_range[1] for w in cell_lists])
# ymin = min([w.y_range[0] for w in cell_lists])
# ymax = max([w.y_range[1] for w in cell_lists])
#
# all_index_pairs = []
# for w in cell_lists:
#     index_pairs = [(c.x, c.y) for c in w]
#     all_index_pairs.extend(index_pairs)
#
# all_index_pairs = sorted(set(all_index_pairs))
#
# xrange = (xmax-xmin) + 1
# yrange = (ymax-ymin)  +1
# subgrid = xc.grid.Grid(grid_size=(xrange, yrange), corpus=grid.corpus)
#
# for xsub in range(xrange):
#     for ysub in range(yrange):
#         xorig = xsub + xmin
#         yorig = ysub + ymin
#         c_sub = subgrid[xsub, ysub]
#         c_orig = grid[xorig, yorig]
#         if (xorig, yorig) in all_index_pairs:
#             subgrid[xsub, ysub].value= c_orig.value
#             if c_orig.status == xc.CellStatus.SET:
#                 subgrid[xsub, ysub].status= xc.CellStatus.LOCKED
#             else:
#                 subgrid[xsub, ysub].status= xc.CellStatus.EMPTY
#         else:
#             c_sub.status = xc.CellStatus.BLACK
#
# # print(subgrid)
# grid_gui.run_default(grid)
# grid_gui.run_default(subgrid)

import random
random.seed(10)
subgrid.reset_for_solving()
solver = DepthFirstSolver(auto_verify_lt2=True)
solver.solve(subgrid, print_frequency=1)