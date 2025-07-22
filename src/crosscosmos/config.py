from pathlib import Path

# keep track of the root file path of AstroCodex
project_root = Path(__file__).parents[2]
crosscosmos_root = Path(__file__).parent

__all__ = ["project_root", "crosscosmos_root"]
