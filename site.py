import threading


class Site:
    def __init__(self, site_id, properties=None):
        self.id = site_id
        self._lock = threading.RLock()
        self._state = properties or {}  # Initialize _state directly
        self.channels = {}
        self.subsites = {}

    def set_property(self, key, value):
        with self._lock:
            self._state[key] = value

    def get_property(self, key):
        with self._lock:
            return self._state.get(key)

    def add_channel(self, channel):
        with self._lock:
            self.channels[channel.id] = channel

    def get_channel(self, channel_id):
        with self._lock:
            return self.channels.get(channel_id)

    def add_subsite(self, subsite):
        with self._lock:
            self.subsites[subsite.id] = subsite

    def get_subsite(self, subsite_id):
        with self._lock:
            return self.subsites.get(subsite_id)

    def is_group_prohibited_group(self, group_id):
        return group_id in self.get_property("prohibited_groups")

    def is_group_prohibited_subscriber(self, subscriber_id):
        return subscriber_id in self.get_property("prohibited_subscriber")