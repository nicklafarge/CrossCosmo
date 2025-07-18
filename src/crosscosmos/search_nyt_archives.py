from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import polars as pl
from pathlib import Path
from datetime import datetime
import time


def scrape_citations(url: str) -> pl.DataFrame:
    """
    Scrape citations from a webpage and return as a Polars DataFrame.

    Parameters
    ----------
    url : str
        The URL to scrape citations from

    Returns
    -------
    pl.DataFrame
        DataFrame with columns 'source_name' and 'date'

    Raises
    ------
    Exception
        If the web scraping fails
    """
    # Setup Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Load the page
        driver.get(url)

        # Wait for page to load and look for the View All button
        wait = WebDriverWait(driver, 10)

        try:
            # Find and click the View All button
            view_all_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "view-all")))
            view_all_button.click()

            # Wait a moment for content to load after clicking
            time.sleep(2)

        except Exception:
            # If View All button not found, continue with existing content
            pass

        # Get the page source after JavaScript execution
        page_source = driver.page_source

    finally:
        driver.quit()

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(page_source, "html.parser")

    # Find the citations ul element
    citations_ul = soup.find("ul", class_="citations")
    if not citations_ul:
        raise ValueError("No ul element with class 'citations' found")

    # Extract citation data
    citations = []
    for li in citations_ul.find_all("li"):
        text = li.get_text(strip=True)
        if " - " in text:
            source_name, date_str = text.rsplit(" - ", 1)
            citations.append({"source_name": source_name.strip(), "date": date_str.strip()})

    # Create DataFrame
    return pl.DataFrame(citations)


def parse_date_string(date_str: str) -> datetime | None:
    """
    Parse date string in multiple formats to datetime object.

    Supports formats:
    - 'Jul. 05, 2013' (abbreviated with period)
    - 'April 21, 2022' (full month name)
    - 'Jul 05, 2013' (abbreviated without period)

    Parameters
    ----------
    date_str : str
        Date string to parse

    Returns
    -------
    datetime | None
        Parsed datetime object or None if parsing fails
    """
    date_formats = [
        "%b. %d, %Y",  # Jul. 05, 2013
        "%B %d, %Y",  # April 21, 2022
        "%b %d, %Y",  # Jul 05, 2013
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


if __name__ == "__main__":
    url = "http://crosswordtracker.com/answer/adhoc/?search_redirect=True"
    df = scrape_citations(url)

    # Optionally convert date strings to datetime objects
    df = df.with_columns(pl.col("date").map_elements(parse_date_string, return_dtype=pl.Datetime).alias("parsed_date"))
