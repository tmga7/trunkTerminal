import random


def rssi_calculate(level):
    if -130 <= level <= -114:
        return (level + 130) * (20 / 16)  # Convert to RSSI 0-19
    elif -115 <= level <= -94:
        return (level + 115) * (20 / 21) + 20  # Convert to RSSI 20-39
    elif -95 <= level <= -79:
        return (level + 95) * (20 / 16) + 40  # Convert to RSSI 40-59
    elif -80 <= level <= -64:
        return (level + 80) * (20 / 16) + 60  # Convert to RSSI 60-79
    elif -65 <= level <= -50:
        return (level + 65) * (20 / 15) + 80  # Convert to RSSI 80-100
    return 0  # Return 0 if out of range


class Radio:

    def __init__(self, core, radio_id, radio_type, is_phase2_capable=False):
        self.id = radio_id
        self.core = core
        self.site = None
        self.type = radio_type
        self.is_phase2_capable = is_phase2_capable  # add the property
        self.is_on = False
        self.in_emergency = False
        self.rssi = None
        self.affiliation = set()

    def register(self, site_id):

        # We rely on core because we have no site to talk to yet
        if self.core.handle_unit_registration_request(self, site_id):
            return True

    def site_search(self):
        rssi_list = []

        for site_id, site in self.core.sites.items():
            # TODO Here is where we would get location of subscriber, and location of the site, and come up with dBm
            #  level
            result_level = random.randint(-130, -50)
            rssi_value = rssi_calculate(result_level)
            rssi_list.append((site_id, rssi_value))

        # TODO For now, we just sort by best signal, but future radio groups would allow site selection (always, preferred, never)
        rssi_list.sort(key=lambda x: x[1], reverse=True)

        print(rssi_list)

        if rssi_list:
            best_site_id = rssi_list[0][0]
            print(f"Best site ID based on RSSI: {best_site_id}")

            # Now we see if we are the best site, and if so, move to it
            # if self.site.id != best_site_id:
            # self.register(best_site_id)

            return best_site_id

    def turn_on(self, talkgroup_ids):

        print(f"Radio {self.id} turn on")

        if self.register(self.site_search()):
            # Now we can try and affiliate
            self.site.group_affiliation_request(self, talkgroup_ids)

        # self.request_talkgroup(self)

    def subscriber_group_ptt(self):
        #
        print("ptt starts")
        self.core.global_isp_group_voice_service_request(self)
        print("ptt --> finish")

