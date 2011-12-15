import abc

class Base(object):
    __metaclass__ = abc.ABCMeta
    required_options = []

    def __init__(self, id, options={}):
        self.id = id
        self.options = options
        for option in self.required_options:
            if not option in self.options:
                raise ValueError, 'Missing configuration option: %s' % option

    @abc.abstractmethod
    def get_all_stops(self):    
        pass

    @abc.abstractmethod
    def get_predictions(self, stop):
        pass
