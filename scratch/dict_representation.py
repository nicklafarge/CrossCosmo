"""
"""
import timeit
import polars as pl

import crosscosmos as xc
from crosscosmos import Refiner, WordMap

max_len = 10

corpus = xc.Corpus()
df = corpus.df
refiner = xc.Refiner(df)
word_map = WordMap(df)

word_len = 8
def test1():
    return [w for w, s in word_map.words[word_len][0]['A'] if w[2] == "A" and w[6] == "D"]

def test2():
    return df.filter(
        (pl.col("word").str.len_chars() == word_len) &
        (pl.col("word").str.slice(0, 1) == "A") &
        (pl.col("word").str.slice(2, 1) == "A") &
        (pl.col("word").str.slice(6, 1) == "D")
    )["word"]


def test3():
    return (xc.Refiner(df)
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

def test8():
    return 10

if __name__ == '__main__':
    import timeit
    v1 = test1()
    v2 = test2()
    v3 = test3()
    v4 = test4()
    # v5 = test5()
    # v6 = test6()
    # v7 = test7()
    # v8 = test8()


    print(timeit.timeit("test3()", globals=locals(), number=100))
    print(timeit.timeit("test4()", globals=locals(), number=100))
    # print(timeit.timeit("test5()", globals=locals(), number=100))
    # print(timeit.timeit("test6()", globals=locals(), number=100))
    # print(timeit.timeit("test7()", globals=locals(), number=100))
    # print(timeit.timeit("test8()", globals=locals(), number=100))
