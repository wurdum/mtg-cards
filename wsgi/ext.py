import random
import string
import cStringIO


def get_token(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def parse_card(line):
    """parse_card(line) -> (string, string)

    Parses input line to find card name and cards number.
    If no cards number found, returns 1.

    :param line: input string
    :return: tuple (card name, cards number)
    """

    length = len(line)
    number = ''

    current_pos = length - 1
    while line[current_pos].isdigit():
        number = line[current_pos] + number
        current_pos -= 1

    if not number:
        number = '1'

    card_name = line[:current_pos].strip(' \t\r;')

    return card_name, number


def read_file(stream):
    """read_file(stream) -> list of (string, string)

    Parses input stream and returns list of cards names and cards numbers

    :return: list of tuples (card name, card number)
    """

    if isinstance(stream, cStringIO.OutputType):
        full_content = stream.getvalue()
        stripped_lines = [l.strip(' \t\r') for l in full_content.split('\n')]
        cards = [parse_card(card) for card in stripped_lines if card]
        return cards

    raise IOError('unknown input stream format encountered, type: %s' % type(stream))