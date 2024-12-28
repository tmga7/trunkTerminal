from events import *

class UnitManager:
    def __init__(self, event_bus, config, site_controllers, default_talkgroup):
        self.event_bus = event_bus
        self.config = config
        self.site_controllers = site_controllers  # Store site_controllers
        self.units = {}  # Store units with their properties
        self.radio_status = {}  # Dictionary to store radio status
        self.console_status = {}  # Store console status (affiliated talkgroups)
        self.site_controllers = site_controllers
        self.default_talkgroup = default_talkgroup #Store the default talkgroup
        if self.default_talkgroup is None:
            print("Warning: No default talkgroup defined in config.yaml")

        for unit_id, unit_config in config.get("units", {}).items():
            self.units[int(unit_id)] = unit_config

    def handle_radio_status_check(self, event):
        rid = event.rid
        unit_config = self.units.get(rid)

        if unit_config:  # Check if the unit exists
            print(f"Unit {rid} Status:")
            print(f"  Type: {unit_config['prop_type']}")  # Print the unit type

            if unit_config["prop_type"] == "subscriber":
                if rid in self.radio_status:
                    status = self.radio_status[rid]
                    if status["registered_site"]:
                        print(f"  Registered on Site: {status['registered_site']}")
                    else:
                        print(f"  Not Registered")

                    if status["affiliated_tg"]:
                        print(f"  Affiliated with Talkgroup: {status['affiliated_tg']}")
                    else:
                        print(f"  Not Affiliated")
                    if status["available_sites"]:
                        print("  Available Sites:")
                        for site_id, rssi in status["available_sites"].items():
                            print(f"   Site {site_id} RSSI: {rssi}")
                    else:
                        print(" No Available Sites")
                else:
                    print("  Not yet Powered On")  # Indicate that it is not powered on
            elif unit_config["prop_type"] == "console":
                if rid in self.console_status:
                    status = self.console_status[rid]
                    if status["affiliated_tgs"]:
                        print(f"  Affiliated with Talkgroups: {status['affiliated_tgs']}")
                    else:
                        print(f"  Not Affiliated with any Talkgroups")
                else:
                    print(" Not yet Powered On")  # Indicate that it is not powered on
        else:
            print(f"Unit {rid} is not a valid unit")

    def handle_radio_site_list_requested(self, event):
        rid = event.rid
        available_sites = {}
        for site_id, site_config in self.config.get("sites", {}).items():
            if self.is_site_online(int(site_id)):  # Use helper function
                available_sites[int(site_id)] = 100  # Default RSSI 100 for now
        self.event_bus.publish(RadioSiteListReceived(rid, available_sites))

    def handle_radio_check_range(self, event):
        rid = event.rid
        available_sites = {}
        for site_id, site_config in self.config.get("sites", {}).items():
            if self.is_site_online(int(site_id)):
                available_sites[int(site_id)] = 100
        if available_sites:
            print(f"Radio {rid}: Available Sites and RSSI:")
            for site_id, rssi in available_sites.items():
                print(f"  Site {site_id}: RSSI {rssi}")
        else:
            print(f"Radio {rid}: Out of range (no available sites).")

    def is_site_online(self, site_id):
        # Check if the site is online (replace with actual check in the future)
        # This implementation checks if the site has been started.
        if site_id in self.site_controllers:
            return self.site_controllers[site_id].site_started
        return False

    def handle_radio_power_on(self, event):
        rid = event.rid
        unit_config = self.units.get(rid)
        if unit_config and unit_config["prop_type"] == "subscriber":
            self.radio_status[rid] = {
                "registered_site": None,
                "affiliated_tg": None,
                "available_sites": {},
                "state": RadioState.IDLE  # Initialize state
            }
            print(f"Radio {rid}: Powered ON, State: {self.radio_status[rid]['state']}")  # Output state

            self.event_bus.publish(RadioSiteListRequested(rid))
            self.radio_status[rid] = {"registered_site": None, "affiliated_tg": None, "available_sites": {}}
            self.event_bus.publish(RadioAffiliateRequested(rid, self.default_talkgroup)) #Affiliate with default TG
        elif unit_config and unit_config["prop_type"] == "console":
            self.console_status[rid] = {"affiliated_tgs": set(), "powered_on": True}
            print(f"Console {rid} started.")

    def handle_radio_select_talkgroup(self, event):
        rid = event.rid
        new_tgid = event.tgid
        if rid in self.radio_status:
            current_tgid = self.radio_status[rid]["affiliated_tg"]
            if current_tgid:
                self.event_bus.publish(RadioDeAffiliateRequested(rid, current_tgid))
            self.event_bus.publish(RadioAffiliateRequested(rid, new_tgid))
        else:
            print(f"Radio {rid} is not powered on.")


    def handle_radio_site_list_requested(self, event):
        rid = event.rid
        available_sites = {}
        for site_id, site_config in self.config.get("sites", {}).items():
            # check if the site is online
            site_online = True  # replace with actual check in the future
            if site_online:
                available_sites[
                    int(site_id)] = 100  # Default RSSI 100 for now. This will become more complex in the future.
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
        if rid in self.radio_status:
            self.radio_status[rid]["state"] = RadioState.REGISTERING
            print(
                f"Radio {rid}: Requesting Registration on Site {event.site_id}, State: {self.radio_status[rid]['state']}")
        self.event_bus.publish(UnitRegisterRequested(rid, event.site_id))

    def handle_unit_registration_success(self, event):
        rid = event.rid
        if rid in self.radio_status:
            self.radio_status[rid]["state"] = RadioState.AFFILIATED
            print(
                f"Radio {rid}: Registration successful on Site {event.site_id}, State: {self.radio_status[rid]['state']}")

    def handle_unit_registration_failed(self, event):
        rid = event.rid
        reason = event.reason
        print(f"Radio {rid}: Registration failed: {reason}")

    def handle_radio_affiliate_requested(self, event):
        rid = event.rid
        tgid = event.tgid
        unit_config = self.units.get(rid)
        if unit_config and unit_config["prop_type"] == "console":
            self.console_status[rid]["affiliated_tgs"].add(tgid)
            self.event_bus.publish(UnitAffiliationSuccess(rid, tgid))
            print(f"Console {rid}: Affiliated with Talkgroup {tgid}")
        elif unit_config and unit_config["prop_type"] == "subscriber":
            if self.can_unit_affiliate_with_talkgroup(rid, tgid):
                self.event_bus.publish(UnitAffiliationSuccess(rid, tgid))
                print(f"Radio {rid}: Requesting Affiliation with Talkgroup {tgid}")
            else:
                self.event_bus.publish(UnitAffiliationFailed(rid, tgid, "Talkgroup mode mismatch or talkgroup does not exist."))
                print(f"Radio {rid}: Affiliation with Talkgroup {tgid} Failed")

    def handle_unit_affiliation_success(self, event):
        rid = event.rid
        tgid = event.tgid
        if rid in self.radio_status:
            self.radio_status[rid]["affiliated_tg"] = tgid
        print(f"Radio {rid}: Affiliated with Talkgroup {tgid}")

    def handle_unit_affiliation_failed(self, event):
        rid = event.rid
        reason = event.reason
        print(f"Radio {rid}: Affiliation failed: {reason}")

    def is_talkgroup_allowed_on_site(self, tgid, site_id):
        site_config = None
        for s_id, s_config in self.config.get("sites", {}).items():
            if int(s_id) == site_id:
                site_config = s_config
                break
        if site_config and "allowed_talkgroups" in site_config:
            return tgid in site_config["allowed_talkgroups"]
        return True  # Default to true if not specified

    def can_unit_affiliate_with_talkgroup(self, rid, tgid):
        tg_config = None
        for tg_id, tg in self.config.get("talkgroups", {}).items():
            if int(tg_id) == tgid:
                tg_config = tg
                break

        if not tg_config:
            return False

        unit_tdma_capable = self.is_unit_tdma_capable(rid)
        tg_mode = tg_config.get("prop_mode")

        if tg_mode == "tdma" and not unit_tdma_capable:
            return False
        elif tg_mode == "fdma" and unit_tdma_capable:
            return False

        return True

    def handle_console_call_preempt(self, event):
        print("Console preempted ongoing call.")

    def handle_subscriber_call_preempt(self, event):
        print("Subscriber preempted ongoing console call.")

    def handle_radio_ptt(self, event):
        rid = event.rid
        tgid = event.tgid
        call_length = event.call_length
        ckr = event.ckr
        unit_config = self.units.get(rid)
        if rid in self.radio_status:
            self.radio_status[rid]["state"] = RadioState.TRANSMITTING
            print(f"Radio {rid}: PTT Pressed, State: {self.radio_status[rid]['state']}")

        if unit_config and unit_config["prop_type"] == "console":
            self.event_bus.publish(ConsoleCallStartRequested(rid, tgid, call_length))
        elif unit_config and unit_config["prop_type"] == "subscriber":
            self.event_bus.publish(CallStartRequested(rid, tgid, call_length, ckr))

    def register_unit(self, rid, site_id):
        self.event_bus.publish(UnitRegistered(rid, site_id))  # Publish the registration event

    def affiliate_unit(self, rid, tgid):
        self.event_bus.publish(UnitAffiliated(rid, tgid))

    def is_unit_tdma_capable(self, rid):
        unit = self.units.get(rid)
        if unit:
            return unit.get("prop_phase2", False)  # Default to False if not present
        return False
