from pathlib import Path

# keep track of the root file path of AstroCodex
project_root = Path(__file__).parents[2]
crosscosmos_root = Path(__file__).parent
config_root = project_root / "config"
grids_root = project_root / "grids"

__all__ = ["config_root", "crosscosmos_root", "grids_root", "project_root"]
