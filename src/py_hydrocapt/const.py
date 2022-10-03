# -*- coding: utf-8 -*-
"""Consts for Hydrocapt python client API."""



HYDROCAPT_EXTERNAL_TO_INTERNAL_COMMANDS = {
"filtration" : ("filtration", {"OFF": 2, "ON":1, "TIMER":3, "AUTO":0, "CHOC":4}, "AUTO"),
"light": ("lighting", {"OFF": 2, "TIMER": 1, "ON":0}, "OFF"),
"heating_regulation" : ("heating_regulation", {"OFF": 1, "AUTO":0}, "OFF"),
"ph_regulation" : ("ph_regulation", {"OFF": 1, "AUTO":0}, "AUTO"),
"redox_regulation" : ("orp_regulation", {"OFF": 1, "AUTO":0}, "AUTO")
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