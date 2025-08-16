import json
import queue
import random
import threading
import time
import uuid
from datetime import datetime, timedelta

from channel import Channel
from console import Console
from rfss import RFSS
from site import Site
from subscriber import Subscriber
from subsite import Subsite
from talkgroup import Talkgroup
from utils import GeospatialUtils
from group import Group


# Traffic and Control Channel

class WACN:
    def __init__(self, wacn_id):
        self.id = wacn_id
        self._lock = threading.RLock()


class SimulatorInstance:
    def __init__(self, wacn_id):
        self.id = str(uuid.uuid4())  # Needs to be unique to all users
        self.wacn = WACN(wacn_id)
        self.event_queue = queue.PriorityQueue()
        self.busy_queue = queue.PriorityQueue()
        self.lock = threading.RLock()
        self.stop_flag = threading.Event()
        self.operating_area = []

        # --- Initialize the Central Registration Table ---
        self.global_registrations = {}
        # Structure: {
        #    'WUID-string': {
        #        'HomeRFSS': id,
        #        'CurrentRFSS': id or None,
        #        'CurrentSiteID': id or None,
        #        'Registered': True/False,
        #        'RegistrationTimestamp': datetime or None,
        #        'LastPollTimestamp': datetime or None,
        #        'IsPhase2': True/False/None,
        #        'IsForeign': True/False/None
        #    },
        #    ...
        # }
        # --- End Initialization ---

        self.su_locale = {}
        self.talkgroup_register = {}
        self.rfss = {}
        self.event_handlers = {
            # Human Interface ISPs
            "SUBSCRIBER_TURN_ON": self._sub_turn_on,
            "SUBSCRIBER_TURN_OFF": self._sub_turn_off,
            "SUBSCRIBER_TRIGGER_SITE_HUNT": self._sub_trigger_site_hunt,
            "SUBSCRIBER_TRIGGER_GROUP_AFFILIATION": self._sub_trigger_group_affiliation,
            # Control and Status ISPs
            "U_REG_REQ": self._handle_u_reg_req,  # Unit Registration Request
            "U_DE_REG_REQ": self._handle_u_de_reg_req,  # De-Registration Request
            "GRP_AFF_REQ": self._handle_grp_aff_req,  # Group Affiliation Request
            # Control and Status OSPs
            "U_REG_RSP": self._handle_u_reg_rsp,  # Unit Registration Response
            "STS_Q": self._handle_sts_q,  # Unit Registration Response
            # Voice Service ISPs
            # Voice Service OSPs
            # Data Service ISPs
            # Data Service OSPs

        }

    def _get_subscriber_object_by_wuid(self, wuid):
        """Retrieves the Subscriber object using its WUID."""
        try:
            parts = wuid.split('-')
            if len(parts) == 3:
                # Assuming WUID format is WACN-HomeRFSS-SubID
                home_rfss_id = int(parts[1])
                subscriber_id = int(parts[2])
                # Access RFSS dictionary safely
                with self.lock:  # Protect access to self.rfss dict
                    home_rfss = self.rfss.get(home_rfss_id)
                if home_rfss:
                    # Access subscriber dictionary safely (using RFSS lock)
                    with home_rfss._lock:  # Protect access to RFSS's subscribers
                        return home_rfss.get_subscriber(subscriber_id)
        except (ValueError, IndexError, KeyError) as e:
            print(f"Error parsing WUID {wuid} or finding subscriber: {e}")
        return None

    def init_load_config(self, config_data, wacn_id):

        with (self.wacn._lock):

            # We need to do some basic geofencing
            # TODO upgrade to geofencing for subscribers, so they can move within selected geogrpahic areas (i.e. police district)
            if config_data.get("operating_area"):
                top_left = config_data.get("operating_area").get("top_left")
                bottom_right = config_data.get("operating_area").get("bottom_right")
                self.operating_area = {
                    'min_latitude': bottom_right['latitude'],
                    'max_latitude': top_left['latitude'],
                    'min_longitude': top_left['longitude'],
                    'max_longitude': bottom_right['longitude']
                }

            for rfss_data in config_data.get("rfss", []):
                rfss_id = rfss_data.get("id")
                if rfss_id:
                    rfss = RFSS(wacn_id, rfss_id)

                    # Load RFSS level consoles
                    for console_data in rfss_data.get("consoles", []):
                        console_id = console_data.get("id")
                        if console_id:
                            console = Console(console_id, console_data)
                            rfss.add_console(console)

                    # Load RFSS level subscribers
                    for subscriber_data in rfss_data.get("subscribers", []):
                        subscriber_id = subscriber_data.get("id")
                        if subscriber_id:
                            wuid = f"{wacn_id}-{rfss_id}-{subscriber_id}"
                            subscriber = Subscriber(subscriber_id, wuid, subscriber_data)
                            rfss.add_subscriber(subscriber)
                            # TODO remove this when we have a better way to handle subscriber turn on/off
                            self.add_event(0, "SUBSCRIBER_TURN_ON", 2,
                                           {'wacn_id': wacn_id, 'rfss_id': rfss_id, 'subscriber_id': subscriber_id})
                            # TODO Fow now, we randomly assign in operating area, but in the future this may be preloaded by a geo zone
                            rfss.set_sub_location(subscriber_id, None, None, self.operating_area.get('min_latitude'),
                                                  self.operating_area.get('max_latitude'),
                                                  self.operating_area.get('min_longitude'),
                                                  self.operating_area.get('max_longitude'))

                    # Load RFSS level talkgroups
                    for talkgroup_data in rfss_data.get("talkgroups", []):
                        talkgroup_id = talkgroup_data.get("id")
                        if talkgroup_id:
                            talkgroup = Talkgroup(talkgroup_id, talkgroup_data)
                            rfss.add_talkgroup(talkgroup)

                    # Load RFSS level groups
                    for group_data in rfss_data.get("groups", []):
                        group_id = group_data.get("id")
                        if group_id:
                            group = Group(group_id, group_data)
                            rfss.add_group(group)

                    # Load sites, channels, and subsites for the RFSS
                    for site_data in rfss_data.get("sites", []):
                        site_id = site_data.get("id")
                        if site_id:
                            site = Site(site_id, site_data)
                            if rfss.add_site(site):
                                for channel_data in site_data.get("channels", []):
                                    channel_id = channel_data.get("id")
                                    if channel_id:
                                        channel = Channel(channel_id, channel_data)
                                        site.add_channel(channel)
                                for subsite_data in site_data.get("subsites", []):
                                    subsite_id = subsite_data.get("id")
                                    if subsite_id:
                                        subsite = Subsite(subsite_id, subsite_data)
                                        site.add_subsite(subsite)
                    self.rfss[rfss_id] = rfss

        print("Configuration Loaded")

    def set_property(self, key, value):
        with self._lock:
            self._state[key] = value

    def get_property(self, key):
        with self._lock:
            return self._state.get(key)

    def get_subscriber_property(self, wuid, key):
        with self.lock:
            with self.wacn._lock:
                parts = wuid.split('-')
                if len(parts) == 3:
                    rfss_id = parts[1]
                    subscriber_id = parts[2]

                    rfss = self.rfss.get(rfss_id)
                    if rfss:
                        subscriber = rfss.get_subscriber(subscriber_id)
                        if subscriber:
                            return subscriber.get_property(key)
                        return None
                    return None
                return None

    def init_start(self):
        self.thread = threading.Thread(target=self.queue_monitor)
        self.thread.start()

    def init_stop(self):
        self.stop_flag.set()
        self.thread.join()

    def tool_sub_site_table(self, rfss_id, subscriber_id):
        with self.lock:
            all_sites = self.tool_list_all_subsites()
            with self.wacn._lock:
                rfss = self.rfss.get(rfss_id)
                if rfss:
                    subscriber = rfss.get_subscriber(subscriber_id)
                    if subscriber:
                        sub_location = subscriber.get_property("location")
                        sub_table = []
                        for site_info in all_sites:
                            distance = GeospatialUtils.distance_between_points(
                                sub_location['latitude'], sub_location['longitude'], site_info.get('latitude'),
                                site_info.get('longitude'))
                            signal_strength_dbm, rssi_level = GeospatialUtils.estimate_rssi(distance, site_info.get(
                                'operating_radius'))
                            sub_table.append({
                                "wacn": site_info.get('wacn'),
                                "rfss_id": site_info.get('rfss_id'),
                                "site_id": site_info.get('site_id'),
                                "subsite_id": site_info.get('subsite_id'),
                                "signal_strength_dbm": signal_strength_dbm,
                                "rssi_level": rssi_level,
                                "REG_DENY": False,
                                "REG_REFUSED": False
                            })
                        # TODO make an option to preference on home RFSS
                        """
                        def sort_key(item):
                            return (item['rfss_id'], -item['signal_strength_dbm'])
                        sorted_subsites = sorted(sub_table, key=sort_key)
                        """

                        sorted_subsites = sorted(sub_table, key=lambda x: x["signal_strength_dbm"], reverse=True)
                        subscriber.set_property("site_table", sorted_subsites)

    def tool_subscriber_group_property(self, subscriber_id, property):

        with self.lock:
            with self.wacn._lock:
                for group in self.wacn.groups.values():
                    if group.is_subscriber_in_group(subscriber_id):
                        return group.get_property(property)
                return None

    def tool_talkgroup_group_property(self, talkgroup_id, property):

        with self.lock:
            with self.wacn._lock:
                for group in self.wacn.groups.values():
                    if group.is_talkgroup_in_group(talkgroup_id):
                        return group.get_property(property)
                return None

    def tool_list_all_subsites(self):
        all_subsites = []
        with self.lock:
            for rfss in self.rfss.values():
                for site in rfss.sites.values():
                    for subsite in site.subsites.values():
                        if not subsite.get_property(
                                "disabled"):  # TODO we need change this to reflect a site status when it goes offline
                            all_subsites.append({
                                "wacn": self.wacn.id,
                                "rfss_id": rfss.id,
                                "site_id": site.id,
                                "subsite_id": subsite.id,
                                "latitude": subsite.get_property("latitude"),
                                "longitude": subsite.get_property("longitude"),
                                "operating_radius": subsite.get_property("operating_radius")
                            })
        return all_subsites

    def add_event(self, priority, event, event_time_seconds=0, metadata=None):
        # Calculate the event time
        # print("we are in add event")

        current_time = datetime.now()
        event_time_delta = timedelta(seconds=event_time_seconds)
        event_time = current_time + event_time_delta

        # Handle rollover to the next day
        event_time_seconds_total = (current_time.hour * 3600 + current_time.minute * 60 +
                                    current_time.second + current_time.microsecond / 1e6 + event_time_seconds)
        event_time_seconds_total %= 86400  # Total seconds in a day
        event_time = (current_time.replace(hour=0, minute=0, second=0, microsecond=0) +
                      timedelta(seconds=event_time_seconds_total))

        precise_event_time = event_time.timestamp()

        with self.lock:
            self.event_queue.put((priority, precise_event_time, event, metadata))

        # Add timestamp to the print statement
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        print(
            f"[{timestamp}] System Added event: {event} with priority {priority}, scheduled for {datetime.fromtimestamp(precise_event_time).strftime('%Y-%m-%d %H:%M:%S.%f')}, metadata: {metadata}")

    def queue_monitor(self):
        while not self.stop_flag.is_set():
            try:
                current_time = time.time()

                # Print the contents of the event queue for debugging
                print(f"System Event Queue State: {list(self.event_queue.queue)}")

                # Process Event Queue
                events_to_requeue = []
                while not self.event_queue.empty():
                    priority, event_time, event, metadata = self.event_queue.get()
                    if current_time >= event_time:
                        self.process_event(priority, event, metadata)
                    else:
                        events_to_requeue.append((priority, event_time, event, metadata))

                # Requeue the events that are not yet due
                for event in events_to_requeue:
                    self.event_queue.put(event)

                # Process Busy Queue
                self.process_busy_queue()

                # Print the contents of the busy queue for debugging
                print(f"System Busy Queue State: {list(self.busy_queue.queue)}")

                # Sleep for 500ms to avoid busy waiting
                time.sleep(1.5)

            except queue.Empty:
                continue

    def process_event(self, priority, event, metadata):
        handler = self.event_handlers.get(event)
        if handler:
            handler(priority, metadata)
        else:
            print(f"Unknown event type: {event}")

            print(
                f"[Processing event: {event} with priority {priority}")

            # If event needs to be reprocessed, move it to the busy queue
            # if metadata and metadata.get('reprocess'):
            #    with self.lock:
            #        self.busy_queue.put((priority, time.time(), event, metadata))

    def process_busy_queue(self):
        while not self.busy_queue.empty():

            priority, event_time, event, metadata = self.busy_queue.get()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            if self.channel_free or (metadata and metadata.get('force_process')):
                print(f"[{timestamp}] System: Processing busy queue event: {event} with priority {priority}")
                # Simulate processing time
                time.sleep(random.uniform(0.5, 1.5))
                # Move the event back to the event queue for reprocessing
                self.event_queue.put((priority, event_time, event, metadata))
                self.busy_queue.task_done()
            else:
                self.busy_queue.put((priority, event_time, event, metadata))
                break

    ####### EVENT HANDLERS START

    def _sub_turn_on(self, priority, metadata):
        wacn_id = metadata.get("wacn_id")
        rfss_id = metadata.get("rfss_id")
        subscriber_id = metadata.get("subscriber_id")

        # What is our list of sites that the radio can see?
        self.tool_sub_site_table(rfss_id, subscriber_id)

        with self.lock:
            with self.wacn._lock:
                rfss = self.rfss.get(rfss_id)
                if rfss:
                    subscriber = rfss.get_subscriber(subscriber_id)
                    if subscriber:
                        if subscriber.turn_on():
                            self.add_event(10, "U_REG_REQ", 1,
                                           {'target_rfss_id': subscriber.get_property('current_rfss_id'),
                                            'target_site_id': subscriber.get_property('current_site_id'),
                                            'wuid': subscriber.get_property('wuid'),
                                            'is_phase2': subscriber.get_property('is_phase2')})
                        else:
                            self.add_event(10, "U_REG_RSP", 15,
                                           {'target_rfss_id': subscriber.get_property('current_rfss_id'),
                                            'target_site_id': subscriber.get_property('current_site_id'),
                                            'wuid': subscriber.get_property('wuid'),
                                            'reason': 'REG_FAIL'})

    def _sub_trigger_site_hunt(self, priority, metadata):
        wacn_id = metadata.get("wacn_id")
        rfss_id = metadata.get("rfss_id")
        subscriber_id = metadata.get("subscriber_id")

        with self.wacn._lock:
            rfss = self.rfss.get(rfss_id)
            if rfss:
                subscriber = rfss.get_subscriber(subscriber_id)
                if subscriber:
                    print(f"Subscriber {subscriber_id}: initiating new site hunt.")
                    # Trigger the subscriber to start the registration process again
                    selected_site = subscriber.control_channel_hunt()
                    if selected_site:
                        self.add_event(10, "U_REG_REQ", 1, {'subscriber_id': subscriber_id})
                    else:
                        # SIMULATE OUT OF RANGE AGAIN
                        self.add_event(10, "U_REG_RSP", 15, {'subscriber_id': subscriber_id, 'reason': 'REG_FAIL'})

    def _sub_trigger_group_affiliation(self, priority, metadata):
        wuid = metadata.get("wuid")

        parts = wuid.split('-')
        if len(parts) == 3:
            rfss_id = int(parts[1])
            subscriber_id = int(parts[2])

            with self.lock:
                with self.wacn._lock:
                        rfss = self.rfss.get(rfss_id)
                        if rfss:
                            subscriber = rfss.get_subscriber(subscriber_id)
                            if subscriber:
                                self.add_event(5, "GRP_AFF_REQ", 2,
                                               {'wuid': wuid, 'talkgroup': subscriber.get_property('active_talkgroup'),
                                                'site_id': subscriber.get_property('current_site_id')})



    def _sub_turn_off(self, priority, metadata):
        subscriber_id = metadata.get("subscriber_id")

    def _handle_sts_q(self, priority, metadata):
        print(f"metadata _handle_u_reg_rsp {metadata}")

    def _handle_u_reg_rsp(self, priority, metadata):
        wuid = metadata.get('wuid')

        with self.lock:

            if metadata.get('reason') == 'REG_FAIL':
                self.add_event(0, "SUBSCRIBER_TRIGGER_SITE_HUNT", 15, {'wuid': wuid})
                message = f"Registration request failure for ({wuid}): out of range, could not find a site."
            elif metadata.get('reason') == 'REG_DENY':
                self.add_event(0, "SUBSCRIBER_TRIGGER_SITE_HUNT", 15, {'wuid': wuid})
                message = f"Registration request failure for ({wuid}): registration is not allowed at the site."
            elif metadata.get('reason') == 'REG_REFUSED':
                message = f"Registration request failure for ({wuid}): SUID is invalid but the SU need not enter trunking hunt."
            elif metadata.get('reason') == 'REG_ACCEPT':
                self.add_event(0, "SUBSCRIBER_TRIGGER_GROUP_AFFILIATION", 0, {'wuid': wuid})
                message = f"Registration request success for ({metadata.get('wuid')} on RFSS {self.su_locale[wuid]}): registration is accepted."
            print(message)

    def _handle_u_reg_req(self, priority, metadata):
        target_rfss_id = metadata.get('target_rfss_id')
        target_site_id = metadata.get('target_site_id')
        wuid = metadata.get('wuid')
        is_phase2 = metadata.get('is_phase2')

        print(f"metadata _handle_u_reg_req {metadata}")
        with self.lock:
            with self.wacn._lock:

                if target_rfss_id is None or target_site_id is None or wuid is None:
                    self.add_event(10, "U_REG_RSP", 1, {'wuid': wuid, 'reason': 'REG_FAIL'})
                    return

                target_rfss = self.rfss.get(target_rfss_id)
                subscriber = self._get_subscriber_object_by_wuid(wuid)
                home_rfss_id = subscriber.get_property('home_rfss_id')

                # --- Validate and Register with the RFSS ---
                # This method should handle RFSS-local validation and update rfss.registers
                # It needs its own internal locking (e.g., with target_rfss._lock)
                # Returns (success_bool, reason_string, registration_details_dict)
                is_valid, reason, reg_details = target_rfss.process_registration_attempt(
                    wuid, target_site_id, is_phase2, home_rfss_id
                )

                if is_valid:
                    # --- Update SimulatorInstance State ---
                    self.su_locale[wuid] = target_rfss_id  # Update quick lookup

                    # --- Update Central Registration Table ---
                    now = datetime.now()  # Use current time as fallback
                    reg_time = reg_details.get('registration_time', now)  # Get time from RFSS if possible
                    is_foreign = (int(target_rfss_id) != int(home_rfss_id))

                    self.global_registrations[wuid] = {
                        'HomeRFSS': home_rfss_id,
                        'CurrentRFSS': target_rfss_id,
                        'CurrentSiteID': target_site_id,
                        'Registered': True,
                        'RegistrationTimestamp': reg_time,
                        'LastPollTimestamp': reg_time,  # Initially same as registration
                        'IsPhase2': is_phase2,
                        'IsForeign': is_foreign
                    }
                    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    print(
                        f"[{timestamp_str}] CentralRegTable: Updated for {wuid}, Registered on RFSS {target_rfss_id}, Site {target_site_id}")
                    # print(f"DEBUG: Current table entry for {wuid}: {self.global_registrations[wuid]}")
                """
                rfss = self.rfss.get(rfss_id)
                if rfss:
                    if rfss.register_subscriber(wuid, site_id, is_phase2):
                        self.su_locale[wuid] = rfss_id
                        # TODO this is to query the "keep alive"
                        self.add_event(0, "STS_Q", 3660, {'wuid': wuid})
                        self.add_event(10, "U_REG_RSP", 1,
                                       {'wuid': wuid, 'reason': 'REG_ACCEPT'})
                    else:
                        self.add_event(10, "U_REG_RSP", 1,
                                       {'wuid': wuid, 'reason': 'REG_DENY'})
                        """

    def _handle_u_de_reg_req(self, priority, metadata):
        # De-Registration Request
        subscriber_id = metadata.get('subscriber_id')

    def _handle_grp_aff_req(self, priority, metadata):
        wuid = metadata.get("wuid")
        talkgroup = metadata.get("talkgroup")

        if metadata.get("talkgroup"):
            wuid_parts = wuid.split('-')
            tg_parts = talkgroup.split('-')
            print(f"wuid_parts {wuid_parts}")
            print(f"tg_parts {tg_parts}")
            if (len(wuid_parts) == 3) and (len(tg_parts) == 3):
                home_rfss_id = int(wuid_parts[1])
                home_subscriber_id = int(wuid_parts[2])
                target_site_id = int(tg_parts[1])
                target_tg_id = int(tg_parts[2])

                with self.lock:
                    with self.wacn._lock:
                        target_rfss_id = self.su_locale[wuid]
                        print(f"target_rfss_id {target_rfss_id}")
                        rfss = self.rfss.get(target_rfss_id)
                        if rfss:

                            is_valid, reason = rfss.validate_affiliation(wuid, target_tg_id)

                            if is_valid:
                                site_id = rfss.registers.get(wuid, {}).get('site_id')
                                print(f"site_id {site_id}")

                            #TODO we need to check for phase 2 is supported, if so update modulation, we also need to see if subscriber is rejected because roaming, we also need to check if vtalkgroup is valid
                            if rfss.add_affiliation(metadata.get("talkgroup_id"), wuid, metadata.get("site_id")):
                                self.add_event(10, "GRP_AFF_RSP", 1,
                                           {'wuid': wuid, 'reason': 'AFF_ACCEPT'})
                            else:
                                self.add_event(10, "GRP_AFF_RSP", 1,
                                               {'wuid': wuid, 'reason': 'AFF_DENY'})
            else:
                self.add_event(10, "GRP_AFF_RSP", 1,
                               {'wuid': wuid, 'reason': 'AFF_REFUSED'})

    # ------- EVENT HANDLERS STOP


class MainProgram:
    def __init__(self):
        self.simulators = {}

    def create_system_instance(self, config_file):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_file}' not found.")
            return None
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in '{config_file}'.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

        wacn_list = config_data.get("wacn")
        # TODO support multiple WACNs for roaming, but for now we use just one WACN
        wacn_data = wacn_list[0]
        wacn_id = wacn_data.get("id")

        if wacn_id is None:
            print("Error: wacn_id not found in config file.")
            return None

        simulator = SimulatorInstance(wacn_id)
        simulator.init_load_config(wacn_data, wacn_id)
        # simulator.add_event(2, "Event 2", 1.25)
        simulator.init_start()

        self.simulators[wacn_id] = simulator

        return wacn_id

    def stop_system_instances(self):
        print("Stopping all system instances...")
        for instance in self.simulators.values():
            instance.init_stop()
        print("All system instances stopped.")
