import random
import requests
from bs4 import BeautifulSoup
import re
import logging


class Scraper:
    def __init__(self, url, character_limit=2000):
        self.url = url
        self.character_limit = character_limit

    def fetch_content(self) -> dict:
        logging.info(f"Fetching content from {self.url}")
        response = requests.get(self.url)
        if response.status_code == 200:
            return self.parse(response.text)
        return {}

    def parse(self, content):
        soup = BeautifulSoup(content, 'html.parser')

        for element in soup.find_all(["href"]):
            element.decompose()

        for script in soup(["script", "style"]):
            script.extract()

        all_text = soup.get_text()

        lines = (line.strip() for line in all_text.splitlines())

        all_text_clean = re.sub(r'\s+', ' ', (' '.join(line for line in lines if line)))
        all_text_clean = all_text_clean.replace("  ", " ").replace('\\n', '')
        return all_text_clean


class RssScrap(Scraper):

    def parse(self, content) -> dict:
        news = []
        try:
            soup = BeautifulSoup(content, 'lxml')
            for item in soup.find_all('item'):
                image = item.find('enclosure')
                if image:
                    image = image.get('url')
                if not image:
                    image = item.find('media:thumbnail').get('url')
                news.append({
                    'title': item.find('title').text,
                    'link': item.find('link').text,
                    'description': item.find('description').text,
                    'image': image
                })
        except Exception as e:
            logging.error(f"Error: {e}")
        finally:
            random.shuffle(news)
            chosen_rss = news[0]
            return chosen_rss


if __name__ == '__main__':
    url = 'https://www.newscientist.com/subject/space/feed/'
    scraper = RssScrap(url)
    print(scraper.fetch_content())
