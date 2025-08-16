import threading


class Subsite:
    def __init__(self, subsite_id, properties=None):
        self.id = subsite_id
        self._lock = threading.RLock()
        self._state = properties or {}  # Initialize _state directly

    def set_property(self, key, value):
        with self._lock:
            self._state[key] = value

    def get_property(self, key):
        with self._lock:
            return self._state.get(key)
