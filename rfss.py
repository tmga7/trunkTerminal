import threading
import random
import time
from datetime import datetime, timedelta

class RFSS:
    def __init__(self, wacn_id, rfss_id):
        self._lock = threading.RLock()
        self._state = {}
        self.id = rfss_id
        self.wacn = wacn_id
        self.sites = {}
        self.consoles = {}
        self.subscribers = {}
        self.talkgroups = {}
        self.groups = {}
        self.registers = {}
        self.affiliations = {}
        self.operating_area = None
        # --- RFSS/System Policy Flags (Load from config ideally) ---
        # These determine the general policy for this RFSS
        self._properties = {}  # Placeholder for RFSS-level properties from config
        self._properties.setdefault('allow_roaming', True)
        self._properties.setdefault('allow_phase1_registrations', True)
        self._properties.setdefault('allow_phase2_registrations', True)

    def set_sub_location(self, subscriber_id, lat=None, lon=None, min_lat=None, max_lat=None, min_lon=None, max_lon=None):
        if lat is None and lon is None:
            lat = random.uniform(min_lat, max_lat)
            lon = random.uniform(min_lon, max_lon)

        subscriber = self.get_subscriber(subscriber_id)
        if subscriber:
            subscriber.set_property("location", {'latitude': lat, 'longitude': lon})
            print(f"Subscriber {subscriber_id} location set to {lat}, {lon}")

    def add_affiliation(self, talkgroup_id, wuid, site_id):
        with self._lock:
            if talkgroup_id not in self.affiliations:
                self.affiliations[talkgroup_id] = {}
            self.affiliations[talkgroup_id][wuid] = site_id
            return True

    def remove_affiliation(self, talkgroup_id, wuid):
        with self._lock:
            if talkgroup_id in self.affiliations and wuid in self.affiliations[talkgroup_id]:
                site_id = self.affiliations[talkgroup_id].pop(wuid)
                return True
            elif talkgroup_id not in self.affiliations:
                return False
            elif wuid not in self.affiliations[talkgroup_id]:
                return False
            return False

    def add_console(self, console):
        with self._lock:
            if console.id not in self.consoles:
                self.consoles[console.id] = console
                return True  # Return True if added
            return False  # Return False if already exists

    def get_console(self, console_id):
        with self._lock:
            return self.consoles.get(console_id)

    def add_subscriber(self, subscriber):
        with self._lock:
            if subscriber.id not in self.subscribers:
                self.subscribers[subscriber.id] = subscriber
                # self.subscribers_by_id[subscriber.id] = subscriber
                return True
            return False

    def get_subscriber(self, subscriber_id):
        with self._lock:
            return self.subscribers.get(subscriber_id)

    def add_talkgroup(self, talkgroup):
        with self._lock:
            if talkgroup.id not in self.talkgroups:
                self.talkgroups[talkgroup.id] = talkgroup

    def get_talkgroup(self, talkgroup_id):
        with self._lock:
            return self.talkgroups.get(talkgroup_id)

    def add_group(self, group):
        with self._lock:
            self.groups[group.id] = group

    def add_site(self, site):
        with self._lock:
            if site.id not in self.sites:
                self.sites[site.id] = site
                return True  # Return True if the site was added
            return False  # Return False if the site already exists

    def get_site(self, site_id):
        with self._lock:
            return self.sites.get(site_id)

    def register_subscriber(self, wuid, site_id, is_phase2):
        with (self._lock):
            parts = wuid.split('-')

            if len(parts) == 3:
                wacn_id = parts[0]
                rfss_id = parts[1]
                subscriber_id = parts[2]

            if wacn_id == self.wacn and rfss_id == self.id:
                foreign = False
            else:
                foreign = True

            #TODO are they allowed to register? i.e. group they are part, ID allowed on site, roaming allowed?
            allow_registration = True

            if allow_registration:
                # self.subscribers[subscriber_id].dump_properties()
                self.registers[wuid] = {
                    "foreign": foreign,
                    "site_id": site_id,
                    "registered": True,
                    "registration_time": datetime.now(),
                    "is_phase2": is_phase2,
                    "last_status_poll": datetime.now(),
                    # "priority": group_priority, TODO add priority from group class
                }
                return True
            else:
                return False

    def validate_affiliation(self, wuid, talkgroup_id):
        registration_info = self.registers.get(wuid)
        print(f"Talkgroup jeys of RFSS {self.id}: {self.talkgroups.keys()}")

        talkgroup = self.get_talkgroup(talkgroup_id)

        if not registration_info:
            print(f"Affiliation Validation Failed for WUID {wuid}: Not registered on this RFSS.")
            return False, "NOT_REGISTERED"

        if not talkgroup:
            print(f"Affiliation Validation Failed for WUID {wuid}: Talkgroup {talkgroup_id} does not exist on RFSS {self.id}.")
            return False, "TG_NOT_FOUND"

        if not talkgroup.get_property("enabled"):
            print(f"Affiliation Validation Failed for WUID {wuid}: Talkgroup {talkgroup_id} is disabled.")
            return False, "TG_DISABLED"

        if not talkgroup.get_property("allow_voice_transmission"):
            print(
                f"Affiliation Validation Failed for WUID {wuid}: Talkgroup {talkgroup_id} does not allow voice transmissions.")
            return False, "VOICE_NOT_ALLOWED"

        tg_modulation = talkgroup.get_property("modulation")
        unit_is_phase2 = registration_info.get("is_phase2")

        if tg_modulation in ("fdma", "tdma", "mixed"):
            if unit_is_phase2 is False and tg_modulation == "tdma":
                print(
                    f"Affiliation Validation Failed for WUID {wuid}: Phase 1 unit cannot affiliate with a TDMA-only Talkgroup {talkgroup_id}.")
                return False, "INCOMPATIBLE_MODULATION"
            elif unit_is_phase2 is False and tg_modulation == "mixed":
                print(
                    f"Affiliation Validation: Phase 1 unit affiliated with Mixed-mode Talkgroup {talkgroup_id} (potential downgrade to FDMA).")
                return True, "OK_MIXED_POTENTIAL_DOWNGRADE"
            elif unit_is_phase2 is False and tg_modulation == "fdma":
                return True, "OK_FDMA"
            elif unit_is_phase2 is True and tg_modulation == "fdma":
                return True, "OK_FDMA"
            elif unit_is_phase2 is True and tg_modulation == "tdma":
                return True, "OK_TDMA"
            elif unit_is_phase2 is True and tg_modulation == "mixed":
                print(
                    f"Affiliation Validation: Phase 2 unit affiliated with Mixed-mode Talkgroup {talkgroup_id} (using TDMA).")
                return True, "OK_MIXED_TDMA"  # Assuming TDMA is preferred for Phase 2 on mixed

        # If modulation is something else or not specified, allow it for now
        return True, "OK"

    def set_property(self, key, value):
        """Sets an RFSS-level property."""
        with self._lock:
            self._properties[key] = value

    def get_property(self, key, default=None):
        """Gets an RFSS-level property."""
        with self._lock:
            return self._properties.get(key, default)

    def process_registration_attempt(self, wuid, site_id, is_phase2, home_rfss_id):
        """
        Validates a registration request received by this RFSS and updates
        local registers if the registration is permitted and successful.

        Args:
            wuid (str): The WUID of the registering subscriber (e.g., "WACN-HomeRFSS-SubID").
            site_id (int/str): The target site ID within this RFSS.
            is_phase2 (bool): If the subscriber is reporting Phase 2 capability via the request.
            home_rfss_id (int/str): The designated home RFSS ID of the subscriber.

        Returns:
            tuple: (success_bool, reason_string, registration_details_dict or None)
                   If successful, reason is 'REG_ACCEPT' and registration_details contains
                   information like 'registration_time', 'last_status_poll'.
                   If failed, reason indicates why (e.g., 'REG_DENY_SITE_DISABLED').
        """
        # --- Critical Section for RFSS state ---
        with self._lock: # Protect access to self.sites and self.registers

            print(f"RFSS {self.id}: Registration Request for {wuid} on site {site_id} home_rfss_id(: {home_rfss_id}, Phase2: {is_phase2} sitekeys = {self.sites.keys()}).")

            # --- 1. Site Validation ---
            site = self.sites.get(site_id)
            if not site:
                log_msg = f"RFSS {self.id}: Registration DENIED for {wuid}. Reason: Target Site {site_id} not found."
                print(log_msg)
                # Use a reason code defined in P25 standards if possible, otherwise use descriptive string
                return False, 'REG_FAIL', None # Or 'REG_DENY'? Standard says Fail if site unknown

            # Check if the site itself is enabled/operational
            # Assuming Site object has a way to report its status (e.g., a property)
            # NOTE: If registration happens at a Subsite level, check the specific subsite status instead/as well.
            if not site.get_property('enabled'): # Example property check
                 log_msg = f"RFSS {self.id}: Registration DENIED for {wuid} on site {site_id}. Reason: Site is disabled."
                 print(log_msg)
                 return False, 'REG_DENY', None # Denied because site unavailable

            # --- 2. Capability Validation (RFSS/Site vs Subscriber) ---
            rfss_allows_phase = self.get_property('allow_phase2_registrations') if is_phase2 else self.get_property('allow_phase1_registrations')
            if not rfss_allows_phase:
                phase = "Phase 2" if is_phase2 else "Phase 1"
                log_msg = f"RFSS {self.id}: Registration DENIED for {wuid} on site {site_id}. Reason: RFSS does not allow {phase} registrations."
                print(log_msg)
                return False, 'REG_DENY', None # Denied by RFSS policy

            # Optionally, check if the SITE specifically supports the phase
            site_supports_phase = site.get_property('supports_phase2') if is_phase2 else site.get_property('supports_phase1', True) # Default allow P1
            if not site_supports_phase:
                phase = "Phase 2" if is_phase2 else "Phase 1"
                log_msg = f"RFSS {self.id}: Registration DENIED for {wuid} on site {site_id}. Reason: Site does not support {phase}."
                print(log_msg)
                # Consider if this should be DENY or REFUSED based on standard interpretation
                return False, 'REG_DENY', None

            # --- 3. Subscriber/Roaming Validation ---
            is_foreign = (str(self.id) != str(home_rfss_id))

            if is_foreign:
                # Check RFSS roaming policy first
                if not self.get_property('allow_roaming', True): # Default allow if property missing
                     log_msg = f"RFSS {self.id}: Registration DENIED for roaming {wuid}. Reason: Roaming not allowed on this RFSS."
                     print(log_msg)
                     return False, 'REG_DENY', None # Denied by RFSS policy

                # Check Site-specific roaming policy (if it exists and overrides RFSS)
                site_allow_roaming = site.get_property('allow_roaming') # Can be True, False, or None (inherit)
                if site_allow_roaming is False: # Site explicitly denies roaming
                     log_msg = f"RFSS {self.id}: Registration DENIED for roaming {wuid}. Reason: Roaming not allowed on Site {site_id}."
                     print(log_msg)
                     return False, 'REG_DENY', None # Denied by Site policy

                # TODO: Add more granular roaming checks if needed:
                # - Allow only specific WACNs/RFSSs?
                # - Check roaming agreements?

            # TODO: Add other subscriber validation checks if required:
            # - Is the WUID in a valid range or format?
            # - Is the WUID on a specific deny list for this RFSS/Site?
            # - Does the subscriber's group have registration permission here?

            # --- 4. Success - Update Registration State ---
            # If all checks passed, proceed with registration
            registration_time = datetime.now()

            # Prepare the details to store in the RFSS's register
            registration_entry = {
                "foreign": is_foreign,
                "site_id": site_id,
                "registered": True, # Mark as registered ON THIS RFSS
                "registration_time": registration_time,
                "is_phase2": is_phase2,
                "last_status_poll": registration_time, # Initialize poll time to registration time
                # Add other relevant details if needed, e.g., subscriber priority
            }

            # Update the RFSS's register dictionary
            self.registers[wuid] = registration_entry

            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            log_msg = f"[{timestamp_str}] RFSS {self.id}: Registration ACCEPTED for {wuid} on site {site_id} (Foreign: {is_foreign}, Phase2: {is_phase2})."
            print(log_msg)

            # Prepare details to return to SimulatorInstance for the global table
            return_details = {
                'registration_time': registration_time,
                'last_status_poll': registration_time
                # Include other details if the central table needs them directly from here
            }

            return True, 'REG_ACCEPT', return_details
        # --- End Critical Section ---

    def process_deregistration(self, wuid):
         """ Removes a subscriber's registration entry from this RFSS."""
         with self._lock:
             if wuid in self.registers:
                 del self.registers[wuid]
                 timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                 print(f"[{timestamp_str}] RFSS {self.id}: Deregistered {wuid} locally.")
                 return True
             else:
                 # It's okay if it wasn't registered; might be a stale request
                 # print(f"RFSS {self.id}: Deregistration request for {wuid} - unit not registered locally.")
                 return False # Indicate unit wasn't present
