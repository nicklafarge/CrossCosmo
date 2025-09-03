""" """
import string

PLACEHOLDERS = {r"?", r"-", r" "}

ALPHABET = set(string.ascii_uppercase)
VOWELS = set("aeiouAEIOU")
CONSONANTS = set("bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ")
ANY_LETTER_RE_PATTERN = "[a-zA-Z]"

NYT_REGULAR_SIZE = 15
NYT_SUNDAY_SIZE = 21
