import difflib
from eventlet.green import urllib2
from bs4 import BeautifulSoup, Tag
import ext
import models
from scrapers.helpers import openurl
from scrapers.tcgplayer import TCGPlayerScrapper


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
        if content_record['name'].split()[0].strip().lower() in ['mountain', 'swamp', 'island', 'plains', 'forest']:
            return None

        scrapper = MagiccardsScraper(content_record['name'], content_record['number'])
        return scrapper.get_card()

    def get_card(self):
        """Parses card info, if no info returns card object without info and prices

        :return: models.Card object
        """
        page_url = self.MAGICCARDS_BASE_URL + self.MAGICCARDS_QUERY_TMPL % urllib2.quote(self.name)
        page = openurl(page_url)
        soup = BeautifulSoup(page, from_encoding='utf-8')

        if not self._is_card_page(soup):
            hint = self._try_get_hint(self.name, soup)
            if hint is None:
                return models.Card(self.name, int(self.number))

            self.name = hint.text
            page_url = ext.url_join(ext.get_domain(page_url), hint['href'])
            page = openurl(page_url)
            soup = BeautifulSoup(page)

        # if card is found, but it's not english
        if not self._is_en(soup):
            en_link_tag = list(soup.find_all('table')[3].find_all('td')[2].find('img', alt='English').next_elements)[1]
            self.name = en_link_tag.text
            page_url = ext.url_join(ext.get_domain(page_url), en_link_tag['href'])

        reda_pages = self._get_redas_urls(page_url)

        redas = []
        for reda_page in reda_pages:
            page = openurl(reda_page['url'])
            reda_soup = BeautifulSoup(page)

            info = self._get_card_info(reda_soup)
            price = self._get_prices(reda_soup)
            if price is None:
                continue

            card_info = models.CardInfo(**info)
            card_prices = models.CardPrices(**price)

            redas.append(models.Redaction(reda_page['name'], info=card_info, prices=card_prices))

        return models.Card(self.name, int(self.number), redactions=redas)

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
                tags.append({'name': tag.text.strip().lower(),
                             'url': ext.url_join(ext.get_domain(self.MAGICCARDS_BASE_URL), tag['href'])})

            if tag.name == 'b':
                # remove card type
                reda_name = tag.text.split('(')[0].strip().lower()
                tags.append({'name': reda_name, 'url': page_url})

        return tags

    def _is_en(self, soup):
        """
        Checks if found card is en
        """
        en_link = list(soup.find_all('table')[3].find_all('td')[2].find('img', alt='English').next_elements)[1]
        return en_link.name == 'b'

    def _is_card_page(self, soup):
        """Parses soup page and find out is page has card info

        :param soup: soup page from www.magiccards.info
        :return: boolean value
        """
        return len(soup.find_all('table')) > 2

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
        script_block = content_table.find('script')
        if script_block is None:
            return None

        request_url = script_block['src']
        sid = ext.get_query_string_params(request_url)['sid']

        tcg_scrapper = TCGPlayerScrapper(sid)
        brief_prices_info = tcg_scrapper.get_brief_info()

        return brief_prices_info