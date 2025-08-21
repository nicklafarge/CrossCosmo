import polars as pl
import numpy as np

from crosscosmos.enums import CellStatus
from crosscosmos.grid import Grid


def get_letter_distribution_at_position(
    df: pl.DataFrame, position: int, word_col: str = "word", score_col: str | None = None
) -> pl.DataFrame:
    """
    Compute the distribution of letters at a specific position in words.

    Parameters
    ----------
    df : pl.DataFrame
        DataFrame containing word column
    position : int
        Position to analyze (0-indexed)
    word_col : str
        Name of the column containing words
    score_col : str | None
        Optional column with quality scores (0-100) to weight the distribution

    Returns
    -------
    pl.DataFrame
        DataFrame with letters and their statistics at the specified position
    """
    filtered = df.filter(pl.col(word_col).str.len_chars() > position).with_columns(
        letter=pl.col(word_col).str.slice(position, 1).str.to_uppercase()
    )

    # Base aggregation
    agg_exprs = [pl.len().alias("count"), pl.col(word_col).n_unique().alias("unique_words")]

    # Add score-based metrics if score column provided
    if score_col:
        agg_exprs.extend(
            [
                pl.col(score_col).mean().alias("avg_score"),
                pl.col(score_col).sum().alias("total_score"),
                (pl.col(score_col) * 1.0).sum().alias("score_weighted_count"),
            ]
        )

    result = (
        filtered.group_by("letter")
        .agg(agg_exprs)
        .with_columns(
            [
                (pl.col("count") / pl.col("count").sum() * 100).round(2).alias("percentage"),
                pl.col("count").sum().alias("total_words"),
            ]
        )
    )

    if score_col:
        result = result.with_columns(
            score_weighted_pct=(pl.col("score_weighted_count") / pl.col("score_weighted_count").sum() * 100).round(2)
        )

    return result.sort("count", descending=True)


def compute_letter_scores(
    df1: pl.DataFrame,
    df2: pl.DataFrame,
    use_quality_scores: bool = False,
    frequency_weight: float = 0.4,
    quality_weight: float = 0.3,
    scarcity_weight: float = 0.3,
    scarcity_penalty_power: float = 1.0,
) -> pl.DataFrame:
    """
    Compute combined letter scores from two frequency distributions.

    Parameters
    ----------
    df1, df2 : pl.DataFrame
        DataFrames from get_letter_distribution_at_position
    use_quality_scores : bool
        Whether to incorporate quality scores in the calculation
    frequency_weight : float
        Weight for frequency component (how often letter appears)
    quality_weight : float
        Weight for quality component (avg quality of words with letter)
    scarcity_weight : float
        Weight for scarcity preservation (penalty for excluding words)
    scarcity_penalty_power : float
        Power factor for scarcity penalty (higher = more penalty for excluding words)

    Returns
    -------
    pl.DataFrame
        DataFrame with letters and their combined scores

    Notes
    -----
    Weights should sum to 1.0 for normalized scores.
    """
    # Get total counts for scaling
    total1 = df1["count"].sum()
    total2 = df2["count"].sum()

    # Prepare columns for join - only include columns that exist
    cols1 = ["letter", "count", "percentage"]
    cols2 = ["letter", "count", "percentage"]

    # Only add quality columns if they actually exist in the dataframes
    if use_quality_scores:
        if "avg_score" in df1.columns:
            cols1.append("avg_score")
        if "score_weighted_pct" in df1.columns:
            cols1.append("score_weighted_pct")
        if "avg_score" in df2.columns:
            cols2.append("avg_score")
        if "score_weighted_pct" in df2.columns:
            cols2.append("score_weighted_pct")

    # Join distributions
    combined = df1.select(cols1).join(
        df2.select(cols2), on="letter", how="outer_coalesce", suffix="_df2"
    ).fill_null(0)

    # Calculate components
    combined = combined.with_columns(
        [
            # Words excluded by choosing this letter
            pl.lit(total1).alias("total1"),
            pl.lit(total2).alias("total2"),
            (pl.lit(total1) - pl.col("count")).alias("excluded1"),
            (pl.lit(total2) - pl.col("count_df2")).alias("excluded2"),
        ]
    )

    # Scarcity-adjusted penalty with configurable power
    combined = combined.with_columns(
        [
            (
                (pl.col("excluded1") / pl.col("total1")).pow(scarcity_penalty_power)
                * (100 / np.log(pl.col("total1") + 1))
            ).alias("scarcity_penalty1"),
            (
                (pl.col("excluded2") / pl.col("total2")).pow(scarcity_penalty_power)
                * (100 / np.log(pl.col("total2") + 1))
            ).alias("scarcity_penalty2"),
        ]
    )

    # Base frequency score
    combined = combined.with_columns(frequency_score=(pl.col("percentage") + pl.col("percentage_df2")) / 2)

    # Calculate final score based on available metrics
    if use_quality_scores and "avg_score" in combined.columns:
        # Use score-weighted percentages if available, else regular percentages
        if "score_weighted_pct" in combined.columns:
            combined = combined.with_columns(effective_pct1=pl.col("score_weighted_pct"))
        else:
            combined = combined.with_columns(effective_pct1=pl.col("percentage"))

        if "score_weighted_pct_df2" in combined.columns:
            combined = combined.with_columns(effective_pct2=pl.col("score_weighted_pct_df2"))
        else:
            combined = combined.with_columns(effective_pct2=pl.col("percentage_df2"))

        # Handle missing avg_score columns with defaults
        avg_score1 = pl.col("avg_score") if "avg_score" in combined.columns else pl.lit(50)
        avg_score2 = pl.col("avg_score_df2") if "avg_score_df2" in combined.columns else pl.lit(50)

        # Combined score with quality weighting
        combined = combined.with_columns(
            score=(
                (pl.col("effective_pct1") + pl.col("effective_pct2")) / 2 * frequency_weight
                + (avg_score1 + avg_score2) / 2 * quality_weight
                + (100 - (pl.col("scarcity_penalty1") + pl.col("scarcity_penalty2")) / 2) * scarcity_weight
            ).round(2)
        )

        # Only include avg_score columns in output if they exist
        output_cols = ["letter", "score", "count", "count_df2", "excluded1", "excluded2"]
        if "avg_score" in combined.columns:
            output_cols.append("avg_score")
        if "avg_score_df2" in combined.columns:
            output_cols.append("avg_score_df2")
    else:
        # Score without quality metrics (redistribute quality weight to frequency)
        adjusted_freq_weight = frequency_weight + quality_weight
        combined = combined.with_columns(
            score=(
                pl.col("frequency_score") * adjusted_freq_weight
                + (100 - (pl.col("scarcity_penalty1") + pl.col("scarcity_penalty2")) / 2) * scarcity_weight
            ).round(2)
        )

        output_cols = ["letter", "score", "count", "count_df2", "excluded1", "excluded2"]

    return (
        combined.select(output_cols).rename({"count": "count1", "count_df2": "count2"}).sort("score", descending=True)
    )

def score_single_position(
    df: pl.DataFrame,
    letter_scores: pl.DataFrame,
    position: int,
    word_col: str = "word",
    new_score_col: str = "letter_score",
) -> pl.DataFrame:
    """
    Apply letter scores to words based on the letter at a specific position.

    Parameters
    ----------
    df : pl.DataFrame | dict
        DataFrame with words to score
    letter_scores : pl.DataFrame
        Output from compute_letter_scores with 'letter' and 'score' columns
    position : int
        Position to evaluate (0-indexed)
    word_col : str
        Name of the word column
    new_score_col : str
        Name for the new score column

    Returns
    -------
    pl.DataFrame
        Original dataframe with added score column
    """
    # Create letter lookup dict
    if isinstance(letter_scores, pl.DataFrame):
        letter_scores_map = dict(zip(letter_scores["letter"], letter_scores["score"]))
    else:
        letter_scores_map = letter_scores

    return df.with_columns(
        pl.col(word_col)
        .str.slice(position, 1)
        .str.to_uppercase()
        .replace(letter_scores_map, default=0.0)  # Default 0 for letters not in scoring
        .alias(new_score_col)
    )


def apply_multi_position_scores(
    df: pl.DataFrame, position_scores: dict[int, pl.DataFrame], word_col: str = "word", aggregation: str = "mean", combined_score_col: str = "total_score"
) -> pl.DataFrame:
    """
    Apply letter scores from multiple positions to compute overall word scores.

    Parameters
    ----------
    df : pl.DataFrame
        DataFrame with words to score
    position_scores : dict[int, pl.DataFrame]
        Dictionary mapping positions to their letter score dataframes
    word_col : str
        Name of the word column
    aggregation : str
        How to combine scores ('mean', 'sum', 'min', 'max', 'product')
    combined_score_col : str
        Name of the resulting combined score column

    Returns
    -------
    pl.DataFrame
        DataFrame with individual position scores and combined score
    """
    result = df.clone()
    score_cols = []

    # Add score for each position
    for pos, scores in position_scores.items():
        col_name = f"pos{pos}_score"
        score_cols.append(col_name)
        result = score_single_position(result, scores, pos, word_col, col_name)

    # Combine scores based on aggregation method
    if aggregation == "mean":
        result = result.with_columns(pl.mean_horizontal(score_cols).alias(combined_score_col))
    elif aggregation == "sum":
        result = result.with_columns(pl.sum_horizontal(score_cols).alias(combined_score_col))
    elif aggregation == "min":
        result = result.with_columns(pl.min_horizontal(score_cols).alias(combined_score_col))
    elif aggregation == "max":
        result = result.with_columns(pl.max_horizontal(score_cols).alias(combined_score_col))
    elif aggregation == "product":
        # Product of normalized scores (to keep in reasonable range)
        result = result.with_columns(
            pl.reduce(lambda a, b: a * b / 100, pl.col(score_cols)).alias(combined_score_col)
        )

    # Reorder columns: word, score, word_score, then everything else
    result = result.select(
        [word_col, "score", combined_score_col, pl.exclude([word_col, "score", combined_score_col])]
    )
    return result.sort(combined_score_col, descending=True)


def score_words_by_all_letters(
    df: pl.DataFrame, letter_scores: pl.DataFrame, word_col: str = "word", aggregation: str = "mean"
) -> pl.DataFrame:
    """
    Score words based on ALL their letters using a single letter score mapping.

    Parameters
    ----------
    df : pl.DataFrame
        DataFrame with words to score
    letter_scores : pl.DataFrame
        DataFrame with 'letter' and 'score' columns (typically from compute_letter_scores)
    word_col : str
        Name of the word column
    aggregation : str
        How to combine letter scores ('mean', 'sum', 'min', 'max')

    Returns
    -------
    pl.DataFrame
        DataFrame with added 'word_score' column after word and score columns
    """
    # Create letter->score mapping
    score_dict = dict(zip(letter_scores["letter"], letter_scores["score"]))

    # Split words into individual letters and score each
    result = df.with_columns(
        # Convert word to list of uppercase letters
        letters=pl.col(word_col).str.to_uppercase().str.split("")
    ).with_columns(
        # Map each letter to its score
        letter_scores=pl.col("letters").list.eval(pl.element().replace(score_dict, default=0.0))
    )

    # Aggregate scores based on method
    if aggregation == "mean":
        result = result.with_columns(word_score=pl.col("letter_scores").list.mean())
    elif aggregation == "sum":
        result = result.with_columns(word_score=pl.col("letter_scores").list.sum())
    elif aggregation == "min":
        result = result.with_columns(word_score=pl.col("letter_scores").list.min())
    elif aggregation == "max":
        result = result.with_columns(word_score=pl.col("letter_scores").list.max())

    # Reorder columns: word, score, word_score, then everything else
    result = result.select(
        [word_col, "score", "word_score", pl.exclude([word_col, "score", "word_score", "letters", "letter_scores"])]
    )



    return result.sort("word_score", descending=True)

