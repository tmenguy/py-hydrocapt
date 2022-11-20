# -*- coding: utf-8 -*-
"""Consts for Hydrocapt python client API."""



HYDROCAPT_EXTERNAL_TO_INTERNAL_COMMANDS = {
"Filtration" : ("filtration", {"Filtration OFF": 2, "Filtration ON":1, "Filtration TIMER":3, "Filtration AUTO":0, "Filtration CHOC":4}, "Filtration AUTO"),
"Light": ("lighting", {"Pool Light OFF": 2, "Pool Light TIMER": 1, "Pool Light ON":0}, "Pool Light OFF"),
"Heating Regulation" : ("heating_regulation", {"Pool Heat OFF": 1, "Pool Heat AUTO":0}, "Pool Heat OFF"),
"pH Regulation" : ("ph_regulation", {"pH Regulation OFF": 1, "pH Regulation AUTO":0}, "pH Regulation AUTO"),
"Redox Regulation" : ("orp_regulation", {"redox Regulation OFF": 1, "redox Regulation AUTO":0}, "redox Regulation AUTO")
}


HYDROCAPT_INTERNAL_TO_EXTERNAL_COMMANDS = {}
for k_ext, v_trad in HYDROCAPT_EXTERNAL_TO_INTERNAL_COMMANDS.items():
    int_cmd_to_ext = {v: k for k, v in v_trad[1].items()}
    HYDROCAPT_INTERNAL_TO_EXTERNAL_COMMANDS[v_trad[0]] = (k_ext, int_cmd_to_ext, v_trad[1][v_trad[2]])


HYDROCAPT_EXTERNAL_COMMANDS = {}
for k_ext, v_trad in HYDROCAPT_EXTERNAL_TO_INTERNAL_COMMANDS.items():
    default_v = v_trad[2]
    cmds = [default_v]
    for k in v_trad[1]:
        if k != default_v:
            cmds.append(k)
    HYDROCAPT_EXTERNAL_COMMANDS[k_ext] = cmds


HYDROCAPT_TIMER = "timer"


HYDROCAPT_EXTERNAL_TO_INTERNAL_CONSIGNS = {
  "setpoint_heating": ["setpoint_heating", "integer", "Heat"],
  "Filtration Timer": ["timer_filtration", HYDROCAPT_TIMER, "Filtration"],
  "Lighting Timer": ["timer_lighting", HYDROCAPT_TIMER, "Pool Light"]
}

HYDROCAPT_INTERNAL_TO_EXTERNAL_CONSIGNS = {}
for k_ext, v_trad in HYDROCAPT_EXTERNAL_TO_INTERNAL_CONSIGNS.items():
    HYDROCAPT_INTERNAL_TO_EXTERNAL_CONSIGNS[v_trad[0]] = [k_ext, v_trad[1], v_trad[2]]

HYDROCAPT_TIMERS = {}
for k_ext, v_trad in HYDROCAPT_EXTERNAL_TO_INTERNAL_CONSIGNS.items():
    if v_trad[1] == HYDROCAPT_TIMER:
        HYDROCAPT_TIMERS[v_trad[0]] = v_trad[2]


HYDROCAPT_LOGIN_URL = "https://www.hydrocapt.fr/pool/poolLogin/login"
HYDROCAPT_DISCONNECT_URL = "https://www.hydrocapt.fr/pool/poolLogin/disconnect"
HYDROCAPT_EDIT_POOL_OWN_URL = "https://www.hydrocapt.fr/pool/poolEdit/own"
HYDROCAPT_AJAX_VALUES_HISTORY = "https://www.hydrocapt.fr/pool/ajaxHistoric/getJsonValues"
HYDROCAPT_GET_POOL_COMMAND_URL = "https://www.hydrocapt.fr/pool/ajaxCommands/get"
HYDROCAPT_SAVE_POOL_COMMAND_URL = "https://www.hydrocapt.fr/pool/ajaxCommands/save"
HYDROCAPT_POOL_LIST_OWN_URL = "https://www.hydrocapt.fr/pool/poolList/own"
HYDROCAPT_CURRENT_COMMAND_STATE_URL = "https://www.hydrocapt.fr/pool/ajaxOmeoGetCurrentsOrder"
HYDROCAPT_GET_ALARMS_URL = "https://www.hydrocapt.fr/pool/ajaxAlarms/get"
HYDROCAPT_AJAX_POOL_HISTORIC = "https://www.hydrocapt.fr/pool/poolHistoric"

HYDROCAPT_GET_POOL_CONSIGN_URL = "https://www.hydrocapt.fr/pool/ajaxSetpoints/get"
HYDROCAPT_SAVE_POOL_CONSIGN_URL = "https://www.hydrocapt.fr/pool/ajaxSetpoints/save"