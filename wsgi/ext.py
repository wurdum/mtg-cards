import random
import string
import cStringIO
import urlparse


def get_token(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def get_first(iterable, func, default=None):
    """
    Returns first element that satisfy condition
    """
    for item in iterable:
        if func(item):
            return item

    return default


def result_or_default(func, default=None, prevent_empty=False):
    """Returns result of func execution or default value

    :param func: function to execute
    :return: result of func ot default value
    """
    try:
        result = func()
        return result if not prevent_empty or result else default
    except:
        return default


def get_domain(url):
    """
    Returns hostname with scheme
    """
    decomposed = urlparse.urlparse(url)
    return decomposed.scheme + '://' + decomposed.hostname


def get_domain_with_path(url):
    """
    Returns hostname with scheme and path
    """
    decomposed = urlparse.urlparse(url)
    return decomposed.scheme + '://' + decomposed.hostname + decomposed.path


def get_query_string_params(url):
    """
    Returns dict of query string parameters
    """
    return dict([(k, v[0]) for k, v in urlparse.parse_qs(urlparse.urlparse(url).query).items()])


def url_join(base, url):
    """
    Joins 2 parts of url
    """
    return urlparse.urljoin(base, url)


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