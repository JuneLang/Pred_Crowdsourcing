

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
        if v:
            self._data = v
        else:
            self._data = {}

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

    def totalvotes(self):
        votes = 0
        if self._versions:
            for version in self._versions:
                votes += version["votes"]
        return votes

    def group_dicts(self):
        dicts = {}
        for version in self.versions:
            if version["data"].get("value"):
                n = self._normalized_versions[version["data"]["value"]]
                if not dicts.get(n):
                    dicts.setdefault(n, [])
                    dicts[n][0] = 0
                dicts[n][0] += version["votes"]
                dicts[n].append(version)

            # for original, normalized in self._normalized_versions:
            #     if version["data"].get("value"):
            #         if version["data"]["value"] == original:
            #             if not dicts.get(normalized):
            #                 dicts.setdefault(normalized, [])
            #                 dicts.setdefault("votes", 0)
            #             dicts[normalized].append(version)
            #             dicts["votes"] += version["votes"]
        return dicts

    def to_json(self):
        json = {}
        json["id"] = self._id
        json["status"] = self.status
        json["name"] = self._name
        json["data"] = self.data
        if self.versions:
            for version in self.versions:
                if version["data"].get("value"):
                    version["normalized"] = self.normalized_versions[version["data"]["value"]]
        json["versions"] = self.versions
        return json
