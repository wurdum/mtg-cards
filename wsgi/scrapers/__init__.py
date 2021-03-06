import eventlet
import ext
import worker
from scrapers import magiccards, buymagic, spellshop
from scrapers.tcgplayer import TCGPlayerScrapper


def resolve_cards_async(content):
    """Parses card info using MagiccardScrapper in thread for request mode and
    mergers duplicates

    :param content: list of (card_name, card_number) tuples
    :return: list of models.Card objects
    """
    pool = eventlet.GreenPool(len(content))
    cards = [card for card in pool.imap(magiccards.resolve_card, _filter_lands(content))]

    return cards


def _filter_lands(content):
    """Removes lands cards

    :param content: list of dict (card name, card number)
    """
    lands = ['mountain', 'swamp', 'island', 'plains', 'forest']
    for record in content:
        if record['name'].strip().lower().split()[0] not in lands:
            yield record


def get_tcg_sellers(task, cards):
    """Reads task results and parses tcg sellers info

    :param task: object of models.Task
    :param cards: list of models.Card objects
    :return: list of models.TCGSeller objects with filled cards property
    """
    sellers = []
    for entry in task.entries:
        card = ext.get_first(cards, lambda c: c.name == entry.card_name)
        for seller_offers in entry.offers:
            seller = ext.get_first(sellers, lambda s: s == seller_offers['seller'])
            if seller is None:
                seller = seller_offers['seller']
                sellers.append(seller)

            for offer in seller_offers['offers']:
                seller.add_card_offer(card, offer)

    return sellers


def get_buymagic_offers_async(cards):
    """Parses async www.buymagic.ua to obtain offers

    :param cards: list of models.Card objects
    :return: dict {models.Card: models.ShopOffer}
    """
    offers = {}
    pool = eventlet.GreenPool(len(cards))
    for card, card_offers in pool.imap(buymagic.get_offers, cards):
        offers[card] = card_offers

    return offers


def get_spellshop_offers_async(cards):
    """Parses async www.spellshop.com.ua to obtain offers

    :param cards: list of models.Card objects
    :return: dict {models.Card: models.ShopOffer}
    """
    offers = {}
    pool = eventlet.GreenPool(10 if len(cards) > 10 else len(cards))
    for card, offer in pool.imap(spellshop.get_offers, cards):
        offers[card] = offer

    return offers