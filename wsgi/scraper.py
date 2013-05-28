from urllib2 import quote, urlopen
from urlparse import urljoin
from bs4 import BeautifulSoup
import models


MAGICCARDS_BASE_URL = 'http://magiccards.info/'
MAGICCARDS_QUERY_TMPL = 'query?q=!%s&v=card&s=cname'


class MagiccardsScraper(object):
    """Parses cards info using www.magiccards.info resource"""

    def __init__(self):
        super(MagiccardsScraper, self).__init__()

    def process_cards(self, content):
        """Foreach card parses data from www.magiccards.info.

        :param content: list of tuples (card name, card number)
        :return: list of models.Card
        """
        cards = []

        for c in content:
            page_url = MAGICCARDS_BASE_URL + MAGICCARDS_QUERY_TMPL % quote(c[0])
            page = urlopen(page_url).read()
            soup = BeautifulSoup(page, from_encoding='utf-8')

            data = self._get_card_data(soup)

            cards.append(models.Card(c[0], int(c[1]), **data))

        return cards

    def _get_card_data(self, soup):
        """Parses soup page and returns dict with card info

        :param soup: soup page from www.magiccards.info
        :return: dictionary with card info
        """
        content_table = soup.find_all('table')[3]
        return {'url': self._get_url(content_table),
                'img_url': self._get_img_url(content_table),
                'description': self._get_description(content_table),
                'price': self._get_prices(content_table)}

    def _get_url(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: url of the page with card
        """
        return urljoin(MAGICCARDS_BASE_URL, table.find_all('a')[0]['href'])

    def _get_img_url(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: url of the card image
        """
        return table.find_all('img')[0]['src']

    def _get_description(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: list of paragraphs of card's description
        """
        dirty_descr = str(table.find_all('p', class_='ctext')[0].contents[0])
        clean_descr = dirty_descr.replace('<b>', '').replace('</b>', '').replace('</br>', '').split('<br><br>')
        return clean_descr

    def _get_prices(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: dictionary with prices from TCGPlayer, L-lower, M-middle, H-higher
        """
        prices = {}
        # for key, value in {'TCGPHiLoLow': 'l', 'TCGPHiLoMid': 'm', 'TCGPHiLoHigh': 'h'}.iteritems():
        #     prices[value] = [table.find_all('td', class_=key)[0].descedants[0]]
        return {}