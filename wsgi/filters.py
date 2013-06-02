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


def register(app):
    app.add_template_filter(active_if)
    app.add_template_filter(get_new_order)
    app.add_template_filter(price)
    app.add_template_filter(price_float)
    app.add_template_filter(price_sum)