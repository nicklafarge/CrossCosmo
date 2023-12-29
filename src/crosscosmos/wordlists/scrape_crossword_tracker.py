""" Scrape words from the crossword tracker website

Source:
    https://crosswordtracker.com
"""

# Standard library imports
import logging

# Third-party imports
from bs4 import BeautifulSoup
import requests
from tqdm import tqdm

# Local imports
import crosscosmos as xc
from crosscosmos.data_models import xword_tracker_model

logger = logging.getLogger(__name__)


BASE_URL = "https://crosswordtracker.com"
word_bank = []

# browse_url = f"{BASE_URL}/browse/"
browse_url = "https://crosswordtracker.com/browse/"
browse_html = requests.get(browse_url).content
browse_soup = BeautifulSoup(browse_html, 'html.parser')
letter_pages = browse_soup.find("ul", id="letters").find_all("li")

i = 0
for i in range(26):
    print(f"--------------- {xc.letter_utils.int2char(i)} ---------------")
    letter_page = letter_pages[i].a['href']
    letter_url = BASE_URL + letter_page
    letter_soup = BeautifulSoup(requests.get(letter_url).content,
                                'html.parser')
    n_pages = int(letter_soup.find("div", id="paginator").find_all('div')[-2].text)
    for j in tqdm(range(1, n_pages + 1)):
        letter_i_url = letter_url + f"?page={j}"
        letter_i_soup = BeautifulSoup(requests.get(letter_i_url).content,
                                      'html.parser')

        letter_i_box = letter_i_soup.find('div', class_="browse_box")
        words = letter_i_box.find_all('li')
        for w in words:
            word = xword_tracker_model.XwordWord(word=w.text, info=BASE_URL+w.a['href'])
            xword_tracker_model.orm.commit()