""" """

import polars as pl
from spellchecker import SpellChecker

import crosscosmos as xc

spell = SpellChecker()

sunday = xc.constants.NYT_SUNDAY_SIZE
cols = ["word", "score", "length"]

min_score = 40

df = xc.Query(db=xc.LaFargeWord, default=False,  limit=None).min_score(min_score).df()

refine_kwargs = {
    "min_score": min_score,
    "max_length": 15
}

def find_words(_df, word):

    word_set = set(_df["word"].to_list())
    word_set.remove("ING")
    word_set.remove("TIC")
    word_set.remove("ISH")
    word_set.remove("EST")

    result_df = (
        _df.filter(pl.col("word").str.starts_with(word))  # Only process relevant rows
        .with_columns([pl.col("word").str.slice(len(word)).alias("second_part")])
        .filter(pl.col("second_part").str.len_chars() >= 3)  # Length filter
    )

    # Get unique second parts to minimize expensive xc.search calls
    unique_second_parts = set(result_df["second_part"].to_list())

    # Batch compute scores for unique second parts only
    second_part_scores = {}
    for part in unique_second_parts:
        if part in word_set:  # Only compute score if word exists in dataset
            try:
                second_part_scores[part] = df.filter(pl.col("word")==part)["score"].item()
            except (KeyError, IndexError):
                continue  # Skip if search fails

    # Apply filters efficiently
    valid_rows = []
    for row in result_df.iter_rows(named=True):
        second_part = row["second_part"]
        if second_part not in second_part_scores:
            continue
        if second_part_scores[second_part] < min_score:
            continue

        valid_rows.append({"word": row["word"], "score": row["score"], "pt1": word, "pt2": second_part})

    if not valid_rows:
        return pl.DataFrame(schema={"word": str, "score": float, "pt1": str, "pt2": str})

    # Convert to DataFrame and apply spell check
    result_pl = pl.DataFrame(valid_rows)

    # Vectorized spell check filtering
    known_words = [row["word"] for row in valid_rows if spell.known([row["word"]])]
    return result_pl.filter(pl.col("word").is_in(known_words))



df_cool2 = find_words(df, "COOL")
df_lit2 = find_words(df, "LIT")
df_fire2 = find_words(df, "FIRE")
df_dope2 = find_words(df, "DOPE")
df_sick2 = find_words(df, "SICK")
df_tight2 = find_words(df, "TIGHT")
df_fly2 = find_words(df, "FLY")
df_bomb2 = find_words(df, "BOMB")

df_ace2 = find_words(df, "ACE")
df_fresh2 = find_words(df, "FRESH")
df_sweet2 = find_words(df, "SWEET")
df_wicked2 = find_words(df, "WICKED")
df_killer2 = find_words(df, "KILLER")
df_stellar2 = find_words(df, "STELLAR")
df_bangin2 = find_words(df, "BANGIN")
df_phat2 = find_words(df, "PHAT")
df_ill2 = find_words(df, "ILL")
df_trill2 = find_words(df, "trill")

df_hot2 = find_words(df, "hot")
df_choice2 = find_words(df, "choice")

df_dank2 = find_words(df, "DANK")

df_solid2 = find_words(df, "SOLID")
df_mad2 = find_words(df, "MAD")
df_rad2 = find_words(df, "RAD")
df_epic2 = find_words(df, "EPIC")
df_clutch2 = find_words(df, "CLUTCH")
df_savage2 = find_words(df, "SAVAGE")
df_legit2 = find_words(df, "LEGIT")
df_fierce2 = find_words(df, "FIERCE")