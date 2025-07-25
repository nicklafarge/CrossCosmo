""" """

import logging

from crosscosmos.corpus import Corpus

logger = logging.getLogger(__name__)


def match(corpus: Corpus, query: str | xc.grid.CellList):
    return corpus.query(str(query))


def match_by_level(corpus_lvl_dict: dict, query: str, lvl: int = 1):
    if lvl not in corpus_lvl_dict.keys():
        return ValueError(f"Invalid corpus index: {lvl}")

    return match(corpus_lvl_dict[lvl], query)


# if __name__ == "__main__":
#     logger.info("LOADING")
#     corpus_lvls = {
#         1: xc.corpus.Corpus.from_test(),
#         2: xc.corpus.Corpus.from_diehl(),
#         3: xc.corpus.Corpus.from_lafarge(),
#         4: xc.corpus.Corpus.from_collab(),
#     }
#
#     def m(query: str, lvl: int = 3):
#         return match_by_level(corpus_lvls, query, lvl)
#
#     query_str = "A--D"
#     test1 = m(corpus_lvls, query_str, 1)
#     test2 = m(corpus_lvls, query_str, 2)
#     test3 = m(corpus_lvls, query_str, 3)
#
#     # KARANAMOK
#     m("------R", 1)
#     m("------M-K", 4)
