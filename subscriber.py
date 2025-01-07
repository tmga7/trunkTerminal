import threading


class Subscriber:
    def __init__(self, subscriber_id, properties=None):
        self.id = subscriber_id
        self._lock = threading.RLock()
        self._state = properties or {}

    def set_property(self, key, value):
        with self._lock:
            self._state[key] = value

    def get_property(self, key):
        with self._lock:
            return self._state.get(key)

    def control_channel_hunt(self):

        # TODO we want to read the current site the subscriber is on, and see if the threshold between the new site is really that much to prevent jumping

        with self._lock:
            site_table = self.get_property('site_table')

            for subsite in site_table:
                if subsite['REG_REFUSED']:
                    return None

            for subsite in site_table:
                if not subsite['REG_DENY'] and subsite['signal_strength_dbm'] > -120:
                    return subsite['site_id'], subsite['subsite_id']


