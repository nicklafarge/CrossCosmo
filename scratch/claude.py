"""
Crossword Parallel Word Optimizer

Find parallel words that maximize crossing potential for crossword construction.
"""

import heapq
from collections import defaultdict
from typing import NamedTuple

from pony import orm
from pony.orm import db_session

# from pony.orm import *
from crosscosmos.data_models.lafarge_model import LaFargeWord


class WordCandidate(NamedTuple):
    """Represents a word candidate with its crossing potential."""

    word: str
    score: float
    crossing_potential: float
    bigram_counts: list[int]


class CrosswordOptimizer:
    """Optimize parallel word selection for crossword construction."""

    def __init__(self):
        """Initialize the optimizer and build indices."""
        self.bigram_counts = {}  # Cache for bigram frequencies
        self._build_bigram_index()

    @db_session
    def _build_bigram_index(self):
        """Build an index of bigram frequencies from the database."""
        bigram_freq = defaultdict(float)
        word_count = defaultdict(int)

        # Query all words using Pony ORM
        words = LaFargeWord.select()
        # words = select((w.word, w.score) for w in LaFargeWord)[:]

        for row in words:
            word = row.word
            score = row.score
            # for word, score in words:
            if word and len(word) >= 2:
                # Count bigrams at start of words (weighted by score)
                bigram = word[:2].upper()
                bigram_freq[bigram] += score if score else 1.0
                word_count[bigram] += 1

        # Store both weighted frequency and raw count
        self.bigram_counts = {bigram: (freq, word_count[bigram]) for bigram, freq in bigram_freq.items()}

    def get_bigram_potential(self, bigram: str) -> tuple[float, int]:
        """
        Get the crossing potential for a bigram.

        Parameters
        ----------
        bigram : str
            Two-letter combination

        Returns
        -------
        tuple[float, int]
            Weighted frequency and raw count of words starting with bigram
        """
        return self.bigram_counts.get(bigram.upper(), (0.0, 0))

    @db_session
    def evaluate_word_crossing(self, word: str, previous_word: str) -> WordCandidate:
        """
        Evaluate a word's crossing potential given the previous parallel word.

        Parameters
        ----------
        word : str
            Candidate word to evaluate
        previous_word : str
            Previous word in the grid (creates vertical constraints)

        Returns
        -------
        WordCandidate
            Word with calculated crossing potential
        """
        word = word.upper()
        previous_word = previous_word.upper()

        if len(word) != len(previous_word):
            raise ValueError("Words must have same length for parallel placement")

        bigram_counts = []
        total_potential = 0.0

        # Calculate potential for each crossing position
        for i in range(len(word)):
            bigram = previous_word[i] + word[i]
            freq, count = self.get_bigram_potential(bigram)
            bigram_counts.append(count)
            total_potential += freq

        # Get word's own score using Pony ORM
        word_obj = LaFargeWord.get(word=word)
        word_score = word_obj.score if word_obj else 1.0

        return WordCandidate(
            word=word, score=word_score, crossing_potential=total_potential, bigram_counts=bigram_counts
        )

    @db_session
    def evaluate_word_full_stack(self, word: str, word_stack: list[str], down_lengths: list[int]) -> WordCandidate:
        """
        Evaluate a word considering all vertical constraints from previous rows.

        Parameters
        ----------
        word : str
            Candidate word to evaluate
        word_stack : list[str]
            All previous words in the stack
        down_lengths : list[int]
            Required lengths for down words

        Returns
        -------
        WordCandidate
            Word with calculated crossing potential
        """
        word = word.upper()
        word_stack = [w.upper() for w in word_stack]

        if any(len(word) != len(w) for w in word_stack):
            raise ValueError("All words must have same length")

        total_potential = 0.0
        constraint_scores = []

        # For each column, check if vertical word is possible
        for col in range(len(word)):
            # Build vertical constraint string
            vertical = "".join(w[col] for w in word_stack) + word[col]
            required_length = down_lengths[col]

            # Use raw SQL for prefix matching since Pony doesn't support LIKE in queries
            matching_words = LaFargeWord.select(
                lambda w: len(w.word) == required_length and orm.raw_sql("w.word LIKE $vertical || '%'")
            )

            count = matching_words.count()
            score_sum = sum(w.score for w in matching_words)

            constraint_scores.append(count)
            total_potential += score_sum if score_sum else count

        # Get word's own score
        word_obj = LaFargeWord.get(word=word)
        word_score = word_obj.score if word_obj else 1.0

        return WordCandidate(
            word=word, score=word_score, crossing_potential=total_potential, bigram_counts=constraint_scores
        )

    @db_session
    def find_best_parallel_words(
        self, previous_word: str, target_length: int, min_score: float = 0.0, top_k: int = 10
    ) -> list[WordCandidate]:
        """
        Find the best parallel words given constraints.

        Parameters
        ----------
        previous_word : str
            Previous word that creates vertical constraints
        target_length : int
            Required length for parallel words
        min_score : float, optional
            Minimum word score to consider
        top_k : int, optional
            Number of top candidates to return

        Returns
        -------
        list[WordCandidate]
            Top candidates sorted by crossing potential
        """
        # Query candidates using Pony ORM
        word_candidates = (
            LaFargeWord.select(lambda w: len(w.word) == target_length and w.score >= min_score)
            .order_by(orm.desc(LaFargeWord.score))
            .limit(1000)
        )

        # Use heap to maintain top-k efficiently
        candidates = []

        for word_obj in word_candidates:
            if word_obj.word:
                try:
                    candidate = self.evaluate_word_crossing(word_obj.word, previous_word)

                    # Use negative potential for min-heap behavior
                    if len(candidates) < top_k:
                        heapq.heappush(candidates, (-candidate.crossing_potential, candidate))
                    elif candidate.crossing_potential > -candidates[0][0]:
                        heapq.heapreplace(candidates, (-candidate.crossing_potential, candidate))

                except ValueError:
                    continue

        # Extract and sort results
        results = [candidate for _, candidate in candidates]
        return sorted(results, key=lambda x: x.crossing_potential, reverse=True)

    def find_optimal_word_stack(
        self, starting_word: str, down_lengths: list[int], num_rows: int, min_score: float = 0.0
    ) -> list[list[WordCandidate]]:
        """
        Find optimal stack of parallel words.

        Parameters
        ----------
        starting_word : str
            First word in the grid
        down_lengths : list[int]
            Required lengths for down words at each position
        num_rows : int
            Number of parallel words to find
        min_score : float, optional
            Minimum word score threshold

        Returns
        -------
        list[list[WordCandidate]]
            Best candidates for each row
        """
        word_length = len(starting_word)
        stack_candidates = []

        # First row is given
        current_word = starting_word.upper()

        # Find candidates for each subsequent row
        for row in range(1, num_rows):
            candidates = self.find_best_parallel_words(
                current_word,
                word_length,
                min_score=min_score,
                top_k=20,  # Get more candidates for flexibility
            )

            if not candidates:
                print(f"Warning: No valid candidates found for row {row}")
                break

            stack_candidates.append(candidates)

            # Use best candidate for next iteration
            # (Could implement beam search for better global optimization)
            current_word = candidates[0].word

        return stack_candidates

    @db_session
    def find_optimal_word_stack_advanced(
        self, starting_word: str, down_lengths: list[int], num_rows: int, min_score: float = 0.0, beam_width: int = 3
    ) -> list[list[str]]:
        """
        Find optimal stack using beam search with full vertical constraints.

        Parameters
        ----------
        starting_word : str
            First word in the grid
        down_lengths : list[int]
            Required lengths for down words at each position
        num_rows : int
            Number of parallel words to find
        min_score : float, optional
            Minimum word score threshold
        beam_width : int, optional
            Number of partial solutions to maintain at each level

        Returns
        -------
        list[list[str]]
            Best complete stacks found
        """
        word_length = len(starting_word)

        # Initialize beam with starting word
        beam = [([starting_word.upper()], 0.0)]

        for row in range(1, num_rows):
            new_beam = []

            for word_stack, stack_score in beam:
                # Get candidates for next row using Pony ORM

                candidates = (
                    LaFargeWord.select(lambda w: len(w.word) == word_length and w.score >= min_score)
                    .order_by(orm.desc(LaFargeWord.score))
                    .limit(100)
                )

                # Evaluate each candidate
                for word in candidates:
                    if word:
                        try:
                            candidate = self.evaluate_word_full_stack(word, word_stack, down_lengths)

                            # Only consider if all constraints can be satisfied
                            if all(c > 0 for c in candidate.bigram_counts):
                                new_stack = word_stack + [candidate.word]
                                new_score = stack_score + candidate.crossing_potential
                                new_beam.append((new_stack, new_score))
                        except:
                            continue

            # Keep top beam_width solutions
            new_beam.sort(key=lambda x: x[1], reverse=True)
            beam = new_beam[:beam_width]

            if not beam:
                print(f"No valid solutions found at row {row}")
                break

        return [stack for stack, score in beam]

    @db_session
    def find_words_for_gap(
        self,
        fixed_words: list[tuple[int, str]],
        target_row: int,
        down_lengths: list[int],
        min_score: float = 0.0,
        top_k: int = 10,
    ) -> list[WordCandidate]:
        """
        Find words that fit in a gap between fixed words.

        Parameters
        ----------
        fixed_words : list[tuple[int, str]]
            List of (row_index, word) tuples for fixed words
        target_row : int
            Row index where we need to find a word
        down_lengths : list[int]
            Required lengths for down words at each position
        min_score : float, optional
            Minimum word score threshold
        top_k : int, optional
            Number of top candidates to return

        Returns
        -------
        list[WordCandidate]
            Best words that satisfy all crossing constraints
        """
        # Sort fixed words by row index
        fixed_words = sorted(fixed_words, key=lambda x: x[0])
        word_length = len(fixed_words[0][1])

        # Validate all words have same length
        if not all(len(word) == word_length for _, word in fixed_words):
            raise ValueError("All fixed words must have same length")

        # Build constraint patterns for each column
        column_constraints = []
        for col in range(word_length):
            constraint = ["?"] * max(down_lengths[col], max(row for row, _ in fixed_words) + 1)

            # Fill in known letters
            for row, word in fixed_words:
                if row < len(constraint):
                    constraint[row] = word[col].upper()

            # Extract the pattern we need
            if target_row < len(constraint):
                pattern = "".join(constraint[: down_lengths[col]])
                column_constraints.append((col, pattern, target_row))
            else:
                column_constraints.append((col, None, target_row))

        # Find candidates using Pony ORM
        word_candidates = (
            LaFargeWord.select(lambda w: len(w.word) == word_length and w.score >= min_score)
            .order_by(orm.desc(LaFargeWord.score))
            .limit(500)
        )

        candidates = []
        for word_obj in word_candidates:
            if not word_obj.word:
                continue

            word = word_obj.word.upper()
            valid = True
            crossing_potential = 0.0
            valid_crossings = []

            # Check each column constraint
            for col, pattern, row_pos in column_constraints:
                if pattern and row_pos < len(pattern):
                    # Build the potential vertical word
                    test_pattern = pattern[:row_pos] + word[col] + pattern[row_pos + 1 :]

                    # For complex pattern matching, we'll fetch and filter in Python
                    # This is more efficient than complex SQL for pattern matching
                    all_words_of_length = LaFargeWord.select(lambda w: len(w.word) == len(pattern))[
                        :
                    ]  # Fetch all at once

                    # Filter for pattern match in Python
                    matching_words = []
                    for w in all_words_of_length:
                        word_upper = w.word.upper()
                        if all(
                            word_upper[i] == test_pattern[i] for i in range(len(test_pattern)) if test_pattern[i] != "?"
                        ):
                            matching_words.append(w)

                    count = len(matching_words)
                    score_sum = sum(w.score for w in matching_words)

                    # count = matching_words.count()
                    # score_sum = sum(w.score for w in matching_words)

                    if count == 0:
                        valid = False
                        break

                    valid_crossings.append(count)
                    crossing_potential += score_sum if score_sum else count

            if valid:
                candidate = WordCandidate(
                    word=word,
                    score=word_obj.score,
                    crossing_potential=crossing_potential,
                    bigram_counts=valid_crossings,
                )

                if len(candidates) < top_k:
                    heapq.heappush(candidates, (-candidate.crossing_potential, candidate))
                elif candidate.crossing_potential > -candidates[0][0]:
                    heapq.heapreplace(candidates, (-candidate.crossing_potential, candidate))

        # Extract and sort results
        results = [candidate for _, candidate in candidates]
        return sorted(results, key=lambda x: x.crossing_potential, reverse=True)


# Example usage and testing
def demonstrate_usage():
    """Demonstrate the crossword optimizer functionality."""

    # Initialize optimizer
    optimizer = CrosswordOptimizer()

    # Example: Find best words to follow "BED"
    starting_word = "SLOOK"
    down_lengths = [3, 3, 3, 4, 8]  # Constraints for down words

    print(f"Starting word: {starting_word}")
    print(f"Down constraints: {down_lengths}")
    print("-" * 50)

    # Find best candidates for second row
    candidates = optimizer.find_best_parallel_words(starting_word, 3, top_k=5)

    print("\nTop candidates for second row:")
    for i, candidate in enumerate(candidates, 1):
        print(f"{i}. {candidate.word} (score: {candidate.score:.2f}, potential: {candidate.crossing_potential:.2f})")
        print("   Bigram counts: ", end="")
        for j, (prev_letter, curr_letter, count) in enumerate(
            zip(starting_word, candidate.word, candidate.bigram_counts)
        ):
            print(f"{prev_letter}{curr_letter}:{count}", end=" ")
        print()

    # Find optimal stack
    print("\n" + "=" * 50)
    print("Finding optimal word stack...")

    stack = optimizer.find_optimal_word_stack(starting_word, down_lengths, num_rows=5, min_score=50.0)

    print(f"\nOptimal stack starting with {starting_word}:")
    print(starting_word)
    for row_num, candidates in enumerate(stack, 2):
        if candidates:
            best = candidates[0]
            print(f"Row {row_num}: {best.word} (potential: {best.crossing_potential:.2f})")


def demonstrate_gap_filling():
    """Demonstrate gap-filling functionality."""

    print("\n" + "=" * 50)
    print("Gap Filling Demonstration")
    print("=" * 50)

    optimizer = CrosswordOptimizer()

    # Define the gap problem
    fixed_words = [(0, "SLOOKS"), (2, "DMYBEE")]
    target_row = 1
    down_lengths = [5, 5, 4, 5, 5, 5]  # All down words are 3 letters

    print("Fixed grid pattern:")
    print("Row 0: B E D")
    print("Row 1: ? ? ?")
    print("Row 2: R A P")
    print(f"\nDown word lengths: {down_lengths}")

    # Find words that fit in the gap
    gap_candidates = optimizer.find_words_for_gap(fixed_words, target_row, down_lengths, top_k=50)

    print(f"\nTop candidates for row {target_row}:")
    for i, candidate in enumerate(gap_candidates, 1):
        print(f"{i}. {candidate.word} (score: {candidate.score:.2f}, potential: {candidate.crossing_potential:.2f})")

        # Show the resulting down words
        print("   Forms down words: ", end="")
        for col, letter in enumerate(candidate.word):
            down_word = f"{fixed_words[0][1][col]}{letter}{fixed_words[1][1][col]}"
            print(f"{down_word}", end=" ")
        print(f"(valid crossings: {candidate.bigram_counts})")


if __name__ == "__main__":
    # Run demonstrations
    print("Running Crossword Optimizer with Pony ORM...")

    # demonstrate_usage()
    # demonstrate_gap_filling()


    ####################################################################################
    # Demonstrate gap-filling functionality.
    ####################################################################################

    print("\n" + "=" * 50)
    print("Gap Filling Demonstration")
    print("=" * 50)

    optimizer = CrosswordOptimizer()

    # Define the gap problem
    fixed_words = [(0, "SLOOKS"), (2, "DMYBEE")]
    target_row = 1
    down_lengths = [5, 5, 4, 5, 5, 5]  # All down words are 3 letters

    print("Fixed grid pattern:")
    print("Row 0: B E D")
    print("Row 1: ? ? ?")
    print("Row 2: R A P")
    print(f"\nDown word lengths: {down_lengths}")

    # Find words that fit in the gap
    gap_candidates = optimizer.find_words_for_gap(fixed_words, target_row, down_lengths, top_k=50)

    print(f"\nTop candidates for row {target_row}:")
    for i, candidate in enumerate(gap_candidates, 1):
        print(f"{i}. {candidate.word} (score: {candidate.score:.2f}, potential: {candidate.crossing_potential:.2f})")

        # Show the resulting down words
        print("   Forms down words: ", end="")
        for col, letter in enumerate(candidate.word):
            down_word = f"{fixed_words[0][1][col]}{letter}{fixed_words[1][1][col]}"
            print(f"{down_word}", end=" ")
        print(f"(valid crossings: {candidate.bigram_counts})")
