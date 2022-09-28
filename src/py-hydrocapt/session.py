# -*- coding: utf-8 -*-
"""Session manager for the hydrocapt API in order to maintain authentication between calls."""
#from urllib.parse import quote_plus


import requests
from requests import Session

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from .exceptions import HydrocaptError

from lxml import html

from .const import HYDROCAPT_LOGIN_URL
from .const import HYDROCAPT_DISCONNECT_URL
from .const import HYDROCAPT_EDIT_POOL_OWN_URL

class HydrocaptClientSession(object):
    """HTTP session manager for Hydrocapt api.
    This session object allows to manage the authentication and re-authentication
    """


    def __init__(self, username: str, password: str, pool_internal_id :int = -1) -> None:
        """Initialize and authenticate.

        Args:
            username: the hydrocapt registered user
            password: the hydrocapt user's password
        """

        self.username = username
        self.password = password
        self._session : Optional[Session] = None
        self._pool_internal_id = pool_internal_id


    def _new_session(self) -> Session:


        session_requests = requests.session()


        #use quote, from urllib.parse import quote, or quote_plus here for the strings?
        payload = {
            "login": self.username,
            "pass": self.password,
        }

        result = session_requests.post(
            HYDROCAPT_LOGIN_URL,
            data=payload,
            headers=dict(referer=HYDROCAPT_DISCONNECT_URL)
        )

        result.raise_for_status()

        if self._pool_internal_id < 0:


            result_edit_pool = session_requests.get(
                HYDROCAPT_EDIT_POOL_OWN_URL,
            )

            result_edit_pool.raise_for_status()

            tree = html.fromstring(result_edit_pool.text)

            try:
                pool_id = int(list(set(tree.xpath("//input[@name='serial']/@value")))[0])

            except:
                raise HydrocaptError("Hydrocapt Diffazur: Can't get pool id")

            self._pool_internal_id = pool_id

        return session_requests

    def get_internal_pool_id(self):

        if self._pool_internal_id < 0 or self._session is None:
            self._session = self._new_session()

        return self._pool_internal_id

    def post(self, url, data, headers=None):

        if self._session is None:
            self._session = self._new_session()


        if headers is None:
            headers = {}

        if headers.get("referer") is None:
            headers["referer"] = url

        try:
            ret = self._session.post(url, data=data, headers=headers)
            ret.raise_for_status()
        except:
            self._session = self._new_session()
            ret = self._session.post(url, data=data, headers=headers)

        ret.raise_for_status()


        return ret

    def get(self, url):

        if self._session is None:
            self._session = self._new_session()

        ret = None
        try:
            ret = self._session.get(url)
            ret.raise_for_status()
        except:
            self._session = self._new_session()
            ret = self._session.get(url)

        ret.raise_for_status()

        return ret
