import os
import pymongo
import models

MONGO_URL = os.environ.get('OPENSHIFT_MONGODB_DB_URL', 'localhost')
DB = os.environ.get('OPENSHIFT_APP_NAME', 'cards')


def save_cards(token, cards):
    """
    Saves cards list to db with token as key
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.list.insert({'token': token, 'cards': [todict(c) for c in cards]})


def get_cards(token):
    """Searches cards list by token

    :return: list of models.Card objects
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    dict_obj = db.list.find_one({'token': token})
    if not dict_obj:
        return []

    dict_cards_list = dict_obj['cards']

    cards = []
    for c in dict_cards_list:
        info = models.CardInfo(**c['info']) if 'info' in c and c['info'] else None
        prices = models.CardPrices(**c['prices']) if 'prices' in c and c['prices'] else None
        card = models.Card(c['name'], c['number'], info=info, prices=prices)
        cards.append(card)

    return cards


def todict(obj, classkey=None):
    """
    Converts object graph to dict structures
    """
    if isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = todict(obj[k], classkey)
        return obj
    elif hasattr(obj, "__iter__"):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
                     for key, value in obj.__dict__.iteritems()
                     if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj
