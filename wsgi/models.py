import ext


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


class TCGCardSeller(object):
    """
    Represents tcg seller for specific card
    """

    def __init__(self, sid, name, url, rating, sales, number, price, condition):
        self.sid = sid
        self.name = name
        self.url = url
        self.rating = rating
        self.number = number
        self.price = price
        self.sales = sales
        self.condition = condition

    def __repr__(self):
        return self.name + ' ' + self.sid


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
        self._cards.append({'card': card, 'condition': condition, 'number': number, 'price': price})

    def get_available_cards_num(self, cards):
        """Returns number of cards that could be bought from this seller

        :param cards: list of models.Card objects
        :return: number as int
        """
        available = 0
        for card in cards:
            available_card = ext.get_first(self._cards, lambda c: c['card'].name == card.name)
            if available_card is not None:
                available += card.number if available_card['number'] >= card.number else available_card['number']

        return available

    def __repr__(self):
        return self.name + ' ' + len(self._cards)
