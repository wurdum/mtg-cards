import itertools
from subprocess import Popen, PIPE
import models
import db


def get_task(token):
    """Returns task for token or creates new

    :param token: str
    """
    task = db.get_task(token)
    if task is None:
        task = create_new_task(token)
        db.save_task(task)

    return task


def create_new_task(token):
    """
    Creates new task fot token
    """
    cards = db.get_cards(token, only_resolved=True)
    task_entries = itertools.chain(*[[models.TaskEntry(card.name, reda.name, reda.prices.sid) for reda in card.redactions]
                                     for card in cards])

    return models.Task(token, entries=task_entries)


def run_daemon():
    """
    Runs daemon script if it wasn't started
    """
    if not daemon_is_run():
        import sys
        Popen(['nohup', sys.executable, 'worker/daemon.py'])


def daemon_is_run():
    ps_comm = 'ps aux'
    grep_comm = 'grep daemon.py'
    ps_exec = Popen(ps_comm.split(), stdout=PIPE)
    grep_exec = Popen(grep_comm.split(), stdin=ps_exec.stdout, stdout=PIPE)
    result = grep_exec.communicate()[0]

    return result.strip()