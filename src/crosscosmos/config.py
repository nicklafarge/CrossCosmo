# Standard libarary imports
from pathlib import Path

# keep track of the root file path of AstroCodex
crosscosmos_project_root = Path(__file__).parents[2]
crosscosmos_root = Path(__file__).parent

__all__ = ["crosscosmos_project_root", "crosscosmos_root"]
