import difflib
from bs4 import BeautifulSoup, Tag
import ext
import models
from scrapers.helpers import openurl, quote
from scrapers.tcgplayer import TCGPlayerScrapper

MAGICCARDS_BASE_URL = 'http://magiccards.info/'
MAGICCARDS_QUERY_TMPL = 'query?q=!%s&v=card&s=cname'


def resolve_card(content_record):
    """Resolves card

    :param content_record: dict {card name, card number}
    :return: object models.Card
    """
    base_resolver = BasicResolver(content_record['name'])
    resolve_result = base_resolver.get_name_and_url()
    if resolve_result is None:
        return models.Card(content_record['name'], content_record['number'])

    name, url = resolve_result

    advanced_resolver = AdvancedResolver(url)
    redactions = advanced_resolver.get_redactions()
    if redactions is None:
        return models.Card(name, content_record['number'])

    return models.Card(name, content_record['number'], redactions=redactions)


class BasicResolver(object):
    """
    Finds basic page for card and fixes name if needs
    """

    def __init__(self, name):
        self.name = name

    def get_name_and_url(self):
        """
        Returns tuple (card name, card url) or None
        """
        card_name = self.name
        page_url = MAGICCARDS_BASE_URL + MAGICCARDS_QUERY_TMPL % quote(self.name)

        request_result = self._choose_hint_if_need(card_name, page_url)
        if request_result is None:
            return None

        card_name, page_url = request_result
        card_name, page_url = self._change_page_to_en(card_name, page_url)

        if page_url is None:
            return None

        return card_name, page_url

    def _choose_hint_if_need(self, name, url):
        """Selects correct hint and updates name and url for card.
        If card is already resolved correctly, returns name and url from input.

        :param name: card name
        :param url: card url
        :return: tuple (card name, card url)
        """
        page = openurl(url)
        soup = BeautifulSoup(page)

        if len(soup.find_all('table')) > 2:
            return name, url

        hint = self._try_get_hint(self.name, soup)
        if hint is None:
            return None

        name = hint.text
        url = ext.url_join(ext.get_domain(url), hint['href'])

        return name, url

    def _change_page_to_en(self, name, url):
        """If current url leads to not en page, changes to en and updates card name.

        :param name: card name
        :param url: card url
        :return: tuple (card name, card url)
        """
        page = openurl(url)
        soup = BeautifulSoup(page)
        en_link_tag = list(soup.find_all('table')[3].find_all('td')[2].find('img', alt='English').next_elements)[1]
        if en_link_tag.name == 'b':
            return name, url

        name = en_link_tag.text
        url = ext.url_join(ext.get_domain(url), en_link_tag['href'])

        return name, url

    def _try_get_hint(self, name, soup):
        """Parses soup page and tries find out card hint.
        Selects hint that has max affinity with base card name.

        :param name: cards name
        :param soup: soup page from www.magiccards.info
        :return: tag 'a' with hint
        """
        hints_list = []
        for hint_li in soup.find_all('li'):
            hint_tag = hint_li.contents[0]
            resemble_rate = difflib.SequenceMatcher(a=ext.uni(name), b=ext.uni(hint_li.contents[0].text)).ratio()
            hints_list.append({'a_tag': hint_tag, 'rate': resemble_rate})

        return sorted(hints_list, key=lambda h: h['rate'], reverse=True)[0]['a_tag'] if hints_list else None


class AdvancedResolver(object):
    """
    Resolves card redactions, info and tcg prices
    """

    def __init__(self, url):
        self.url = url

    def get_redactions(self):
        """
        Parses card redactions
        """
        reda_pages = self._get_redas_urls(self.url)

        redas = []
        for name, url in reda_pages:
            page = openurl(url)
            reda_soup = BeautifulSoup(page)

            info = self._get_card_info(reda_soup)
            price = self._get_prices(reda_soup)
            if price is None:
                continue

            card_info = models.CardInfo(**info)
            card_prices = models.CardPrices(**price)

            redas.append(models.Redaction(name, info=card_info, prices=card_prices))

        return redas

    def _get_redas_urls(self, page_url):
        """Parses card page and finds all available card redactions

        :param page_url: card page url
        :return: list of dict (reda name, reda url)
        """
        page = openurl(page_url)
        soup = BeautifulSoup(page)

        content_table = soup.find_all('table')[3]
        redas_td = content_table.find_all('td')[2]

        # if card has second side
        start_block_index = 1 if len(redas_td.find_all('u')) == 3 else 2
        redas_block_start = redas_td.find_all('u')[start_block_index]

        tags = []
        for tag in redas_block_start.next_sibling.next_elements:
            if not isinstance(tag, Tag):
                continue

            if tag.name == 'u':
                break

            if tag.name == 'a':
                tags.append((tag.text.strip().lower(), ext.url_join(ext.get_domain(MAGICCARDS_BASE_URL), tag['href'])))

            if tag.name == 'b':
                # remove card type in parentheses like (myth rare)
                tags.append((tag.text.split('(')[0].strip().lower(), page_url))

        return tags

    def _get_card_info(self, soup):
        """Parses soup page and returns dict with card info

        :param soup: soup page from www.magiccards.info
        :return: dictionary with card info
        """
        content_table = soup.find_all('table')[3]
        return {'url': self._get_url(content_table),
                'img_url': self._get_img_url(content_table)}

    def _get_url(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: url of the page with card
        """
        return ext.url_join(MAGICCARDS_BASE_URL, table.find_all('a')[0]['href'])

    def _get_img_url(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: url of the card image
        """
        return table.find_all('img')[0]['src']

    def _get_prices(self, magic_soup):
        """Parses prices by TCGPlayer card sid

        :param magic_soup: soup page from www.magiccards.info
        :return: dictionary with prices from TCGPlayer in format {sid, low, mid, high}
        """
        content_table = magic_soup.find_all('table')[3]
        script_block = content_table.find('script')
        if script_block is None:
            return None

        request_url = script_block['src']
        sid = ext.get_query_string_params(request_url)['sid']

        tcg_scrapper = TCGPlayerScrapper(sid)
        brief_prices_info = tcg_scrapper.get_brief_info()
        if brief_prices_info is None:
            return None

        return brief_prices_info