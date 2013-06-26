import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import worker
from scrapers.tcgplayer import TCGPlayerScrapper


def run():
    """
    Runs parsing sellers for each non 'updated' tasks
    """
    tokens = db.get_tokens()
    for token in tokens:
        task = worker.get_task(token)
        if task.status == 'updated':
            continue

        execute(task)


def execute(task):
    """Parses tcgplayer sellers info for cards in specified task

    :param task: instance of models.Task
    :return:
    """
    for entry in task.entries:
        if entry.status == 'updated':
            continue

        scrapper = TCGPlayerScrapper(entry.card_sid)
        offers = scrapper.get_full_info()
        entry.offers = offers
        entry.status = 'updated'
        db.save_task(task)

    task.status = 'updated'
    db.save_task(task)


if __name__ == '__main__':
    run()