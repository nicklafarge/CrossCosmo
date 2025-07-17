import csv
from pathlib import Path

path = Path("/Users/nlafarge/Library/CloudStorage/Dropbox/Personal/CrossCosmos/space")

WHITESPACE = r"            "

with open(path, "r") as file:
    reader = csv.reader(file, delimiter="\n")

    words = [row[0].strip() for row in reader]


words_by_len = sorted(words, key=lambda w: len(w))
out_words = "\n".join([f"{WHITESPACE}{w}" for w in words_by_len])

new_file = path.parent / f"{path.name}_sorted"
with open(new_file, "w") as file:
    file.write(out_words)