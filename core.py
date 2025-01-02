from site_constants import *
from prototype_site import Site
from core_radio import Radio
from core_talkgroup import Talkgroup


class Core:
    class CallSequence:
        def __init__(self):
            self.calls = []  # [call ID
            self.time_started = None
            self.time_granted = None
            self.time_ended = None
            self.resources_ready = False
            self.status = None

    def __init__(self):
        self.sites = {}
        self.talkgroups = {}
        self.radios = {}
        self.radio_to_site = {}

    def create_radio(self, radio_id, radio_type, is_phase2_capable):
        if radio_id in self.radios:
            print(f"Radio {radio_id} already exists.")
            return
        self.radios[radio_id] = Radio(self, radio_id, radio_type, is_phase2_capable)
        print(f"Radio {radio_id} created.")

    def create_site(self, site_id):
        if site_id in self.sites:
            print(f"Site {site_id} already exists.")
            return
        self.sites[site_id] = Site(self)
        self.sites[site_id].id = site_id

        print(f"Site {site_id} created.")

    def create_talkgroup(self, tg_id, mode, allow_fdma=True, allow_tdma=True, hang_time=2500):
        if tg_id not in self.talkgroups:
            self.talkgroups[tg_id] = Talkgroup(tg_id, mode, allow_fdma, allow_tdma, hang_time)
            print(
                f"Talkgroup {tg_id} created with mode {mode} and allow fdma {allow_fdma} and tdma {allow_tdma} and hang time {hang_time}")
        else:
            print("Talkgroup already exists.")

    def add_site(self, site_id, site):
        self.sites[site_id] = site
        print(f"Site {site_id} added to core.")

    # ===== Intermediate commands while radio is not on a site

    def handle_unit_registration_request(self, radio, site_id):

        # TODO Acknowledge Response - FNE (ACK_RSP_FNE)

        # Unit Registration Response (U_REG_RSP)

        # Check if the radio is registered on any other site
        existing_site = self.radio_to_site.get(radio.id)
        if existing_site:
            # 1 Attempt deaffiliation
            self.sites[existing_site].deaffiliate(radio, radio.affiliation)
            # 2 Attempt deregistration
            self.sites[existing_site].unit_deregistration(radio)

        # Verify
        existing_site = self.find_radio_in_sites(radio.id)
        if not existing_site:
            # Let's register
            if self.sites[site_id].unit_registration(radio):
                self.radio_to_site[radio.id] = site_id
                return True
            else:
                return False

    # -->

    def dump_talkgroup_sites(self, talkgroup_ids):
        # [x,x]
        site_set = set()

        for talkgroup_id in talkgroup_ids:
            if talkgroup_id in self.talkgroups:
                for key, value in self.talkgroups[talkgroup_id].affiliations.items():
                    site_set.add(value)

        site_list = list(site_set)

        return site_list

    def dump_talkgroup_radio_ids(self, talkgroup_ids):
        # [x,x] =
        radio_list = set()

        for talkgroup_id in talkgroup_ids:
            if talkgroup_id in self.talkgroups:
                for key, value in self.talkgroups[talkgroup_id].affiliations.items():
                    radio_list.add(key)

        radios = list(radio_list)

        return radios

    def dump_call_sequences(self, site_ids):
        # [x,x] =
        seq_list = []

        for site_id in site_ids:
            if site_id == self.sites[site_id].id:
                for call in self.sites[site_id].calls:
                    if call.id not in seq_list:
                        seq_list.append(call.id)

        sequences = list(seq_list)

        return sequences

    # ===== Coordination commands
    def global_isp_group_voice_service_request(self, initiating_radio, talkgroup_ids=None):

        # Determine what sites we need for the talkgroup call to proceed
        # A console by default, will transmit on all talkgroups if not specified
        if not talkgroup_ids:
            if initiating_radio.type == RADIO_TYPE_SUBSCRIBER:
                talkgroup_ids = [next(iter(initiating_radio.affiliation))]
            elif initiating_radio.type == RADIO_TYPE_CONSOLE and not talkgroup_ids:
                talkgroup_ids = initiating_radio.affiliation

        for talkgroup_id in talkgroup_ids:
            # We will check if all radios on the talkgroup are Phase 2
            radio_list = self.dump_talkgroup_radio_ids([talkgroup_id])

            site_list = self.dump_talkgroup_sites([talkgroup_id])

            for the_site in site_list:
                self.sites[the_site].create_call(initiating_radio, talkgroup_id)

            # TODO create a master sequence of the calls we need to manage
            print(self.dump_call_sequences(site_list))

        # is_phase2_capable

    def find_radio_in_sites(self, radio_id):
        print(self.sites.items())
        for site_id, site in self.sites.items():
            if radio_id in site.radios:
                return site
        return None

    # Subscriber emulation functions
