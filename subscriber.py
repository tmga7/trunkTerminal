import threading


class Subscriber:
    def __init__(self, subscriber_id, wuid, properties=None):
        self.id = subscriber_id
        self._lock = threading.RLock()
        self._state = properties or {}
        self.set_property('wuid', wuid)

    def set_property(self, key, value):
        with self._lock:
            self._state[key] = value

    def get_property(self, key):
        with self._lock:
            return self._state.get(key)

    def dump_properties(self):
        with self._lock:
            return print(f"Subscriber {self.id} Dump: \r\n {self._state} \n")

    def activate_talkgroup(self, talkgroup_id):
        with self._lock:
            talkgroup = f"{self.get_property('current_wacn')}-{self.get_property('current_rfss_id')}-{talkgroup_id}"
            self.set_property('active_talkgroup', talkgroup)
            return True

    def turn_on(self):
        with self._lock:
            self.control_channel_hunt()
            available_talkgroups = self.get_property('talkgroups')
            if available_talkgroups:
                self.activate_talkgroup(available_talkgroups[0])
                return True
            return None

    def can_subscriber_register(self):
        with self._lock:
            return True

    def control_channel_hunt(self):

        # TODO we want to read the current site the subscriber is on, and see if the threshold between the new site is really that much to prevent jumping

        with self._lock:
            site_table = self.get_property('site_table')
            self.set_property('current_wacn', None)
            self.set_property('current_rfss_id', None)
            self.set_property('current_site_id', None)
            self.set_property('current_subsite_id', None)

            for subsite in site_table:
                if subsite['REG_REFUSED']:
                    self.set_property('current_site', {})
                    return False

            for subsite in site_table:
                if not subsite['REG_REFUSED'] and subsite['signal_strength_dbm'] > -120:
                    self.set_property('current_wacn', subsite['wacn'])
                    self.set_property('current_rfss_id', subsite['rfss_id'])
                    self.set_property('current_site_id', subsite['site_id'])
                    self.set_property('current_subsite_id', subsite['subsite_id'])
                    return True
                return False
            return False

