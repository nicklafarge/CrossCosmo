# Standard libaray
import os
import pickle
import json
from pathlib import Path


def save_json_dict(filename: Path, jdict: dict):
    with open(filename, 'w') as outfile:
        json.dump(jdict, outfile, indent=2)


def load_json(filename: Path) -> dict:
    with open(filename) as f:
        data = json.load(f)
    if isinstance(data, str):
        data = json.loads(data)
    return data
