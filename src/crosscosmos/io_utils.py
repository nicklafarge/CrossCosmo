"""Utilities for file input/output"""

import json
from pathlib import Path


def save_json_dict(filename: Path | str, jdict: dict) -> None:
    """Saves a dictionary to a JSON file.

    Parameters
    ----------
    filename : Path
        The path to the output JSON file.
    jdict : dict
        The dictionary to be saved.
    """
    filename = Path(filename)

    if not filename.parent.is_dir():
        raise FileNotFoundError("Folder not found: {filename}")

    with open(filename, "w") as outfile:
        json.dump(jdict, outfile, indent=2)


def load_json(filename: Path | str) -> dict:
    """Loads data from a JSON file.

    This function can handle cases where the JSON data is stored as a
    string within the file.

    Parameters
    ----------
    filename : Path
        The path to the JSON file.

    Returns
    -------
    dict
        The loaded data as a dictionary.
    """
    filename = Path(filename)

    if not filename.is_file():
        raise FileNotFoundError("File not found: {filename}")

    with open(filename) as f:
        data = json.load(f)
    if isinstance(data, str):
        data = json.loads(data)
    return data
