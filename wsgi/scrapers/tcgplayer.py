import itertools
import re
from eventlet.green import urllib2
from bs4 import BeautifulSoup
import ext
import models
from scrapers.helpers import openurl


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
        tcg_response = openurl(self.brief_url)
        html_response = tcg_response.replace('\'+\'', '').replace('\\\'', '"')[16:][:-3]

        tcg_soup = BeautifulSoup(html_response)
        link_container = tcg_soup.find('td', class_='TCGPHiLoLink')
        if link_container is None:
            return None

        prices = {'sid': self.sid,
                  'url': ext.get_domain_with_path(link_container.contents[0]['href']),
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