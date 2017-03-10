from datetime import datetime
from User import User


class Label(object):
    def __init__(self, properties):
        self.id = properties["id"]
        self._status = properties["status"]
        self._name = properties["name"]
        self._data = properties["data"]
        self.user_list = []

        self._versions = []  # versions of translations of users
        self.versions = properties["versions"]
        self._normalized_versions = {}
        self._ratio = 0.0
        self._freq_list = []


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
        if v and self._data.get("value"):
            self._data["value"] = v
        else:
            self._data = {}

    @property
    def versions(self):
        return self._versions

    @versions.setter
    def versions(self, v):
        self._versions = v
        # get the user information by the way
        for version in self._versions:
            for inst in version["instances"]:
                u = User(inst["user_id"])
                u.label_list.append(self)
                self.user_list.append(u)

    @property
    def normalized_versions(self):
        return self._normalized_versions

    @normalized_versions.setter
    def normalized_versions(self, v):
        self._normalized_versions = v

    @property
    def ratio(self):
        return self._ratio

    @ratio.setter
    def ratio(self, v):
        self._ratio = v if v else self._ratio

    @property
    def freq_list(self):
        return [group.aggMap for group in self._freq_list]

    @freq_list.setter
    def freq_list(self, v):
        self._freq_list = v if v is not None else []

    def totalvotes(self):
        votes = 0
        if self._versions is not None:
            for version in self._versions:
                votes += version["votes"]
        return votes

    # def group_dicts(self):
    #     dicts = {}
    #     for version in self.versions:
    #         if version["data"].get("value"):
    #             n = self._normalized_versions[version["data"]["value"]]
    #             if not dicts.get(n):
    #                 dicts.setdefault(n, [])
    #                 dicts[n][0] = 0
    #             dicts[n][0] += version["votes"]
    #             dicts[n].append(version)
    #
    #     return dicts

    # def group_dicts(self):
    #     versions = []
    #     for group in self.freq_list:
    #         version = {}
    #         default_proposition = group.items()[0]
    #         temp = {"values": default_proposition[0]}
    #         version.setdefault("data", temp)
    #         version.setdefault()

    def votes_sequence(self):
        seq = []
        if self.versions and (self.data is not None) and self.data.get("value"):
            for version in self.versions:
                for instance in version["instances"]:
                    created = instance["created"]
                    time = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
                    if len(seq) < 1:
                        if version["data"]["value"] == "":
                            seq.append(("", time))
                        else:
                            seq.append((self.normalized_versions[version["data"]["value"]], time))
                    else:
                        for i in range(len(seq)):
                            if time <= seq[i][1]:
                                if version["data"]["value"] == "":
                                    seq.insert(i, ("_emptyKey", time))
                                else:
                                    seq.insert(i, (self.normalized_versions[version["data"]["value"]], time))
                                break
                        if version["data"]["value"] == "":
                            seq.insert(i, ("_emptyKey", time))
                        else:
                            seq.insert(i, (self.normalized_versions[version["data"]["value"]], time))
                        break

        seq = [s[0] for s in seq]
        return seq

    def to_json(self):
        json = {}
        json["id"] = self.id
        json["status"] = self.status
        json["name"] = self._name
        json["data"] = self.data
        if self.versions:
            for version in self.versions:
                if version["data"].get("value"):
                    version["normalized"] = self.normalized_versions[version["data"]["value"]]
        json["versions"] = self.versions
        return json
