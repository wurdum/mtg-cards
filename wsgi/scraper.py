# coding=utf-8
import re
import itertools
import eventlet
from eventlet.green import urllib2
from bs4 import BeautifulSoup
import models
import ext


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
    :return: list of models.TCGSeller objects with filled cards property
    """
    sellers = []
    pool = eventlet.GreenPool(len(cards))
    for card, sellers_offers in pool.imap(get_tcg_card_offers, cards):
        for seller_offers in sellers_offers:
            seller = ext.get_first(sellers, lambda s: s == seller_offers['seller'])
            if seller is None:
                seller = seller_offers['seller']
                sellers.append(seller)

            for offer in seller_offers['offers']:
                seller.add_card_offer(card, offer)

    return sellers


def get_tcg_card_offers(card):
    """Parses TCGPlayer sellers list for specified card

    :param card: models.Card object
    :return: tuple (models.Card, dict {'seller': models.TCGSeller, 'offers': list of models.TCGCardOffer})
    """
    tcg_scrapper = TCGPlayerScrapper(card.prices.sid)
    return card, tcg_scrapper.get_full_info()


def get_buymagic_offers_async(cards):
    """Parses async www.buymagic.ua to obtain offers

    :param cards: list of models.Card objects
    :return: dict {models.Card: models.ShopOffer}
    """
    offers = {}
    pool = eventlet.GreenPool(len(cards))
    for card, card_offers in pool.imap(BuyMagicScrapper.get_offers, cards):
        offers[card] = card_offers

    return offers


def get_spellshop_offers_async(cards):
    """Parses async www.spellshop.com.ua to obtain offers

    :param cards: list of models.Card objects
    :return: dict {models.Card: models.ShopOffer}
    """
    offers = {}
    pool = eventlet.GreenPool(len(cards))
    for card, offer in pool.imap(SpellShopScrapper.get_offers, cards):
        offers[card] = offer

    return offers


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

            if not self._is_card_page(soup):
                hint = self._try_get_hint(soup)
                if hint is not None:
                    page_url = ext.url_join(ext.get_domain(page_url), hint['href'])
                    self.name = hint.text
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

    def _is_card_page(self, soup):
        """Parses soup page and find out is page has card info

        :param soup: soup page from www.magiccards.info
        :return: boolean value
        """
        return len(soup.find_all('table')) > 2

    def _try_get_hint(self, soup):
        """Parses soup page and tries find out card hint

        :param soup: soup page from www.magiccards.info
        :return: tag 'a' with hint
        """
        hints_list = soup.find_all('li')
        return hints_list[0].contents[0] if hints_list else None

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
        return ext.url_join(MagiccardsScraper.MAGICCARDS_BASE_URL, table.find_all('a')[0]['href'])

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
        sid = ext.get_query_string_params(request_url)['sid']

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
                  'url': ext.get_domain_with_path(tcg_soup.find('td', class_='TCGPHiLoLink').contents[0]['href']),
                  'low': str(tcg_soup.find('td', class_='TCGPHiLoLow').contents[1].contents[0]),
                  'mid': str(tcg_soup.find('td', class_='TCGPHiLoMid').contents[1].contents[0]),
                  'high': str(tcg_soup.find('td', class_='TCGPHiLoHigh').contents[1].contents[0])}

        return prices

    def get_full_info(self):
        """Parses offers info for card

        :return: dict {'seller': models.TCGSeller, 'offers': list of models.TCGCardOffer}
        """
        opener = urllib2.build_opener()
        opener.addheaders.append(self.FULL_URL_COOKIE)

        sellers_offers = []
        link = self.full_url
        while True:
            tcg_response = opener.open(link).read()
            soup = BeautifulSoup(tcg_response)

            offers_block = soup.find('table', class_='priceTable').find_all('tr', class_='vendor')
            for block in offers_block:
                offer_td = block.find('td', class_='seller')
                name = offer_td.find_all('a')[0].text.strip()
                url = ext.get_domain(self.full_url) + offer_td.find_all('a')[0]['href']
                rating = str(offer_td.find('span', class_='actualRating').find('a').contents[0]).strip().split()[1]
                sales = ext.result_or_default(
                    lambda: str(offer_td.find('span', class_='ratingHeading').find('a').contents[0]).strip(),
                    default='')
                number = int(block.find('td', class_='quantity').text.strip())
                price = str(block.find('td', class_='price').contents[0]).strip()
                condition = str(block.find('td', class_='condition').find('a').contents[0]).strip()

                sellers_offers.append({'seller': models.TCGSeller(name, url, rating, sales),
                                       'offer': models.TCGCardOffer(self.sid, condition, number, price)})

            link_next = self._get_link_next(soup)
            if 'disabled' in link_next.attrs:
                break

            link = ext.get_domain(self.full_url) + link_next['href']

        grouped_sellers = [{'seller': k, 'offers': [seller_offer['offer'] for seller_offer in g]}
                           for k, g in itertools.groupby(sellers_offers, key=lambda so: so['seller'])]

        return grouped_sellers

    def _get_link_next(self, soup):
        """Parses soup to find tag with link to Next page in list

        :param soup: soup page with list of prices
        :return: link Next page tag
        """
        pager_block = soup.find('div', class_='pricePager')
        next_link_tag = pager_block.find('a', text=re.compile(r'Next'))
        return next_link_tag


class BuyMagicScrapper(object):
    """
    Parses search results from www.buymagic.ua
    """
    BASE_SEARCH_URL = 'http://www.buymagic.com.ua/edition/?color=-1&type=-1&rare=-1&id=-1&' \
                      'name={card.name}&description=&card_type=&artist=' \
                      '&ms=0&mv=-1&ps=0&pv=-1&ts=0&tv=-1&s=1&submit=%D0%98%D1%81%D0%BA%D0%B0%D1%82%D1%8C'

    @staticmethod
    def get_offers(card):
        """
        Searches specified card and offer info

        :param card: models.Card object
        :return: returns tuple (models.Card, list of models.ShopOffer)
        """
        search_url = BuyMagicScrapper.BASE_SEARCH_URL.replace('{card.name}', urllib2.quote(card.name))
        page = urllib2.urlopen(search_url).read()
        page = page.replace('<link rel="stylesheet" href="/jquery.fancybox-1.3.0.css" type="text/css" media="screen">',
                            '').replace('"title=', '" title=')
        soup = BeautifulSoup(page, from_encoding='utf-8')

        offers = []
        try:
            root_div = soup.find('div', class_='c2')
            card_div = root_div.find('p').contents[1].find('div')

            url = card_div.find('a')['href']
            price_table = card_div.find('table')

            for offer_tr in price_table.find_all('tr'):
                td_list = offer_tr.find_all('td')
                type = 'common' if td_list[0].find('b').text.strip() == 'Обычный'.decode('utf-8') else 'foil'
                price = ext.uah_to_dollar(td_list[1].text.strip())
                number = len(td_list[2].find_all('option'))

                offers.append(models.ShopOffer(card, url, number, price, type=type))
        except:
            pass

        return card, offers

class SpellShopScrapper(object):
    """
    Parses search results from www.spellshop.com.ua
    """

    BASE_SEARCH_URL = 'http://spellshop.com.ua/index.php?searchstring={card.name}'

    @staticmethod
    def get_offers(card):
        """
        Searches specified card and offer info

        :param card: models.Card object
        :return: returns tuple (models.Card, models.ShopOffer)
        """
        encoded_card_name = urllib2.quote(card.name.replace('\'', ''))
        search_url = SpellShopScrapper.BASE_SEARCH_URL.replace('{card.name}', encoded_card_name)
        page = urllib2.urlopen(search_url).read()
        soup = BeautifulSoup(page, from_encoding='utf-8')

        offer = None
        try:
            cards_table = soup.find('td', class_='td_center').find('table')
            if cards_table is not None:
                card_tr = cards_table.find('tr')
                card_tds = card_tr.find_all('td')

                url = ext.url_join(ext.get_domain(search_url), card_tds[1].find('a')['href'])
                price = ext.uah_to_dollar(card_tds[4].text)
                number = len(card_tds[5].find_all('option'))

                offer = models.ShopOffer(card, url, number, price)
        except:
            pass

        return card, offer