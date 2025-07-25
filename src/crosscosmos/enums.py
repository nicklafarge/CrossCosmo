""" """

from enum import Enum

from crosscosmos.constants import NYT_REGULAR_SIZE, NYT_SUNDAY_SIZE


class GridSize(Enum):
    NYT_REGULAR = (NYT_REGULAR_SIZE, NYT_REGULAR_SIZE)
    NYT_SUNDAY = (NYT_SUNDAY_SIZE, NYT_SUNDAY_SIZE)


class LetterStatus(Enum):
    VALID = 1
    INVALID = 2


class LetterSequenceStatus(Enum):
    INVALID = 1
    VALID_SUBTRIE = 2
    VALID_WORD = 3
