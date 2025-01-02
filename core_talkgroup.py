class Talkgroup:

    def __init__(self, tg_id, mode, allow_fdma=True, allow_tdma=True, hang_time=2500):
        self.id = tg_id
        self.mode = mode
        self.affiliations = {} # [site ID][talkgroup ID]
        self.allow_fdma = allow_fdma
        self.allow_tdma = allow_tdma
        self.allow_site_wait = True
        self.hang_time = hang_time
        self.in_emergency = False

    def add_affiliated_radio(self, radio):
        self.affiliations.add(radio)
        radio.affiliation.add(self.id)
