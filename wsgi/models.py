class Card(object):
    """
    Card model
    """

    def __init__(self, name, number, description=None, url=None, img_url=None, prices=None):
        self.name = name
        self.number = number
        self.description = description
        self.url = url
        self.img_url = img_url
        self.prices = prices

    @property
    def is_resolved(self):
        return self.url is None

    def __repr__(self):
        return '%s x %d' % (self.name, self.number)