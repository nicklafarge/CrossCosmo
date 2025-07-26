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


class ModelSource(Enum):
    Test = 1
    Diehl = 2
    LaFarge = 3
    CrosswordTracker = 4
    CollabWordList = 5


class CellStatus(Enum):
    EMPTY = 0
    SET = 1
    LOCKED = 2
    BLACK = 3


class GridDirection(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


class WordDirection(Enum):
    HORIZONTAL = 0
    VERTICAL = 1

    @staticmethod
    def from_char(str_id):
        if str_id.upper() in ["A", "H"]:
            return WordDirection.HORIZONTAL
        elif str_id.upper() in ["D", "V"]:
            return WordDirection.VERTICAL
        else:
            raise ValueError("Expected A or D")

    @staticmethod
    def flip(wd: "WordDirection") -> "WordDirection":
        return WordDirection(not wd.value)


class GridSymmetry(Enum):
    NONE = 0
    ROTATIONAL = 1
    REFLECTION = 2


class MoveDirection(Enum):
    FORWARD_HORIZONTAL = 1
    FORWARD_VERTICAL = 2
    BACK_HORIZONTAL = 3
    BACK_VERTICAL = 4


class GridStatus(Enum):
    COMPLETE = 1
    INCOMPLETE = 2
    INVALID = 3
