import ext
import numpy


class Card(object):
    """
    Card model with info and prices
    """

    def __init__(self, name, number, redactions=None):
        self.name = name
        self.number = number
        self.redactions = redactions if redactions else []

    @property
    def is_resolved(self):
        return self.redactions is not None and self.redactions

    @property
    def description(self):
        return self.redactions[0].info.description \
            if self.redactions is not None and len(self.redactions) > 1 else None

    def get_avg_prices(self):
        """
        Returns average prices among redactions
        """
        avg_prices = {}
        for prop in ['low', 'mid', 'high']:
            avg_prices[prop] = numpy.median([reda.prices.__dict__[prop] for reda in self.redactions])
        return avg_prices

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return '%s x %d' % (self.name, self.number)


class Redaction(object):
    """
    Represents card redaction
    """

    def __init__(self, name, info=None, prices=None):
        self.name = name
        self.info = info
        self.prices = prices

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return self.name


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

    def __init__(self, sid, redaction, condition, number, price):
        self.sid = sid
        self.redaction = redaction
        self.condition = condition
        self.number = number
        self.price = price

    def __repr__(self):
        return self.sid + ' ' + self.condition


class TCGCardOffersList(object):
    """
    Represents list of offers for card
    """

    def __init__(self, card):
        self.card = card
        self._offers = []

    @property
    def offers(self):
        """
        Offers list sorted by price lower to higher
        """
        return sorted(self._offers, key=lambda o: o.price)

    @property
    def available_card_num(self):
        """
        Returns number of cards available to purchase
        """
        available = sum([o.number for o in self._offers])
        return self.card.number if available > self.card.number else available

    @property
    def card_cost(self):
        """
        Returns card cost if you will buy it
        """
        cost = 0.0
        bought = 0
        for offer in self.offers:
            need_cards = self.card.number - bought
            available_cards = offer.number

            buy_cards = need_cards if available_cards > need_cards else available_cards
            bought += buy_cards
            cost += buy_cards * offer.price

            if bought == self.card.number:
                break

        return cost

    @property
    def card_is_available(self):
        return self.card.number == self.available_card_num

    def add_offer(self, offer):
        """Adds new offer

        :param offer: models.TCGCardOffer object
        """
        self._offers.append(offer)


class TCGSeller(object):
    """
    Represents seller that has several cards
    """

    def __init__(self, name, url, rating, sales):
        self.name = name
        self.url = url
        self.rating = rating
        self.sales = sales
        self._card_offers_lists = []

    @property
    def card_offers_lists(self):
        return self._card_offers_lists

    @property
    def available_cards_num(self):
        """Returns number of cards that could be bought from this seller

        :return: number as int
        """
        return sum([col.available_card_num for col in self._card_offers_lists])

    @property
    def cards_cost(self):
        """Returns cost of cards list

        :return: cost as float
        """
        return sum([col.card_cost for col in self._card_offers_lists])

    def add_card_offer(self, card, offer):
        """
        Adds new card to cards list or if such already added, adds only offer info
        """
        card_offers_list = ext.get_first(self._card_offers_lists, lambda col: col.card.name == card.name)
        if card_offers_list is None:
            card_offers_list = TCGCardOffersList(card)
            self._card_offers_lists.append(card_offers_list)

        card_offers_list.add_offer(offer)

    def get_card_offers(self, card):
        """
        Returns cards offers list for specified card or returns None if there no offers
        """
        return ext.get_first(self._card_offers_lists, lambda c: c.card.name == card.name)

    def has_all_cards(self, cards):
        """
        Returns True if all cards is available and False if not
        """
        return self.available_cards_num == sum([c.number for c in cards])

    def __hash__(self):
        return hash((self.name, self.url))

    def __eq__(self, other):
        return (self.name, self.url) == (other.name, other.url)

    def __repr__(self):
        return self.name + ' ' + len(self._card_offers_lists)


class ShopOffer(object):
    """
    Represents card offer from www.buymagic.ua
    """

    def __init__(self, card, redaction, url, number, price, type='common'):
        self.card = card
        self.redaction = redaction
        self.url = url
        self.number = number
        self.price = price
        self.type = type

    def __repr__(self):
        return '%s %s %s' % (self.card, self.price, self.type)