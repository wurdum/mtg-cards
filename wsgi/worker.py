import itertools
import os
import pymongo
import db as dbmodule
import models
import ext
from scrapers.tcgplayer import TCGPlayerScrapper


class Task(object):

    def __init__(self, token, status='need update', entries=None):
        self.token = token
        self.status = status
        self.entries = entries

    def __repr__(self):
        return '%s [%s]' % (self.token, self.status)


class TaskEntry(object):

    def __init__(self, card_name, card_reda, card_sid, status='need update', offers=None):
        self.card_name = card_name
        self.card_reda = card_reda
        self.card_sid = card_sid
        self.status = status
        self.offers = offers

    def __repr__(self):
        return '%s - %s [%s]' % (self.card_name, self.card_reda, self.status)


MONGO_URL = os.environ.get('OPENSHIFT_MONGODB_DB_URL', 'localhost')
DB = os.environ.get('OPENSHIFT_APP_NAME', 'cards')


def create_task(token):
    cards = dbmodule.get_cards(token, only_resolved=True)
    task_entries = itertools.chain(*[[TaskEntry(card.name, reda.name, reda.prices.sid) for reda in card.redactions]
                                     for card in cards])

    return Task(token, entries=task_entries)


def tooffer(dict_offer):
    return {'seller': models.TCGSeller(**dict_offer['seller']),
            'offers': [models.TCGCardOffer(**dbcoff) for dbcoff in dict_offer['offers']]}


def toentry(dict_entry):
    offers = [tooffer(off) for off in dict_entry['offers']] if 'offers' in dict_entry and dict_entry['offers'] else None
    return TaskEntry(dict_entry['card_name'], dict_entry['card_reda'], dict_entry['card_sid'], dict_entry['status'],
                     offers=offers)


def totask(dict_task):
    entries = [toentry(dbe) for dbe in dict_task['entries']] if 'entries' in dict_task and dict_task['entries'] else None
    return Task(dict_task['token'], dict_task['status'], entries=entries)


def get_task(token):
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    dbtask = db.tasks.find_one({'token': token})
    if dbtask is None or dbtask['status'] == 'need update':
        get_tokens()
        return get_task(token)

    return totask(dbtask)


def execute(task):
    print 'executing', task

    for entry in task.entries:
        if entry.status == 'updated':
            continue

        scrapper = TCGPlayerScrapper(entry.card_sid)
        offers = scrapper.get_full_info()
        entry.offers = offers
        entry.status = 'updated'
        print 'done', len(offers), entry

    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    task.status = 'updated'
    db.tasks.update({'token': task.token}, dbmodule.todict(task))
    print 'done', task


def get_tokens():
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    have_some_new = False
    tokens = [rec['token'] for rec in db.list.find({}, {'token': 1})]
    for token in tokens:
        dbtask = db.tasks.find_one({'token': token})
        if dbtask is None:
            task = create_task(token)
            db.tasks.insert(dbmodule.todict(task))
            have_some_new = True
        else:
            if dbtask['status'] == 'updated':
                continue

            task = totask(dbtask)
            execute(task)

    if have_some_new:
        get_tokens()


if __name__ == '__main__':
    get_tokens()