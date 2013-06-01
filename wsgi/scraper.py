import urllib2
import urlparse
from bs4 import BeautifulSoup
import models


class MagiccardsScraper(object):
    """Parses cards info using www.magiccards.info resource"""

    MAGICCARDS_BASE_URL = 'http://magiccards.info/'
    MAGICCARDS_QUERY_TMPL = 'query?q=!%s&v=card&s=cname'

    def __init__(self):
        super(MagiccardsScraper, self).__init__()

    def process_cards(self, content):
        """Foreach card parses data from www.magiccards.info.

        :param content: list of tuples (card name, card number)
        :return: list of models.Card
        """
        cards = []

        for c in content:
            page_url = self.MAGICCARDS_BASE_URL + self.MAGICCARDS_QUERY_TMPL % urllib2.quote(c[0])
            page = urllib2.urlopen(page_url).read()
            soup = BeautifulSoup(page, from_encoding='utf-8')

            info = self._get_card_info(soup)
            price = self._get_prices(soup)

            card_info = models.CardInfo(**info)
            card_prices = models.CardPrices(**price)
            card = models.Card(c[0], int(c[1]), info=card_info, prices=card_prices)

            cards.append(card)

        return cards

    def _get_card_info(self, soup):
        """Parses soup page and returns dict with card info

        :param soup: soup page from www.magiccards.info
        :return: dictionary with card info
        """
        content_table = soup.find_all('table')[3]
        return {'url': self._get_url(content_table),
                'img_url': self._get_img_url(content_table),
                'description': self._get_description(content_table)}

    def _get_url(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: url of the page with card
        """
        return urlparse.urljoin(self.MAGICCARDS_BASE_URL, table.find_all('a')[0]['href'])

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

    def _get_prices(self, magic_soup):
        """Parses prices by TCGPlayer card sid

        :param magic_soup: soup page from www.magiccards.info
        :return: dictionary with prices from TCGPlayer in format {sid, low, mid, high}
        """
        content_table = magic_soup.find_all('table')[3]
        request_url = content_table.find_all('script')[0]['src']
        sid = urlparse.parse_qs(urlparse.urlparse(request_url).query)['sid'][0]

        tcg_scrapper = TCGPlayerScrapper(sid)

        return tcg_scrapper.get_brief_info()


class TCGPlayerScrapper(object):
    """
    Parses card prices from TCGPlayer using its sid
    """

    BRIEF_BASE_URL = 'http://partner.tcgplayer.com/x3/mchl.ashx?pk=MAGCINFO&sid='
    FULL_BASE_URL = 'http://partner.tcgplayer.com/x3/mcpl.ashx?pk=MAGCINFO&sid='

    def __init__(self, sid):
        self.sid = sid

    @property
    def brief_url(self):
        """
        Url to summary card prices
        """
        return self.BRIEF_BASE_URL + self.sid

    @property
    def full_url(self):
        """
        Url to table with seller <-> count <-> price data
        """
        return self.FULL_BASE_URL + self.sid

    def get_brief_info(self):
        """
        Parses summary price info for card
        :return: dictionary {sid, tcg card url, low, mid, high}
        """
        tcg_response = urllib2.urlopen(self.brief_url).read()
        html_response = tcg_response.replace('\'+\'', '').replace('\\\'', '"')[16:][:-3]

        tcg_soup = BeautifulSoup(html_response)

        prices = {'sid': self.sid,
                  'url': self._clear_url_from_partner(tcg_soup.find('td', class_='TCGPHiLoLink').contents[0]['href']),
                  'low': str(tcg_soup.find('td', class_='TCGPHiLoLow').contents[1].contents[0]),
                  'mid': str(tcg_soup.find('td', class_='TCGPHiLoMid').contents[1].contents[0]),
                  'high': str(tcg_soup.find('td', class_='TCGPHiLoHigh').contents[1].contents[0])}

        return prices

    def _clear_url_from_partner(self, url):
        """
        Removes from url magiccard partner info
        """
        decomposed = urlparse.urlparse(url)
        return decomposed.scheme + '://' + decomposed.hostname + decomposed.path