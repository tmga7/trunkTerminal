import threading


class Group:
    def __init__(self, group_id, properties=None):
        self.id = group_id
        self._lock = threading.RLock()
        self._state = properties or {}

    def set_property(self, key, value):
        with self._lock:
            self._state[key] = value

    def get_property(self, key):
        with self._lock:
            return self._state.get(key)

    def is_subscriber_in_group(self, subscriber_id):
        return subscriber_id in self.get_property("subscribers")

    def is_talkgroup_in_group(self, talkgroup_id):
        return talkgroup_id in self.get_property("talkgroups")
