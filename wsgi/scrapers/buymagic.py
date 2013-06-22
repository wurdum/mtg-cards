# coding=utf-8
from bs4 import BeautifulSoup
import models
import ext
from scrapers.helpers import openurl, quote

BASE_SEARCH_URL = 'http://www.buymagic.com.ua/edition/?color=-1&type=-1&rare=-1&id=-1&' \
                  'name={card.name}&description=&card_type=&artist=' \
                  '&ms=0&mv=-1&ps=0&pv=-1&ts=0&tv=-1&s=1&submit=%D0%98%D1%81%D0%BA%D0%B0%D1%82%D1%8C'


def get_offers(card):
    """Searches specified card and offer info

    :param card: models.Card object
    :return: returns tuple (models.Card, list of models.ShopOffer)
    """
    search_url = BASE_SEARCH_URL.replace('{card.name}', quote(card.name))
    page = openurl(search_url)
    page = fix_page(page)
    soup = BeautifulSoup(page)

    offers = []
    try:
        root_div = soup.find('div', class_='c2')
        card_div = root_div.find('p').contents[1].find('div')

        url = card_div.find('a')['href']
        price_table = card_div.find('table')

        for td_list in [offer_tr.find_all('td') for offer_tr in price_table.find_all('tr')]:
            type = 'common' if td_list[0].find('b').text.strip() == 'Обычный'.decode('utf-8') else 'foil'
            price = ext.uah_to_dollar(td_list[1].text.strip())
            number = len(td_list[2].find_all('option'))

            offers.append(models.ShopOffer(card, url, number, price, type=type))
    except:
        pass

    return card, offers


def fix_page(page):
    """Fixes page html code and removes broken tags

    :param page: buymagic page
    :return: fixed buymagic page
    """
    return page\
        .replace('<link rel="stylesheet" href="/jquery.fancybox-1.3.0.css" type="text/css" media="screen">', '') \
        .replace('"title=', '" title=')