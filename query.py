"""
Copyright 2023 The Johns Hopkins University Applied Physics Laboratory LLC (JHU/APL).

All Rights Reserved.
This material may be only be used, modified, or reproduced by or for the U.S. Government
pursuant to the license rights granted under the clauses at DFARS 252.227-7013/7014 or
FAR 52.227-14. For any other permission, please contact the Office of Technology Transfer at JHU/APL.
"""

# Standard library imports
import logging

# Third-party imports

# Local imports
from crosscosmos.corpus import Corpus

logger = logging.getLogger("query")

logger.info("LOADING")
corpus = {
    1: Corpus.from_test(),
    2: Corpus.from_diehl(),
    3: Corpus.from_lafarge(),
    4: Corpus.from_collab()
}


def match(query: str, lvl: int = 1):
    if lvl not in corpus.keys():
        return ValueError(f"Invalid corpus index: {lvl}")

    return corpus[lvl].query(query.replace(" ", ''))


if __name__ == "__main__":
    query_str = "A--D"
    test1 = match(query_str, 1)
    test2 = match(query_str, 2)
    test3 = match(query_str, 3)


    # KARANAMOK
    match('------R', 1)

    match('------M-K', 4)