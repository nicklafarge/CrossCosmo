"""
"""
import timeit
import polars as pl

import crosscosmos as xc
from crosscosmos import Refiner, WordMap

max_len = 10
df = xc.Query(q=3, limit=None).max_length(10).df()
df = xc.Refiner(df).df()
refiner = xc.Refiner(df)
word_map = WordMap(df)

word_idx_map = {i: {j : {c: [] for c in xc.constants.ALPHABET} for j in range(max_len)} for i in range(1, max_len+1)}

for w in df.iter_rows(named=True):
    for i, c in enumerate(w["word"]):
        word_idx_map[w["length"]][i][c].append(w["word"])

word_len = 8
def test1():
    return [w for w in word_map.words[word_len][0]['A'] if w[2] == "A" and w[6] == "D"]

def test2():
    return df.filter(
        (pl.col("word").str.len_chars() == word_len) &
        (pl.col("word").str.slice(0, 1) == "A") &
        (pl.col("word").str.slice(2, 1) == "A") &
        (pl.col("word").str.slice(6, 1) == "D")
    )["word"]


def test3():
    return (xc.Refiner(df, default=False, alpha_only=False)
            .length(word_len)
            .fix_letter(0, "A")
            .fix_letter(2, "A")
            .fix_letter(6, "D")
            .df()
            )
    return df.filter(
        (pl.col("word").str.len_chars() == word_len) &
        (pl.col("word").str.slice(0, 1) == "A") &
        (pl.col("word").str.slice(2, 1) == "A") &
        (pl.col("word").str.slice(6, 1) == "E")
    )["word"]

def test4():
    return word_map.filter_by_letters(
        word_len,
        {0: "A", 2: "A", 6: "D"}
    )

def test5():
    return word_map.match("A?A???D?")
    return word_map.filter_by_letters(
        word_len,
        {0: "A", 2: "A", 6: "E"}
    )

def test6():
    return word_map.filter_by_letters(
        word_len,
        {2: "A", 6: "D"}
    )

def test7():
    return word_map.filter_by_letters(
        word_len,
        {2: "A", 6: {"A", "C", "L"}}
    )

if __name__ == '__main__':
    import timeit
    print(timeit.timeit("test1()", globals=locals(), number=30))
    print(timeit.timeit("test2()", globals=locals(), number=30))
    print(timeit.timeit("test3()", globals=locals(), number=30))
    print(timeit.timeit("test4()", globals=locals(), number=30))
    print(timeit.timeit("test5()", globals=locals(), number=30))
    print(timeit.timeit("test6()", globals=locals(), number=30))
    print(timeit.timeit("test7()", globals=locals(), number=30))

    v1 = test1()
    v2 = test2()
    v3 = test3()
    v4 = test4()
    v5 = test5()
    v6 = test6()
    v7 = test7()
