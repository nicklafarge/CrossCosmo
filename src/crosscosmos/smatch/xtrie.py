import logging

# Third party
import pygtrie

# Local

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


test_words = ["SKIP", "JUMP", "HELP", "FLOP", "SLOW", "HAND", "SLAP", "LUMP", "LEAP"]

t = pygtrie.CharTrie()
for s in test_words:
    t[s] = True
