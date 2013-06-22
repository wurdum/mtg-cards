from bs4 import BeautifulSoup
import ext
import models
from scrapers.helpers import openurl, quote


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
        encoded_card_name = quote(card.name.replace('\'', ''))
        search_url = SpellShopScrapper.BASE_SEARCH_URL.replace('{card.name}', encoded_card_name)
        page = openurl(search_url)
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