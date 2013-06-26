import os
import pymongo
import models
import filters
import ext

MONGO_URL = os.environ.get('OPENSHIFT_MONGODB_DB_URL', 'localhost')
DB = os.environ.get('OPENSHIFT_APP_NAME', 'cards')


def get_unique_token():
    """Generates unique token

    :return: string token
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    while True:
        token = ext.get_token()
        if db.list.find_one({'token': token}) is None:
            return token


def get_tokens():
    """
    Returns list of tokens
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    return [rec['token'] for rec in db.list.find({}, {'token': 1})]


def get_cards(token, only_resolved=False):
    """Searches cards list by token

    :return: list of models.Card objects
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    dict_obj = db.list.find_one({'token': token})
    if not dict_obj:
        return []

    cards = [tocard(dc) for dc in dict_obj['cards']]

    return filter(lambda c: c.is_resolved, cards) if only_resolved else cards


def get_last_cards_lists(show_private=False, lists_number=5):
    """Gets all cards lists that present in db

    :return: returns list of models.CardList objects
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    cards_lists = []
    query_filter = {'list_type': 'public'} if not show_private else {}
    for cl in db.list.find(query_filter).sort('$natural', -1).limit(lists_number):
        token = cl['token']
        cards = [tocard(dc) for dc in cl['cards']]

        cards_list = models.CardsList(token, sum(c.number for c in cards),
                                      dict([(prop, filters.price_sum(cards, prop)) for prop in ['low', 'mid', 'high']]))

        cards_lists.append(cards_list)

    return cards_lists


def save_cards(token, list_type, cards):
    """
    Saves cards list to db with token as key
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.list.insert({'token': token, 'list_type': list_type, 'cards': [todict(c) for c in cards]})


def delete_cards(token):
    """Removes cards list with specified token

    :param token: token using which will be found cards list that will be deleted
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.list.remove({'token': token})


def get_task(token):
    """
    Returns task for cards list with specified token
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    dbtask = db.tasks.find_one({'token': token})
    if dbtask is None:
        return None

    return totask(dbtask)


def save_task(task):
    """Updates or adds task to db

    :param task: models.Task object
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.tasks.update({'token': task.token}, todict(task), upsert=True)


def delete_task(token):
    """
    Removes task for token
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.tasks.remove({'token': token})


def tocard(dict_card):
    """
    Converts dict to models.Card
    """
    redas = [toreda(r) for r in dict_card['redactions']]
    return models.Card(dict_card['name'], dict_card['number'], redactions=redas)


def toreda(dict_reda):
    """
    Converts dict to models.Redaction
    """
    info = models.CardInfo(**dict_reda['info']) if 'info' in dict_reda and dict_reda['info'] else None
    prices = models.CardPrices(**dict_reda['prices']) if 'prices' in dict_reda and dict_reda['prices'] else None
    return models.Redaction(dict_reda['name'], info=info, prices=prices)


def tooffer(dict_offer):
    """
    Converts dict to models.TCGCardOffer
    """
    return {'seller': models.TCGSeller(**dict_offer['seller']),
            'offers': [models.TCGCardOffer(**dbcoff) for dbcoff in dict_offer['offers']]}


def toentry(dict_entry):
    """
    Converts dict to models.TaskEntry
    """
    offers = [tooffer(off) for off in dict_entry['offers']] if 'offers' in dict_entry and dict_entry['offers'] else None
    return models.TaskEntry(dict_entry['card_name'], dict_entry['card_reda'], dict_entry['card_sid'],
                            dict_entry['status'], offers=offers)


def totask(dict_task):
    """
    Converts dict to models.Task
    """
    entries = [toentry(dbe) for dbe in dict_task['entries']] if 'entries' in dict_task and dict_task['entries'] else None
    return models.Task(dict_task['token'], dict_task['status'], entries=entries)


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
