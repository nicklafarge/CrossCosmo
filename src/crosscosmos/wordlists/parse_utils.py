"""Parsing utilities for word list processing."""

import csv
import logging
from pathlib import Path
from typing import Generator, Type

from pony import orm

logger = logging.getLogger(__name__)


def read_csv_generator(path: Path, delimiter: str = ",", **kwargs) -> Generator[list[str], None, None]:
    """
    Read CSV file and yield rows.

    Parameters
    ----------
    path : Path
        Path to CSV file
    delimiter : str, optional
        CSV delimiter character, by default ","
    **kwargs
        Additional arguments passed to csv.reader

    Yields
    ------
    list[str]
        Row from CSV file
    """
    with open(path, encoding='ISO-8859-1') as file:
        yield from csv.reader(file, delimiter=delimiter, **kwargs)


def parse_word_score(
    word_score_path: Path,
    word_model,
    delimiter: str = ",",
    score_multiplier: float = 1,
    batch_size: int = 1000,
    show_progress: bool = True,
) -> None:
    """
    Parse word-score pairs from CSV and populate database model.

    Parameters
    ----------
    word_score_path : Path
        Path to CSV file containing word,score pairs
    word_model
        Pony ORM model class with 'word' and 'score' fields
    delimiter : str, optional
        CSV delimiter, by default ","
    score_multiplier : float, optional
        Multiplier for score values, by default 1
    batch_size : int, optional
        Number of records to process before committing, by default 1000
    show_progress : bool, optional
        Whether to show progress updates, by default True

    Raises
    ------
    ValueError
        If CSV row doesn't contain exactly 2 fields
    """
    records_processed = 0

    with orm.db_session:
        for row in read_csv_generator(word_score_path, delimiter):
            if len(row) != 2:
                logger.warning(f"Skipping invalid row: {row}")
                continue

            word, score = row
            word = word.strip().upper()

            try:
                score_value = int(int(score) * score_multiplier)
            except ValueError:
                logger.warning(f"Invalid score '{score}' for word '{word}'")
                continue

            # Check if word already exists
            existing = word_model.get(word=word)
            if existing:
                existing.score = score_value
            else:
                word_model(word=word, score=score_value)

            records_processed += 1

            if show_progress and records_processed % batch_size == 0:
                logger.info(f"Processed {records_processed:,} records")
                orm.commit()

        orm.commit()
        logger.info(f"Completed: {records_processed:,} total records processed")
