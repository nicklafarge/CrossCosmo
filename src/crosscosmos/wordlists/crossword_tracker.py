"""Scrape words from the crossword tracker website

Source:
    https://crosswordtracker.com
"""

import logging

import requests
from bs4 import BeautifulSoup
from pony import orm
from tqdm import tqdm

from crosscosmos import constants, letter_utils, project_root

logger = logging.getLogger(__name__)


xword_tracker_db_path = project_root / "word_dbs" / "crossword_tracker_words.sqlite"
xword_tracker_word_db = orm.Database()
xword_tracker_word_db.bind(
    provider="sqlite",
    filename=str(xword_tracker_db_path),
    create_db=True,
)


class XwordWord(xword_tracker_word_db.Entity):
    word = orm.PrimaryKey(str)
    info = orm.Required(str)


xword_tracker_word_db.generate_mapping(create_tables=True)


def scrape_crossword_tracker():
    BASE_URL = "https://crosswordtracker.com"
    word_bank = []

    # browse_url = f"{BASE_URL}/browse/"
    browse_url = "https://crosswordtracker.com/browse/"
    browse_html = requests.get(browse_url, verify=False).content
    browse_soup = BeautifulSoup(browse_html, "html.parser")
    letter_pages = browse_soup.find("ul", id="letters").find_all("li")

    words = []
    i = 0
    for i in range(26):
        print(f"--------------- {letter_utils.int2char(i)} ---------------")
        letter_page = letter_pages[i].a["href"]
        letter_url = BASE_URL + letter_page
        letter_soup = BeautifulSoup(requests.get(letter_url, verify=False).content, "html.parser")
        n_pages = int(letter_soup.find("div", id="paginator").find_all("div")[-2].text)
        for j in tqdm(range(1, n_pages + 1)):
            letter_i_url = letter_url + f"?page={j}"
            letter_i_soup = BeautifulSoup(requests.get(letter_i_url, verify=False).content, "html.parser")

            letter_i_box = letter_i_soup.find("div", class_="browse_box")
            words = letter_i_box.find_all("li")
            for w in words:
                word = XwordWord(word=w.text, info=BASE_URL + w.a["href"])
                orm.commit()

if __name__ == "__main__":
    scrape_crossword_tracker()
