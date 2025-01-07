import threading

class RFSS:
    def __init__(self, rfss_id):
        self.id = rfss_id
        self._lock = threading.RLock()  # Use RLock for reentrant locking critical
        self._state = {}
        self.sites = {}

    def add_site(self, site):
        with self._lock:
            if site.id not in self.sites:
                self.sites[site.id] = site
                return True  # Return True if the site was added
            return False  # Return False if the site already exists

    def get_site(self, site_id):
        with self._lock:
            return self.sites.get(site_id)
