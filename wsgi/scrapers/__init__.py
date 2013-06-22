import eventlet
import ext
from scrapers.magiccards import MagiccardsScraper
from scrapers.tcgplayer import TCGPlayerScrapper
from scrapers.buymagic import BuyMagicScrapper
from scrapers.spellshop import SpellShopScrapper


def resolve_cards_async(content):
    """Parses card info using MagiccardScrapper in thread for request mode and
    mergers duplicates

    :param content: list of (card_name, card_number) tuples
    :return: list of models.Card objects
    """
    pool = eventlet.GreenPool(len(content))
    cards = [card for card in pool.imap(MagiccardsScraper.resolve_card, content)]

    return cards


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



