import re
import itertools
import urlparse
import eventlet
from eventlet.green import urllib2
from bs4 import BeautifulSoup
import models


def resolve_cards_async(content):
    """Parses card info using MagiccardScrapper in thread for request mode

    :param content: list of (card_name, card_number) tuples
    :return: list of models.Card objects
    """
    pool = eventlet.GreenPool(len(content))
    return [card for card in pool.imap(MagiccardsScraper.resolve_card, content)]


def get_tcg_sellers_async(cards):
    """Parses TCGPlayer sellers that could sell specified cards

    :param cards: list of models.Card objects
    :return: list of models.TCGSeller objects
    """
    unique_sellers = {}
    pool = eventlet.GreenPool(len(cards))
    for card, sellers_groups in pool.imap(get_tcg_card_sellers, cards):
        for sellers_group in sellers_groups:
            if sellers_group[0].name not in unique_sellers:
                unique_sellers[sellers_group[0].name] = models.TCGSeller(sellers_group[0].name, sellers_group[0].url,
                                                                         sellers_group[0].rating, sellers_group[0].sales)

            for seller in sellers_group:
                unique_sellers[seller.name].add_card(card, seller.condition, seller.number, seller.price)

    sellers = sorted([v for k, v in unique_sellers.items()],
                     key=lambda s: s.get_available_cards_num(cards), reverse=True)

    return sellers


def get_tcg_card_sellers(card):
    """Parses TCGPlayer sellers list for specified card

    :param card: models.Card object
    :return: tuple (models.Card, list(models.TCGCardSeller))
    """
    tcg_scrapper = TCGPlayerScrapper(card.prices.sid)
    return card, tcg_scrapper.get_full_info()


class MagiccardsScraper(object):
    """
    Parses cards info using www.magiccards.info resource
    """

    MAGICCARDS_BASE_URL = 'http://magiccards.info/'
    MAGICCARDS_QUERY_TMPL = 'query?q=!%s&v=card&s=cname'

    def __init__(self, name, number):
        self.name = name
        self.number = number

    @staticmethod
    def resolve_card(content_record):
        """Parses card info

        :param content_record: (card_name, card_number) tuple
        :return: models.Card object
        """
        scrapper = MagiccardsScraper(content_record[0], content_record[1])
        return scrapper.get_card()

    def get_card(self):
        """Parses card info, if no info returns card object without info and prices

        :return: models.Card object
        """
        page_url = self.MAGICCARDS_BASE_URL + self.MAGICCARDS_QUERY_TMPL % urllib2.quote(self.name)

        try:
            page = urllib2.urlopen(page_url).read()
            soup = BeautifulSoup(page, from_encoding='utf-8')

            info = self._get_card_info(soup)
            price = self._get_prices(soup)

            card_info = models.CardInfo(**info)
            card_prices = models.CardPrices(**price)
        except:
            return models.Card(self.name, int(self.number))
        else:
            return models.Card(self.name, int(self.number), info=card_info, prices=card_prices)

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
        return urlparse.urljoin(MagiccardsScraper.MAGICCARDS_BASE_URL, table.find_all('a')[0]['href'])

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
    FULL_BASE_URL = 'http://store.tcgplayer.com/productcatalog/product/getpricetable' \
                    '?captureFeaturedSellerData=True&pageSize=50&productId='
    FULL_URL_COOKIE = ('Cookie', 'SearchCriteria=WantGoldStar=False&MinRating=0&MinSales='
                                 '&magic_MinQuantity=1&GameName=Magic')

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
        """Parses summary price info for card

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

    def get_full_info(self):
        """Parses sellers info for card

        :return: list of models.TCGSeller objects
        """
        opener = urllib2.build_opener()
        opener.addheaders.append(self.FULL_URL_COOKIE)

        sellers = []
        link = self.full_url
        while True:
            tcg_response = opener.open(link).read()
            soup = BeautifulSoup(tcg_response)

            sellers_blocks = soup.find('table', class_='priceTable').find_all('tr', class_='vendor')
            for block in sellers_blocks:
                seller_td = block.find('td', class_='seller')
                name = seller_td.find_all('a')[0].text.strip()
                url = self._get_domain(self.full_url) + seller_td.find_all('a')[0]['href']
                rating = str(seller_td.find('span', class_='actualRating').find('a').contents[0]).strip().split()[1]
                sales = str(seller_td.find('span', class_='ratingHeading').find('a').contents[0]).strip()
                number = int(block.find('td', class_='quantity').text.strip())
                price = str(block.find('td', class_='price').contents[0]).strip()
                condition = str(block.find('td', class_='condition').find('a').contents[0]).strip()

                seller = models.TCGCardSeller(self.sid, name, url, rating, sales, number, price, condition)
                sellers.append(seller)

            pager_block = soup.find('div', class_='pricePager')
            next_link_tag = pager_block.find('a', text=re.compile(r'Next'))
            if 'disabled' in next_link_tag.attrs:
                break

            link = self._get_domain(self.full_url) + next_link_tag['href']

        grouped_sellers = [list(g) for k, g in itertools.groupby(sellers, key=lambda s: s.name)]

        return grouped_sellers

    def _get_domain(self, url):
        """
        Removes path part of url
        """
        decomposed = urlparse.urlparse(url)
        return decomposed.scheme + '://' + decomposed.hostname

    def _clear_url_from_partner(self, url):
        """
        Removes from url magiccard partner info
        """
        decomposed = urlparse.urlparse(url)
        return decomposed.scheme + '://' + decomposed.hostname + decomposed.path
