from site_constants import *

# from core import Core
from core import Core
from prototype_site import Site

zc = Core()

# Create Talkgroups
zc.create_talkgroup(101, MODE_PTT_ID)
zc.create_talkgroup(102, MODE_TRANSMISSION, True, False)
zc.create_talkgroup(103, MODE_TRANSMISSION)
zc.create_talkgroup(104, MODE_TRANSMISSION)
zc.create_talkgroup(105, MODE_TRANSMISSION)

zc.create_radio(1001, RADIO_TYPE_SUBSCRIBER, True)
zc.create_radio(1002, RADIO_TYPE_SUBSCRIBER, True)
zc.create_radio(1003, RADIO_TYPE_SUBSCRIBER, True)
zc.create_radio(1004, RADIO_TYPE_SUBSCRIBER, True)
zc.create_radio(700001, RADIO_TYPE_SUBSCRIBER, True)

zc.create_site(1)
zc.create_site(2)

zc.sites[1].create_channel(1, CHANNEL_CAP_FDMA | CHANNEL_CAP_CONTROL, 867.5625, 822.5625)
zc.sites[1].create_channel(2, CHANNEL_CAP_FDMA | CHANNEL_CAP_TDMA, 867.5625, 822.5625)
zc.sites[1].initialize_system()

zc.radios[1004].turn_on([101])
zc.radios[700001].turn_on([101, 103, 104])

zc.radios[1004].subscriber_group_ptt()

print(f"HI = ", zc.get_talkgroup_radio_ids([101, 103, 101]))

print(f"Site1 radios: {list(zc.sites[1].radios)}")
print(f"Site2 radios: {list(zc.sites[2].radios)}")
print(f"Talkgroup status: {list(zc.talkgroups[101].affiliations)}")
print(f"Talkgroup status: {list(zc.talkgroups[102].affiliations)}")
print(f"Talkgroup status: {list(zc.talkgroups[103].affiliations)}")
print(f"Talkgroup status: {list(zc.talkgroups[104].affiliations)}")
print(f"Talkgroup status: {list(zc.talkgroups[105].affiliations)}")
# print(f"Site2 radios: {list(zc.sites[2].radios)}")

# site.radios[103].turn_on()


# site.process_call(CALL_TYPE_VOICE, radio1)
# site.process_call(CALL_TYPE_VOICE, radio2)
# site.process_call(CALL_TYPE_VOICE, radio5)
# site.process_call(CALL_TYPE_VOICE, radio3)

# system.add_channel(Channel(3, CHANNEL_CAP_CONTROL | CHANNEL_CAP_TDMA | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))
# system.add_channel(Channel(4, CHANNEL_CAP_DATA | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))
# system.add_channel(Channel(5, CHANNEL_CAP_DATA | CHANNEL_CAP_BSI | CHANNEL_CAP_DATA | CHANNEL_CAP_FDMA, 867.5625, 822.5625))

# site.initialize_system()

# system.control_channel_manager.process_call_request(CALL_TYPE_OTAP, radio2, None, None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio1, [101], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio3, [102], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_VOICE, radio4, [103], None, 15000)
# system.control_channel_manager.process_call_request(CALL_TYPE_PATCHED, radioConsole, , None, 15000)
