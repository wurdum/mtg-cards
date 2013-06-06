import ext
import filters


class Card(object):
    """
    Card model with info and prices
    """

    def __init__(self, name, number, info=None, prices=None):
        self.name = name
        self.number = number
        self.prices = prices
        self.info = info

    @property
    def has_info(self):
        return self.info is not None

    @property
    def has_prices(self):
        return self.prices is not None

    def __repr__(self):
        return '%s x %d' % (self.name, self.number)


class CardInfo(object):
    """
    Card info from www.magiccards.com
    """

    def __init__(self, url, img_url, description):
        self.url = url
        self.img_url = img_url
        self.description = description

    def __repr__(self):
        return self.url


class CardPrices(object):
    """
    Card info from TCGPlayer
    """

    def __init__(self, sid, url, low, mid, high):
        self.sid = sid
        self.url = url
        self.low = low
        self.mid = mid
        self.high = high

    def __repr__(self):
        return "%s: l[%s] m[%s] h[%s]" % (self.url, self.low, self.mid, self.high)


class CardsList(object):
    """
    Represents cards list with summary info
    """

    def __init__(self, token, cards_num, price):
        self.token = token
        self.cards_num = cards_num
        self.price = price


class TCGCardOffer(object):
    """
    Represents tcg seller for specific card
    """

    def __init__(self, sid, condition, number, price):
        self.sid = sid
        self.condition = condition
        self.number = number
        self.price = price

    def __repr__(self):
        return self.sid + ' ' + self.condition


class TCGSeller(object):
    """
    Represents seller that has several cards
    """

    def __init__(self, name, url, rating, sales):
        self.name = name
        self.url = url
        self.rating = rating
        self.sales = sales
        self._cards = []

    @property
    def cards(self):
        return self._cards

    def add_card(self, card, condition, number, price):
        """
        Adds new card to cards list or if such already added, adds only supply info
        """
        card_offer = {'condition': condition, 'number': number, 'price': price}
        card_record = ext.get_first(self._cards, lambda c: c['card'].name == card.name)
        if card_record is None:
            self._cards.append({'card': card, 'offers': [card_offer]})
        else:
            card_record['offers'].append(card_offer)

    def has_all_cards(self, cards):
        """
        Returns True if all cards is available and False if not
        """
        return self.get_available_cards_num(cards) == sum([c.number for c in cards])

    def get_available_cards_num(self, cards):
        """Returns number of cards that could be bought from this seller

        :param cards: list of models.Card objects
        :return: number as int
        """
        available = 0
        for card in cards:
            card_record = ext.get_first(self._cards, lambda c: c['card'].name == card.name)
            if card_record is not None:
                cards_available = sum([r['number'] for r in card_record['offers']])
                available += card.number if cards_available >= card.number else cards_available

        return available

    def calculate_cards_cost(self, cards):
        """Returns cost of cards list

        :param cards: list of models.Card objects
        :return: cost as float
        """
        if not self.has_all_cards(cards):
            raise ValueError('not all cards are available from this seller')

        cost = 0.0
        for card in cards:
            card_record = ext.get_first(self._cards, lambda c: c['card'].name == card.name)
            offers = sorted(card_record['offers'], key=lambda r: filters.price_str_to_float(r['price']))

            bought = 0
            for offer in offers:
                need_cards = card.number - bought
                available_cards = offer['number']

                buy_cards = need_cards if available_cards > need_cards else available_cards
                bought += buy_cards
                cost += buy_cards * filters.price_str_to_float(offer['price'])

                if bought == card.number:
                    break

        return cost

    def __hash__(self):
        return hash((self.name, self.url))

    def __eq__(self, other):
        return (self.name, self.url) == (other.name, other.url)

    def __repr__(self):
        return self.name + ' ' + len(self._cards)
