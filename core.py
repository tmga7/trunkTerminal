from subscriber import Subscriber
import rfss
import yaml


def load_config(filename="config.yaml"):
    with open(filename, 'r') as f:
        config = yaml.safe_load(f)
    return config


class Talkgroup:
    def __init__(self, id, alias, mode, ckr, wait, ptt_id, ptt_id_hangtime):
        self.id = id
        self.alias = alias
        self.mode = mode
        self.ckr = ckr
        self.wait = wait
        self.ptt_id = ptt_id
        self.ptt_id_hangtime = ptt_id_hangtime

    def __repr__(self):
        return f"Talkgroup(id={self.id}, alias='{self.alias}', mode='{self.mode}', ckr={self.ckr}, wait={self.wait}, ptt_id={self.ptt_id}, ptt_id_hangtime={self.ptt_id_hangtime})\r\n"


class System:
    def __init__(self, config):
        if config:  # Check if the config is not empty
            self.id = config['id']
            self.alias = config['alias']
            self.wacn = config['wacn']
            self.rfss = {}
            self.talkgroups = config.get('talkgroups', {})
            self.subscribers = config.get('subscribers', {})

            # Process RFSS data
            for rfss_id, rfss_data in config.get('rfss', {}).items():  # Directly iterate config
                self.rfss[rfss_id] = rfss.RFSS(rfss_id)
                for site_id, site_data in rfss_data.get('site', {}).items():
                    self.rfss[rfss_id].add_site(site_id, site_data)

            # Process talkgroups
            for tg_id, tg_data in self.talkgroups.items():
                self.talkgroups[tg_id] = Talkgroup(tg_id, tg_data['alias'], tg_data['mode'], tg_data['ckr'],
                                                   tg_data['wait'],
                                                   tg_data['ptt_id'], tg_data['ptt_id_hangtime'])

            # Process subscribers
            for sub_id, sub_data in self.subscribers.items():
                self.subscribers[sub_id] = Subscriber(sub_id, sub_data['alias'], sub_data['hardware'],
                                                      sub_data.get('phase2', False))

    def __repr__(self):
        rfss_str = ", ".join(repr(r) for r in self.rfss.values())
        talkgroups_str = ", ".join(repr(t) for t in self.talkgroups.values())
        subscribers_str = ", ".join(repr(s) for s in self.subscribers.values())
        return f"System(id={self.id}, alias='{self.alias}', wacn={self.wacn}, rfss=[{rfss_str}], talkgroups=[{talkgroups_str}], subscribers=[{subscribers_str}])"
