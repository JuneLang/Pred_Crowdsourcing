

class User(object):
    def __init__(self, id, confidence=0):
        self._id = id
        self._confidence = confidence
        self.label_list = []

    @property
    def id(self):
        return self._id

    @property
    def confidence(self):
        return self._confidence

    @confidence.setter
    def confidence(self, v):
        self._confidence = v if v is not None else 0
