import random


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
    return price_str_to_float(card.prices.__dict__[prop])


def price_str_to_float(string):
    """Converts string price to float repr, if price is 0 returns 0.01

    :param string: price string repr
    :return: price as float
    """
    return float(string[1:]) if float(string[1:]) > 0 else 0.01


def get_new_order(args):
    """Return asc when order arg is None of desc and desc when order arg is asc

    :param args: request args dics
    :return: asc or desc
    """
    if 'order' not in args:
        return 'desc'

    return 'asc' if args['order'] == 'desc' else 'desc'


def active_if(var, value, class_alone=True):
    if var == value:
        return 'active' if class_alone else ' active'
    return ''


def idfy(value):
    """Clears input value from symbols that are invalid for html id

    :param value: input string
    :return: cleaned string
    """
    result = ''
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
    if value[0] not in chars[:-2]:
        result = 'a'

    for ch in value:
        if ch not in chars:
            result += '_' + random.choice(chars)
        else:
            result += ch

    return result


def register(app):
    app.add_template_filter(idfy)
    app.add_template_filter(active_if)
    app.add_template_filter(get_new_order)
    app.add_template_filter(price)
    app.add_template_filter(price_float)
    app.add_template_filter(price_sum)