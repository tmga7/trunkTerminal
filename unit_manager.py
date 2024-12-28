from events import *

class UnitManager:
    def __init__(self, event_bus, config):
        self.event_bus = event_bus
        self.config = config
        self.units = {} # Store units with their properties
        for unit_id, unit_config in config.get("units", {}).items():
            self.units[int(unit_id)] = unit_config

    def handle_radio_power_on(self, event):
        rid = event.rid
        self.event_bus.publish(RadioSiteListRequested(rid))

    def handle_radio_site_list_requested(self, event):
        rid = event.rid
        available_sites = {}
        for site_id, site_config in self.config.get("sites", {}).items():
          #check if the site is online
          site_online = True # replace with actual check in the future
          if site_online:
            available_sites[int(site_id)] = 100 # Default RSSI 100 for now. This will become more complex in the future.
        self.event_bus.publish(RadioSiteListReceived(rid, available_sites))

    def handle_radio_site_list_received(self, event):
        rid = event.rid
        sites = event.sites
        if sites:
            # Select site with highest RSSI (currently always 100)
            preferred_site = max(sites, key=sites.get)
            self.event_bus.publish(RadioRegisterRequested(rid, preferred_site))
        else:
            print(f"Radio {rid}: No available sites.")

    def handle_radio_register_requested(self, event):
        rid = event.rid
        site_id = event.site_id
        self.register_unit(rid, site_id)
        print(f"Radio {rid}: Registered on Site {site_id}")

    def handle_radio_affiliate_requested(self, event):
        rid = event.rid
        tgid = event.tgid
        self.affiliate_unit(rid, tgid)
        print(f"Radio {rid}: Affiliated with Talkgroup {tgid}")

    def handle_radio_ptt(self, event):
        rid = event.rid
        tgid = event.tgid
        call_length = event.call_length
        ckr = event.ckr
        self.event_bus.publish(CallStartRequested(rid, tgid, call_length, ckr))

    def register_unit(self, rid, site_id):
        self.event_bus.publish(UnitRegistered(rid, site_id)) # Publish the registration event

    def affiliate_unit(self, rid, tgid):
        self.event_bus.publish(UnitAffiliated(rid, tgid))

    def is_unit_tdma_capable(self, rid):
        unit = self.units.get(rid)
        if unit:
            return unit.get("prop_phase2", False) # Default to False if not present
        return False
