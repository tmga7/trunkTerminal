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
        self.consoles = {}
        self.subscribers = {}
        self.talkgroups = {}
        self.groups = {}
        self.registers = {}  # Registry for subscriber site affiliations
        self.affiliations = {}  # Registry for talkgroup affiliations
        self.operating_area = None

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


class SimulatorInstance:
    def __init__(self, wacn_id):
        self.id = str(uuid.uuid4())  # Needs to be unique to all users
        self.wacn = WACN(wacn_id)
        self.event_queue = queue.PriorityQueue()
        self.busy_queue = queue.PriorityQueue()
        self.lock = threading.RLock()
        self.stop_flag = threading.Event()
        self.operating_area = []
        self.rfss = {}
        self.event_handlers = {
            "SUBSCRIBER_TURN_ON": self._handle_subscriber_turn_on,
            "SUBSCRIBER_TURN_OFF": self._handle_subscriber_turn_off,
            "U_REG_REQ": self._handle_u_reg_req,  # Unit Registration Request
            "U_REG_RSP": self._handle_u_reg_rsp,  #Unit Registration Response
            "U DE_REG_REQ": self._handle_u_de_reg_req,  # De-Registration Request

        }

    def init_load_config(self, config_data):
        wacn_data = config_data.get("wacn", {})

        with self.wacn._lock:
            for console_data in wacn_data.get("consoles", []):
                console_id = console_data.get("id")
                if console_id:
                    console = Console(console_id, console_data)  # Pass properties
                    self.wacn.add_console(console)

            for subscriber_data in wacn_data.get("subscribers", []):
                subscriber_id = subscriber_data.get("id")
                if subscriber_id:
                    subscriber = Subscriber(subscriber_id, subscriber_data)
                    if self.wacn.add_subscriber(subscriber):
                        with self.lock:
                            self.add_event(0, "SUBSCRIBER_TURN_ON", 2, {'subscriber_id': subscriber_id})
                            pass
                    else:
                        print(f"Subscriber with id {subscriber_id} already exists.")

            for talkgroup_data in wacn_data.get("talkgroups", []):
                talkgroup_id = talkgroup_data.get("id")
                if talkgroup_id:
                    talkgroup = Talkgroup(talkgroup_id, talkgroup_data)  # Pass properties
                    self.wacn.add_talkgroup(talkgroup)

            for group_data in wacn_data.get("groups", []):
                group_id = group_data.get("id")
                if group_id:
                    group = Group(group_id, group_data)
                    self.wacn.add_group(group)

            for talkgroup_data in wacn_data.get("talkgroups", []):
                talkgroup_id = talkgroup_data.get("id")
                if talkgroup_id:
                    talkgroup = Talkgroup(talkgroup_id, talkgroup_data)  # Pass properties
                    self.wacn.add_talkgroup(talkgroup)

        with self.lock:

            for rfss_data in config_data.get("rfsss", []):
                rfss_id = rfss_data.get("id")
                if rfss_id:
                    rfss = RFSS(rfss_id)
                    self.rfss[rfss_id] = rfss
                    for site_data in rfss_data.get("sites", []):
                        site_id = site_data.get("id")
                        if site_id:
                            site = Site(site_id, site_data)  # Pass properties
                            if rfss.add_site(site):
                                for channel_data in site_data.get("channels", []):
                                    channel_id = channel_data.get("id")
                                    if channel_id:
                                        channel = Channel(channel_id, channel_data)  # Pass properties
                                        site.add_channel(channel)
                                for subsite_data in site_data.get("subsites", []):
                                    subsite_id = subsite_data.get("id")
                                    if subsite_id:
                                        subsite = Subsite(subsite_id, subsite_data)  # Pass properties
                                        site.add_subsite(subsite)

            # We need to do some basic geofencing
            # TODO upgrade to geofencing for subscribers, so they can move within selected geogrpahic areas (i.e. police district)
            if config_data.get("operating_area"):
                top_left = config_data.get("operating_area").get("top_left")
                bottom_right = config_data.get("operating_area").get("bottom_right")
                min_lat = bottom_right['latitude']
                max_lat = top_left['latitude']
                min_lon = top_left['longitude']
                max_lon = bottom_right['longitude']
                self.operating_area = [top_left,
                                       {'latitude': bottom_right['latitude'], 'longitude': top_left['longitude']},
                                       bottom_right,
                                       {'latitude': top_left['latitude'], 'longitude': bottom_right['longitude']}]

                # Put all subs in random geofence
                with self.wacn._lock:  # Lock WACN for subscriber updates
                    for subscriber in self.wacn.subscribers.values():
                        lat = random.uniform(min_lat, max_lat)
                        lon = random.uniform(min_lon, max_lon)
                        subscriber.set_property("location", {'latitude': lat, 'longitude': lon})
                        # subscriber._state["location"] = {"latitude": lat, "longitude": lon}

        print("Configuration Loaded")

    def set_property(self, key, value):
        with self._lock:
            self._state[key] = value

    def get_property(self, key):
        with self._lock:
            return self._state.get(key)

    def init_start(self):
        self.thread = threading.Thread(target=self.queue_monitor)
        self.thread.start()

    def init_stop(self):
        self.stop_flag.set()
        self.thread.join()

    def tool_subscriber_update_site_table(self, subscriber_id):

        with self.lock:
            sub_table = []
            with self.wacn._lock:
                if subscriber_id in self.wacn.subscribers:
                    sub_location = self.wacn.subscribers[subscriber_id].get_property("location")
                    all_sites = self.tool_list_all_subsites()

                    for site_info in all_sites:
                        distance = GeospatialUtils.distance_between_points(
                            sub_location['latitude'], sub_location['longitude'], site_info.get('latitude'),
                            site_info.get('longitude'))

                        signal_strength_dbm, rssi_level = GeospatialUtils.estimate_rssi(distance, site_info.get(
                            'operating_radius'))

                        sub_table.append({
                            "site_id": site_info.get('site_id'),
                            "subsite_id": site_info.get('subsite_id'),
                            "signal_strength_dbm": signal_strength_dbm,
                            "rssi_level": rssi_level,
                            "REG_DENY": False,
                            "REG_REFUSED": False
                        })

                    sorted_subsites = sorted(sub_table, key=lambda x: x["signal_strength_dbm"], reverse=True)
                    self.wacn.subscribers[subscriber_id].set_property("site_table", sorted_subsites)

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
        all_subsites = []  # List to store subsite information
        with self.lock:  # lock simulator to access rfss and publish event.
            for rfss in self.rfss.values():
                for site in rfss.sites.values():
                    for subsite in site.subsites.values():
                        if not subsite.get_property(
                                "disabled"):  #TODO we need change this to reflect a site status when it goes offline
                            all_subsites.append({
                                "site_id": site.id,
                                "subsite_id": subsite.id,
                                "latitude": subsite.get_property("latitude"),
                                "longitude": subsite.get_property("longitude"),
                                "operating_radius": subsite.get_property("operating_radius")
                            })
        return all_subsites

    def add_event(self, priority, event, event_time_seconds=0, metadata=None):
        # Calculate the event time
        print("we are in add event")

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
            f"[{timestamp}] System Added event: {event} with priority {priority}, scheduled for {datetime.fromtimestamp(precise_event_time).strftime('%Y-%m-%d %H:%M:%S.%f')}")

    def queue_monitor(self):
        while not self.stop_flag.is_set():
            try:
                current_time = time.time()

                # Print the contents of the event queue for debugging
                print(f"System Event Queue State: {list(self.event_queue.queue)}")

                # Process Event Queue
                while not self.event_queue.empty():
                    priority, event_time, event, metadata = self.event_queue.get()
                    if current_time >= event_time:
                        self.process_event(priority, event, metadata)
                    else:
                        self.event_queue.put((priority, event_time, event, metadata))
                        break

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

    def _handle_subscriber_turn_on(self, priority, metadata):
        subscriber_id = metadata.get("subscriber_id")

        with self.lock:
            self.tool_subscriber_update_site_table(subscriber_id)
            with self.wacn._lock:
                selected_site = self.wacn.subscribers[subscriber_id].control_channel_hunt()
                if selected_site:
                    site_id, subsite_id = selected_site
                    self.add_event(10, "U_REG_REQ", 1,
                                   {'subscriber_id': subscriber_id, 'site_id': site_id, 'subsite_id': subsite_id})
                else:
                    self.add_event(10, "U_REG_RSP", 1, {'subscriber_id': subscriber_id, 'reason': 'REG_FAIL'})

    def _handle_subscriber_turn_off(self, priority, metadata):
        subscriber_id = metadata.get("subscriber_id")

    def _handle_u_reg_rsp(self, priority, metadata):

        with self.lock:
            if metadata.get('reason') == 'REG_FAIL':
                message = f"Registration request failure for ({metadata.get('subscriber_id')}): out of range, could not find a site."
            elif metadata.get('reason') == 'REG_DENY':
                message = f"Registration request failure for ({metadata.get('subscriber_id')}): registration is not allowed at the site."
                #TODO we need to update subscriber here, and initiate another hunt
            elif metadata.get('reason') == 'REG_REFUSED':
                message = f"Registration request failure for ({metadata.get('subscriber_id')}): SUID is invalid but the SU need not enter trunking hunt."
            elif metadata.get('reason') == 'REG_ACCEPT':
                message = f"Registration request success for ({metadata.get('subscriber_id')}): registration is accepted."

        print(message)

    def _handle_u_reg_req(self, priority, metadata):
        subscriber_id = metadata.get('subscriber_id')

        # TODO we need to check list if radio is part of a group prohibited from registering on site
        # REG_DENY

        with self.lock:
            group_id = None
            # self.tool_subscriber_group_property(subscriber_id, "id")
            group_priority = None
            # self.tool_subscriber_group_property(subscriber_id, "priority")

            with self.wacn._lock:
                self.wacn.registers[subscriber_id] = {
                    "site_id": metadata.get('site_id'),
                    "subsite_id": metadata.get('subsite_id'),
                    "group_id": group_id,
                    "registration_time": datetime.now(),
                    "is_phase2": self.wacn.subscribers[subscriber_id].get_property("is_phase2"),
                    "last_status_poll": datetime.now(),
                    "priority": group_priority,
                }

                self.add_event(10, "U_REG_RSP", 1,
                               {'subscriber_id': subscriber_id, 'reason': 'REG_ACCEPT'})

    def _handle_u_de_reg_req(self, priority, metadata):
        # De-Registration Request
        subscriber_id = metadata.get('subscriber_id')

    # ------- EVENT HANDLERS STOP


class MainProgram:
    def __init__(self):
        self.simulators = {}

    def create_system_instance(self, config_file):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)  # Load JSON
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_file}' not found.")
            return None
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in '{config_file}'.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

        wacn_id = config_data.get("wacn", {}).get("id")
        if wacn_id is None:
            print("Error: wacn_id not found in config file.")
            return None

        simulator = SimulatorInstance(wacn_id)
        simulator.init_load_config(config_data)
        simulator.add_event(2, "Event 2", 1.25)
        simulator.init_start()

        self.simulators[wacn_id] = simulator

        return wacn_id

    """
    def create_system_instance(self, id):
        instance = SimulatorInstance(id)
        self.system_instances.append(instance)
        instance.start()
    """

    def stop_system_instances(self):
        for instance in self.simulators:
            instance.init_stop()

# Example usage
