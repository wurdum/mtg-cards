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
    task_entries = itertools.chain(
        *[[models.TaskEntry(card.name, reda.name, reda.prices.sid) for reda in card.redactions]
          for card in cards])

    return models.Task(token, entries=list(task_entries))


def run_daemon():
    """
    Runs daemon script if it wasn't started
    """
    if not daemon_is_run():
        import os
        import sys

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(base_dir, 'worker/daemon.py')

        PY_VERSION = 'python-' + ('.'.join(map(str, sys.version_info[:2])))
        sys.path.insert(0, os.path.dirname(__file__) or '.')
        python_exec = os.environ['HOME'] + '/' + PY_VERSION + '/virtenv/bin/python'

        Popen(['nohup', python_exec, script_path])


def daemon_is_run():
    ps_comm = 'ps aux'
    grep_comm = 'grep daemon.py'
    ps_exec = Popen(ps_comm.split(), stdout=PIPE)
    grep_exec = Popen(grep_comm.split(), stdin=ps_exec.stdout, stdout=PIPE)
    result = grep_exec.communicate()[0]
    lines = [line for line in result.split('\n') if 'grep' not in line and line]
    return len(lines) > 0