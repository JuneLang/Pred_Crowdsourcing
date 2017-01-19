

class Label(object):
    def __init__(self, properties):
        self._id = properties["id"]
        self._status = properties["status"]
        self._name = properties["name"]
        self._data = properties["data"]
        self._versions = properties["versions"]  # versions of translations of users
        self._normalized_versions = {}

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, v):
        self._status = v

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, v):
        self._data = v

    @property
    def versions(self):
        return self._versions

    @versions.setter
    def versions(self, v):
        self._versions = v

    @property
    def normalized_versions(self):
        return self._normalized_versions

    @normalized_versions.setter
    def normalized_versions(self, v):
        self._normalized_versions = v
