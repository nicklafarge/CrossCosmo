""" 
"""
import string

from pony import orm

from crosscosmos import query
from crosscosmos.wordlists import LaFargeWord

dfl = query.contains_str_and_removed_str(LaFargeWord, "HOC", 0)

def get_words_by_char_and_length(char: str, position: int, length: int) -> list[str]:
    """
    Get all words with specified character at given position and exact length.

    Parameters
    ----------
    char : str
        The character to match (single character)
    position : int
        Zero-based index position of the character
    length : int
        Required word length

    Returns
    -------
    list[str]
        List of words matching the criteria

    Raises
    ------
    ValueError
        If position >= length or position < 0
    """

    return query.Query().length(length).fix_letter(position, char)._df()

first_word = "TEST"
n_letters = len(first_word)

down_lengths = [4, 3, 3, 3]
best_letters = []
for i in range(n_letters):
    ordered_entries = []
    for letter in string.ascii_uppercase:
        length = down_lengths[i]
        res = LaFargeWord.select(lambda w: len(w.word) == length and w.word[0] == first_word[i] and w.word[1] == letter)
        # res = get_words_by_char_and_length(letter, 0, 4)
        n_words = res.count()
        if n_words > 0:
            ordered_entries.append((letter, n_words))
    best_letters.append(ordered_entries)
