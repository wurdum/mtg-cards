def price(card, prop):
    """Returns card price considering cards number

    :param card: card object
    :param prop: price that will be used (low, mid, high)
    :return: price as float number
    """
    return price_float(card, prop) * card.number


def price_sum(cards, prop):
    """Calculates sum of the prices for cards list

    :param cards: cards list
    :param prop: price that will be summed (low, mid, high)
    :return: sum as float number
    """
    return sum([price_float(card, prop) * card.number for card in cards if card.prices])


def price_float(card, prop):
    """Converts price to float repr

    :param card: card object
    :param prop: price that will be used (low, mid, high)
    :return: price as float number
    """
    return float(card.prices.__dict__[prop][1:])