import math
from collections import defaultdict

from pony.orm import db_session, select

# Per your request, the script will use your existing data model.
# The example block below will define a dummy version for demonstration.
from crosscosmos.wordlists import LaFargeWord


class CrosswordHelper:
    """
    Helps find optimal parallel words for crossword construction by maximizing
    potential crossers for specific down-entry lengths.
    """
    def __init__(self):
        """
        Initializes the helper by loading words via Pony ORM and building
        a prefix-and-length frequency map.
        """
        print("Initializing CrosswordHelper...")
        self._words_by_length = defaultdict(list)
        # This now maps: prefix -> {length -> count}
        self._prefix_length_counts = defaultdict(lambda: defaultdict(int))

        self._load_words_from_db()
        self._build_prefix_length_map()
        print("Initialization complete.")

    @db_session
    def _load_words_from_db(self):
        """
        Loads all words and their scores from the database using Pony ORM.
        """
        print("Loading words from database using Pony ORM...")
        all_entries = select(w for w in LaFargeWord)
        for entry in all_entries:
            clean_word = entry.word.upper().strip()
            if clean_word and clean_word.isalpha():
                self._words_by_length[len(clean_word)].append((clean_word, entry.score))
        print(f"Loaded {sum(len(v) for v in self._words_by_length.values())} words.")

    def _build_prefix_length_map(self):
        """
        Builds a map of 2-letter prefix frequencies, segmented by word length.
        """
        print("Building prefix-and-length frequency map...")
        all_word_tuples = [item for sublist in self._words_by_length.values() for item in sublist]
        for word, _ in all_word_tuples:
            if len(word) >= 2:
                prefix = word[:2]
                length = len(word)
                self._prefix_length_counts[prefix][length] += 1
        print(f"Built map with {len(self._prefix_length_counts)} unique prefixes.")

    def find_best_parallel(self, previous_word, down_lengths, top_n=10, word_score_weight=0.3):
        """
        Finds the best-stacking parallel words given specific down-entry lengths.

        Args:
            previous_word (str): The word in the row above (e.g., 'BED').
            down_lengths (tuple): A tuple of integers for the required down-word lengths.
            top_n (int): The number of top results to return.
            word_score_weight (float): The weight for the word's intrinsic score.

        Returns:
            list: A list of (word, score) tuples, sorted by the final score.
        """
        previous_word = previous_word.upper()
        word_len = len(previous_word)

        if word_len != len(down_lengths):
            raise ValueError("Length of 'previous_word' must match length of 'down_lengths' tuple.")

        candidate_words = self._words_by_length.get(word_len, [])
        scored_candidates = []
        stacking_score_weight = 1.0 - word_score_weight

        for candidate_word, word_score in candidate_words:
            stacking_score = 0
            for i in range(word_len):
                prefix = previous_word[i] + candidate_word[i]
                required_length = down_lengths[i]

                # Look up the count for the specific prefix AND required length
                count = self._prefix_length_counts.get(prefix, {}).get(required_length, 0)
                stacking_score += math.log(count + 1)

            normalized_stacking_score = stacking_score / word_len if word_len > 0 else 0

            final_score = (word_score_weight * word_score) + \
                          (stacking_score_weight * normalized_stacking_score)

            scored_candidates.append((candidate_word, final_score))

        scored_candidates.sort(key=lambda item: item[1], reverse=True)
        return scored_candidates[:top_n]

# --- Example Usage ---
if __name__ == '__main__':
    # db = Database()
    #
    # class LaFargeWord(db.Entity):
    #     word = Required(str, unique=True)
    #     score = Required(int)
    #
    # db.bind(provider='sqlite', filename=':memory:')
    # db.generate_mapping(create_tables=True)
    #
    # @db_session
    # def populate_db():
    #     sample_words = [
    #         ('BED', 50), ('ARE', 60), ('ACE', 65), ('ZED', 10),
    #         ('BAD', 50), ('BAG', 45), ('BAT', 52), # 3-letter words starting with B
    #         ('ERA', 60), ('ERE', 40), ('ERG', 30), # 3-letter words starting with E
    #         ('DEB', 30), ('DEE', 35), ('DEN', 58), # 3-letter words starting with D
    #         ('DENT', 70), ('DECK', 60), ('DEEP', 65) # 4-letter words starting with D
    #     ]
    #     for w, s in sample_words:
    #         if not LaFargeWord.exists(word=w):
    #             LaFargeWord(word=w, score=s)
    #
    # populate_db()

    # Initialize the helper
    helper = CrosswordHelper()

    # Find the best words to stack under "BED" with specific down lengths
    previous_word = "AGENT"
    down_lengths = (3, 3, 3, 4, 8) # Require B__, E__, and D___ to have these lengths
    print(f"\nFinding best parallel words for '{previous_word}' with down lengths {down_lengths}:")

    best_words = helper.find_best_parallel(
        previous_word,
        down_lengths,
        top_n=5
    )

    if best_words:
        for word, score in best_words:
            print(f"  - Word: {word}, Score: {score:.4f}")
    else:
        print("No suitable words found.")
