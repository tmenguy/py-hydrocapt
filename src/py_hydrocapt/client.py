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

from .const import HYDROCAPT_EXTERNAL_COMMANDS

from .const import HYDROCAPT_SAVE_POOL_COMMAND_URL
from .const import HYDROCAPT_POOL_LIST_OWN_URL
from .const import HYDROCAPT_AJAX_POOL_HISTORIC
from .const import HYDROCAPT_GET_ALARMS_URL

from .const import HYDROCAPT_GET_POOL_CONSIGN_URL
from .const import HYDROCAPT_SAVE_POOL_CONSIGN_URL

from .const import HYDROCAPT_EXTERNAL_TO_INTERNAL_CONSIGNS, HYDROCAPT_INTERNAL_TO_EXTERNAL_CONSIGNS, HYDROCAPT_TIMER, HYDROCAPT_TIMERS
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
        self._saved_consigns = {}
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

    def _check_xml_not_authenticated(self, rTree):
        r = rTree.xpath("/root/status")
        if r is not None and len(r) > 0:
            if "You are not authenticated" in r[0].text:
                raise HydrocaptError
            if "OK" in r[0].text:
                pass
            else:
                raise HydrocaptError

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
                redox: A float representing the oxydo reduction level of the pool.
                date_time: The date time when the measure was taken.
                ph_status : Alert status for PH value in : TooLow, OK, TooHigh
                conductivity_status : Alert status for conductivity value in : TooLow, OK, TooHigh
                redox_status : Alert status for redox in : TooLow, OK, TooHigh
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

        vals = {"WATER_TEMP":"water_temperature", "AIR_TEMP":"technical_room_temperature", "PH":"ph", "CONDUCTIVITY":"conductivity", "ORP":"redox"} #redox is ORP

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

        self._check_xml_not_authenticated(tree_alarms)


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

        for val_name, alrm_name in [("conductivity", "CONDUCTIVITY" ), ("redox", "ORP" ), ("ph", "PH" )]:

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

        tree_cmd_state = etree.fromstring(commands_state.text)

        self._check_xml_not_authenticated(tree_cmd_state)

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


    def _set_command_state(self, command, state):

        pool_id = self._get_pool_internal_id()
        if pool_id is None or pool_id < 0:
            raise HydrocaptError("Can't get pool id")

        external_commands = {command:state}
        save_internal_commands = self._get_hydrocapt_internal_command_states_from_external(external_commands)
        save_internal_commands["serial"] = pool_id
        #save_internal_commands["type_aux1"] = 0

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
                return None
            elif "You are not authenticated" in r[0].text:
                raise HydrocaptError


        # wait for change to happen
        saved_states = {}
        for i in range(5):
            cur_states = self.get_commands_current_states()
            if cur_states.get(command) == state:
                return cur_states
            time.sleep(2)

        raise HydrocaptError


    def set_command_state(self, command, state, get_prev=False):

        prev_state = None

        if get_prev is True:
            curr_states = self.get_commands_current_states()
            prev_state = curr_states.get(command)

        try:
            saved_states = self._set_command_state(command, state)
            if saved_states is None:
                #No change
                return prev_state
        except:
            saved_states = {}

        if len(saved_states) == 0:
            self._get_session(force_reconnect=True)
            saved_states = self._set_command_state(command, state)
            if saved_states is None:
                #No change
                return prev_state

        if len(saved_states) == 0:
            raise HydrocaptError("Cannot save command state")

        self._saved_states = saved_states

        return prev_state



    def get_commands_and_options(self):
        return HYDROCAPT_EXTERNAL_COMMANDS


    def get_timers(self):
        return HYDROCAPT_TIMERS
    def _get_hydrocapt_internal_consigns_from_external(self, external_consigns):

        internal_consigns = {}

        for k_ext, v_ext in external_consigns.items():
            k_int_trad = HYDROCAPT_EXTERNAL_TO_INTERNAL_CONSIGNS.get(k_ext)
            if k_int_trad is not None:

                if k_int_trad[1] == HYDROCAPT_TIMER:

                    if v_ext is None or len(v_ext) != 24:
                        continue

                    val_int = ""
                    for v in v_ext:
                        if v:
                            val_int += "1"
                        else:
                            val_int += "0"
                elif k_int_trad[1] == "integer":
                    val_int = int(v_ext)
                elif k_int_trad[1] == "float":
                    val_int = float(v_ext)
                else:
                    val_int = v_ext

                internal_consigns[k_int_trad[0]] = val_int

        return internal_consigns


    def _get_hydrocapt_external_consign_from_internal(self, internal_consigns):

        external_consigns = {}

        for k_int, v_int in internal_consigns.items():
            k_ext_trad = HYDROCAPT_INTERNAL_TO_EXTERNAL_CONSIGNS.get(k_int)
            if k_ext_trad is not None:
                if k_ext_trad[1] == HYDROCAPT_TIMER:

                    if v_int is None or len(v_int) != 24:
                        continue

                    val_ext = []
                    for v in v_int:
                        if v == "0":
                            val_ext.append(False)
                        else:
                            val_ext.append(True)
                elif k_ext_trad[1] == "integer":
                    val_ext = int(v_int)
                elif k_ext_trad[1] == "float":
                    val_ext = float(v_int)
                else:
                    val_ext = v_int

                external_consigns[k_ext_trad[0]] = val_ext

        return external_consigns



    def _set_consign(self, consign, value):

        pool_id = self._get_pool_internal_id()
        if pool_id is None or pool_id < 0:
            raise HydrocaptError("Can't get pool id")

        external_consigns = {consign:value}
        save_internal_consigns = self._get_hydrocapt_internal_consigns_from_external(external_consigns)
        save_internal_consigns["serial"] = pool_id
        #save_internal_commands["type_aux1"] = 0

        result_save = self._get_session().post(
            HYDROCAPT_SAVE_POOL_CONSIGN_URL,
            data=save_internal_consigns,
            headers=dict(referer=HYDROCAPT_POOL_LIST_OWN_URL)
        )

        result_save.raise_for_status()

        tree_save_state = etree.fromstring(result_save.text)
        r = tree_save_state.xpath(f"/root/status")
        if r is not None:
            if "Pas de modification" in r[0].text:
                #ok no modification
                return None
            elif "You are not authenticated" in r[0].text:
                raise HydrocaptError


        # wait for change to happen
        saved_states = {}
        for i in range(5):
            cur_consigns = self.get_current_consigns()
            if cur_consigns.get(consign) == value:
                return cur_consigns
            time.sleep(2)

        raise HydrocaptError


    def set_consign(self, consign, value, get_prev=False):

        prev_value = None

        if get_prev is True:
            cur_consigns = self.get_current_consigns()
            prev_value = cur_consigns.get(consign)

        try:
            saved_states = self._set_consign(consign, value)
            if saved_states is None:
                #No change
                return prev_value
        except:
            saved_states = {}

        if len(saved_states) == 0:
            self._get_session(force_reconnect=True)
            saved_states = self._set_consign(consign, value)
            if saved_states is None:
                #No change
                return prev_value


        if len(saved_states) == 0:
            raise HydrocaptError("Cannot save consign")

        self._saved_consigns = saved_states

        return prev_value

    def set_consign_timer_hour(self, consign, hour_idx, value):

        if HYDROCAPT_EXTERNAL_TO_INTERNAL_CONSIGNS.get(consign,[consign, "integer"])[1] != HYDROCAPT_TIMER:
            return

        if hour_idx < 0 or hour_idx >= 24:
            return

        cur_timer = self._saved_consigns.get(consign)

        if cur_timer is None:
            self.get_current_consigns()

        cur_timer = self._saved_consigns.get(consign)

        if cur_timer is None:
            return

        cur_timer[hour_idx] = value

        self.set_consign(consign, cur_timer)


    def _get_current_consigns(self) -> Dict[str, Any]:

        pool_id = self._get_pool_internal_id()

        get_pool_command_url = f"{HYDROCAPT_GET_POOL_CONSIGN_URL}?serial={pool_id}"

        commands_state = self._get_session().get(get_pool_command_url)


        tree_consign_state = etree.fromstring(commands_state.text)

        self._check_xml_not_authenticated(tree_consign_state)

        internal_consigns = {}



        for state in HYDROCAPT_INTERNAL_TO_EXTERNAL_CONSIGNS:
            for path in [f"/root/datas/select/{state}", f"/root/datas/timer/{state}"]:
                try:
                    r = tree_consign_state.xpath(path)
                    state_val = r[0].text
                    internal_consigns[state] = state_val
                except:
                    pass


        return self._get_hydrocapt_external_consign_from_internal(internal_consigns)

    def get_current_consigns(self) -> Dict[str, Any]:

        try:
            states = self._get_current_consigns()
        except:
            states = {}

        if len(states) == 0:
            self._get_session(force_reconnect=True)
            states = self._get_current_consigns()

        if len(states) == 0:
            raise HydrocaptError("Cannot get current consigns")

        self._saved_consigns = states

        return states


    def get_packaged_data(self):

        res = {}

        for k,v in self._saved_states.items():
            res[k] = v

        for k,v in self._saved_read_values.items():
            res[k] = v

        for k,v in self._saved_consigns.items():
            res[k] = v

        return res


    def fetch_all_data(self):
        self.get_commands_current_states()
        self.get_pool_measure_latest()
        self.get_current_consigns()
        return self.get_packaged_data()


