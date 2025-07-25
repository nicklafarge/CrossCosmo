""" """

import logging

import polars as pl

logger = logging.getLogger(__name__)


class Filter:
    def __init__(self, df: pl.DataFrame, sunday: bool = False):
        """Helper class for applying filters to a dataframe containing word results (see xc.Query)

        Parameters
        ----------
        df : pl.DataFrame
            Database containing word data"""
        self.df = df

    def fix_letter(self, letter_idx: int, value: str) -> "Filter":
        assert len(value) == 1
        self.df = self.df.filter(pl.col("word").str.slice(letter_idx, 1) == value)
        return self

    def apply(self) -> pl.DataFrame:
        return self.df
