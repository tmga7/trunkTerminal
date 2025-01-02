import random
from site_constants import *
import secrets

class Call:

    def __init__(self, sequence, call_type=None, initiating_radio=None, target_talkgroup=None, target_radio=None, channel=None, tdma_slot=None,
                 call_duration=None):
        self.id = sequence
        self.call_type = call_type
        self.initiating_radio = initiating_radio
        self.target_talkgroup = target_talkgroup  # List of talkgroups
        self.target_radio = target_radio  # List of radios
        self.channel = channel
        self.tdma_slot = tdma_slot
        self.call_duration = call_duration
        self.call_id = random.randint(1000, 9999)
        self.end_reason = END_REASON_NORMAL
        self.is_in_hangtime = False

        print("we made a call")

    def end_call(self):
        print("hi")
        # we want to log call
        # if there is a hangtime, change call status and prolong
        # if its in hangtime, then collapse call
        # if it preempted, state that it was - update end reason
        # we wannt to notify site queue of the change
