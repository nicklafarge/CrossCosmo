"""Data models for letters and words"""

import logging

from pydantic import AnyUrl, BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class Letter(BaseModel, frozen=True):
    s: str = ConfigDict()
    i: int
    j: int


class Word(BaseModel):
    word: str
    info: AnyUrl
    pubid: str = None
