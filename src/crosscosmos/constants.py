""" """
import string

PLACEHOLDERS = [r"?", r"-", r" "]

ALPHABET = string.ascii_uppercase
VOWELS = "aeiouAEIOU"
CONSONANTS = "bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ"
ANY_LETTER_RE_PATTERN = "[a-zA-Z]"

NYT_REGULAR_SIZE = 15
NYT_SUNDAY_SIZE = 21
