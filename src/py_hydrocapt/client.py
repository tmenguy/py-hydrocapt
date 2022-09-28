# -*- coding: utf-8 -*-
"""Client for the Diffazur Hydrocapt API."""
import copy
import time
from typing import Any
from typing import Dict
from typing import Optional


from lxml import etree
from dateutil.parser import parse


from datetime import datetime
from datetime import timedelta

#if issues with .maymodule relative imports
if __package__ is None or len(__package__) <= 1:
    import sys
    from pathlib import Path
    DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(DIR.parent))
    __package__ = DIR.name


from .session import HydrocaptClientSession
from .exceptions import HydrocaptError

from .const import HYDROCAPT_AJAX_VALUES_HISTORY
from .const import HYDROCAPT_GET_POOL_COMMAND_URL

from .const import HYDROCAPT_EXTERNAL_TO_INTERNAL_COMMANDS
from .const import HYDROCAPT_INTERNAL_TO_EXTERNAL_COMMANDS


from .const import HYDROCAPT_SAVE_POOL_COMMAND_URL
from .const import HYDROCAPT_POOL_LIST_OWN_URL
from .const import HYDROCAPT_AJAX_POOL_HISTORIC
from .const import HYDROCAPT_GET_ALARMS_URL



class HydrocaptClient(object):
    """Proxy to the Hydrocapt REST API."""

    def __init__(self, username: str, password: str, pool_internal_id: Optional[int] = -1) -> None:
        """Initialize the API and authenticate so we can make requests.

        Args:
            username: string containing your Hydrocapt's app username
            password: string containing your Hydrocapt's app password
        """
        self.username = username
        self.password = password
        self.session: Optional[HydrocaptClientSession] = None
        self.pool_internal_id = pool_internal_id
        self._saved_states = {}
        self._saved_read_values = {}

    def _get_session(self, force_reconnect=False) -> HydrocaptClientSession:
        if self.session is None or force_reconnect is True:
            self.session = HydrocaptClientSession(self.username, self.password, self.pool_internal_id)

        return self.session

    def _get_pool_internal_id(self):
        if self.pool_internal_id < 0:
            session = self._get_session()
            self.pool_internal_id = session.get_internal_pool_id()
        return self.pool_internal_id

    def is_connection_ok(self):
        pool_id = self._get_pool_internal_id()
        return  pool_id >= 0

    def _get_pool_measure_latest(self) -> Dict[str, Any]:
        """Retrieve most recents measures.


        Raises:
            HydrocaptError: when hydrocapt API returns an incorrect response

        Returns:
            A dict whose keys are :
                water_temperature: A float representing the temperature of the pool.
                technical_room_temperature: A float representing the temperature of the pool technical room.
                ph: A float representing the ph of the pool.
                conductivity: A float representing the conductivity of the pool.
                red_ox: A float representing the oxydo reduction level of the pool.
                date_time: The date time when the measure was taken.
                ph_status : Alert status for PH value in : TooLow, OK, TooHigh
                conductivity_status : Alert status for conductivity value in : TooLow, OK, TooHigh
                red_ox_status : Alert status for red_ox in : TooLow, OK, TooHigh
        """
        pool_id = self._get_pool_internal_id()
        if pool_id < 0:
            raise HydrocaptError("can't get pool id in measure")

        today = datetime.today().strftime('%Y-%m-%d')
        get_pool_data_url = f"{HYDROCAPT_AJAX_VALUES_HISTORY}?serial={pool_id}&date={today}&type_date=day"

        pool_data = self._get_session().get(get_pool_data_url)
        a = pool_data.json()
        records = a.get("records", [])


        if a.get("error") is not None or a.get("errors") is not None or len(records) == 0:
            pool_data = self._get_session(force_reconnect=True).get(get_pool_data_url)
            a = pool_data.json()

        #a = json.loads(pool_data.content)
        records = a.get("records", [])


        if len(records) == 0:
            raise HydrocaptError("No data records from pool")

        vals = {"WATER_TEMP":"water_temperature", "AIR_TEMP":"technical_room_temperature", "PH":"ph", "CONDUCTIVITY":"conductivity", "ORP":"red_ox"} #redox is ORP

        bad_vals = {"--.-", "--", "-.-", "---" }

        cur_data = {}

        num_hours = 0 #in the records tab : the list of measure fpr pH, watertemps, etc are per hour ... so th elast one from midnoight to it is the time the measure has been performed

        dates = [today]*25

        for r in records:

            cur_c = r.get("typeInfo", "NOT A VALUE")
            if cur_c in vals:
                r_vals = r.get("values", ["--"]*25)
                do_count_hours = False
                if cur_c == "PH":
                    do_count_hours = True

                cd = -1
                for i in range(len(r_vals)-1, -1 , -1):
                    if r_vals[i] in bad_vals:
                        continue

                    if do_count_hours:
                        num_hours = i

                    cd = r_vals[i]
                    break

                cur_data[vals[cur_c]] = float(cd)
            elif cur_c == "DATE":
                dates = r.get("values", [today]*25)


        #ok num_hours is the index of the measure in the hour based values array
        measure_date = dates[num_hours]
        measure_date = parse(measure_date) + timedelta(hours=num_hours)
        cur_data["date_time"] = measure_date




        #now time to get the limits!

        get_alarms_data = {"serial":pool_id}

        result_get_alarms = self._get_session().post(
            HYDROCAPT_GET_ALARMS_URL,
            data=get_alarms_data,
            headers=dict(referer=f"{HYDROCAPT_AJAX_POOL_HISTORIC}?serial={pool_id}")
        )

        result_get_alarms.raise_for_status()

        tree_alarms = etree.fromstring(result_get_alarms.text)
        r = tree_alarms.xpath("/root/status")
        if r is not None:
            if "You are not authenticated" in r[0].text:
                raise HydrocaptError
            if "OK" in r[0].text:
                pass
            else:
                raise HydrocaptError


        alarms = {}
        for alrm in tree_alarms.iter(tag="alarm"):
            alarm = {}
            do_stop = False
            for c in alrm:
                if c.tag == "max" or c.tag == "min":
                    try:
                        alarm[c.tag] = float(c.text)
                    except:
                        do_stop = True
                        break
                elif c.tag == "enable":
                    try:
                        alarm[c.tag] = bool(c.text)
                    except:
                        do_stop = True
                        break


            if do_stop is False:
                name = alrm.attrib.get("name")
                if name is not None:
                    alarms[name] = alarm


        #now check the alarms:

        for val_name, alrm_name in [("conductivity", "CONDUCTIVITY" ), ("red_ox", "ORP" ), ("ph", "PH" )]:

            alarm = alarms.get(alrm_name)
            cur_data[f"{val_name}_status"] = "OK"
            if alarm is not None:
                c = cur_data.get(val_name, 0.0)
                if c < alarm.get("min", c):
                    cur_data[f"{val_name}_status"] = "TooLow"
                elif c > alarm.get("max", c):
                    cur_data[f"{val_name}_status"] = "TooHigh"

        return cur_data


    def get_pool_measure_latest(self) -> Dict[str, Any]:

        try:
            read_data = self._get_pool_measure_latest()
        except:
            read_data = {}

        if read_data is None or len(read_data) == 0:
            self._get_session(force_reconnect=True)
            read_data = self._get_pool_measure_latest()

        if read_data is None or len(read_data) == 0:
            raise HydrocaptError("Cannot get pool measures")

        self._saved_read_values = read_data

        return read_data




    def _get_hydrocapt_internal_command_states_from_external(self, external_commands):

        internal_commands = {}

        for k_ext, v_ext in external_commands.items():
            k_int_trad = HYDROCAPT_EXTERNAL_TO_INTERNAL_COMMANDS.get(k_ext)
            if k_int_trad is not None:
                val_int = k_int_trad[1].get(v_ext, k_int_trad[1][k_int_trad[2]])
                internal_commands[k_int_trad[0]] = val_int


        return internal_commands

    def _get_hydrocapt_external_command_states_from_internal(self, internal_commands):

        external_commands = {}

        for k_int, v_int in internal_commands.items():
            k_ext_trad = HYDROCAPT_INTERNAL_TO_EXTERNAL_COMMANDS.get(k_int)
            if k_ext_trad is not None:
                val_ext = k_ext_trad[1].get(v_int, k_ext_trad[1][k_ext_trad[2]])
                external_commands[k_ext_trad[0]] = val_ext

        return external_commands



    def _get_commands_current_states(self) -> Dict[str, Any]:

        pool_id = self._get_pool_internal_id()

        get_pool_command_url = f"{HYDROCAPT_GET_POOL_COMMAND_URL}?serial={pool_id}"

        commands_state = self._get_session().get(get_pool_command_url)

        #check for "You are not authenticated" error

        tree_cmd_state = etree.fromstring(commands_state.text)

        internal_states = {}

        for state in HYDROCAPT_INTERNAL_TO_EXTERNAL_COMMANDS:
            try:
                r = tree_cmd_state.xpath(f"/root/datas/{state}")
                state_val = int(r[0].text)
                internal_states[state] = state_val
            except:
                pass

        return self._get_hydrocapt_external_command_states_from_internal(internal_states)

    def get_commands_current_states(self) -> Dict[str, Any]:

        try:
            states = self._get_commands_current_states()
        except:
            states = {}

        if len(states) == 0:
            self._get_session(force_reconnect=True)
            states = self._get_commands_current_states()

        if len(states) == 0:
            raise HydrocaptError("Cannot get commands state")

        self._saved_states = states

        return states



    def _set_all_command_states(self, commands):

        external_commands = copy.deepcopy(commands)

        pool_id = self._get_pool_internal_id()
        if pool_id is None or pool_id < 0:
            raise HydrocaptError("Can't get pool id")



        #first check commands are "complete"
        complete_command_set = True
        for k_ext in HYDROCAPT_EXTERNAL_TO_INTERNAL_COMMANDS:
            if k_ext in external_commands:
                continue
            else:
                complete_command_set = False
                break

        if complete_command_set is False:
            curr_command = self.get_commands_current_states()

            for k_curr, val_curr in curr_command.items():
                if k_curr in external_commands:
                    continue
                else:
                    external_commands[k_curr] = val_curr


        save_internal_commands = self._get_hydrocapt_internal_command_states_from_external(external_commands)


        save_internal_commands["serial"] = pool_id
        save_internal_commands["type_aux1"] = 0


        result_save = self._get_session().post(
            HYDROCAPT_SAVE_POOL_COMMAND_URL,
            data=save_internal_commands,
            headers=dict(referer=HYDROCAPT_POOL_LIST_OWN_URL)
        )

        result_save.raise_for_status()

        tree_save_state = etree.fromstring(result_save.text)
        r = tree_save_state.xpath(f"/root/status")
        if r is not None:
            if "Pas de modification" in r[0].text:
                #ok no modification
                return external_commands
            elif "You are not authenticated" in r[0].text:
                raise HydrocaptError


        # wait for change to happen
        found = False
        for i in range(5):
            cur_states = self.get_commands_current_states()
            if cur_states == external_commands:
                found = True
                break
            time.sleep(2)


        if found is False:
            return {}

        return external_commands


    def set_all_command_states(self, commands):

        try:
            saved_states = self._set_all_command_states(commands)
        except:
            saved_states = {}

        if len(saved_states) == 0:
            self._get_session(force_reconnect=True)
            saved_states = self._set_all_command_states(commands)

        if len(saved_states) == 0:
            raise HydrocaptError("Cannot save command state")

        self._saved_states = saved_states

        return saved_states


    def set_command_state(self, command, state):

        curr_states = self.get_commands_current_states()
        curr_states[command] = state
        return self.set_all_command_states(curr_states)




    def get_packaged_data(self):

        res = {}

        for k,v in self._saved_states.items():
            res[k] = v

        for k,v in self._saved_read_values.items():
            res[k] = v

        return res


    def fetch_all_data(self):
        self.get_commands_current_states()
        self.get_pool_measure_latest()
        return self.get_packaged_data()


