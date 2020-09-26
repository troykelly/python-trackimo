# -*- coding: utf-8 -*-
"""
Protocol handler for Trackimo
"""

import logging
import sys
import requests
import os
import asyncio
import functools

from datetime import datetime, timedelta
from .user import UserHandler
from .account import AccountHandler
from ..exceptions import (
    MissingInformation,
    UnableToAuthenticate,
    NoSession,
    CanNotRefresh,
    TrackimoAPI,
)

_logger = logging.getLogger(__name__)


class Protocol(object):
    def __init__(
        self,
        clientid,
        clientsecret,
        host="app.trackimo.com",
        version=3,
        port=443,
        protocol="https",
        username=None,
        password=None,
        loop=None,
    ):
        super().__init__()
        self.__loop = loop if loop else asyncio.get_event_loop()

        self.__clientid = clientid
        self.__clientsecret = clientsecret
        self.__host = host
        self.__version = version
        self.__port = port
        self.__protocol = protocol

        self.__api_url = (
            f"{self.__protocol}://{self.__host}:{self.__port}/api/v{self.__version}"
        )
        self.__api_login_url = f"{self.__protocol}://{self.__host}:{self.__port}/api/internal/v2/user/login"

        self.__session = None
        self.__api_token = None
        self.__api_expires = None
        self.__refresh_token = None
        self.__trackimo_username = username if username else None
        self.__trackimo_password = password if password else None
        self.__trackimo_accountid = None
        self.__user = None

        self.__scopes = [
            "locations",
            "notifications",
            "devices",
            "accounts",
            "settings",
            "geozones",
        ]

    @property
    def accountid(self):
        return self.__trackimo_accountid

    @property
    def auth(self):
        if not self.__api_token:
            return None
        return {
            "token": self.__api_token,
            "refresh": self.__refresh_token,
            "expires": self.__api_expires,
        }

    @property
    def loop(self):
        if not self.__loop:
            return None
        return self.__loop

    async def login(self, username=None, password=None, scopes=None):

        if username:
            self.__trackimo_username = username
        if password:
            self.__trackimo_password = password
        if scopes:
            self.__scopes = scopes

        if not (self.__trackimo_username and self.__trackimo_password):
            raise UnableToAuthenticate("Must have a username and password available")

        self.__session = requests.Session()

        login_payload = {
            "username": self.__trackimo_username,
            "password": self.__trackimo_password,
            "remember_me": True,
            "whitelabel": "TRACKIMO",
        }

        auth_payload = {
            "client_id": self.__clientid,
            "redirect_uri": "https://app.trackimo.com/api/internal/v1/oauth_redirect",
            "response_type": "code",
            "scope": ",".join(self.__scopes),
        }

        token_payload = {
            "client_id": self.__clientid,
            "client_secret": self.__clientsecret,
            "code": None,
        }

        def send_login_payload():
            return self.__session.request(
                "POST", self.__api_login_url, json=login_payload, allow_redirects=True
            )

        future = self.__loop.run_in_executor(None, send_login_payload)

        response = await future

        if not response.status_code == 200:
            raise UnableToAuthenticate(
                "Could not authenticate with login endpoint", response.status_code
            )

        try:
            data = await self.api_get("oauth2/auth", auth_payload)
        except TrackimoAPI as apierror:
            raise UnableToAuthenticate(
                "Could not proceed with authentication after login",
                apierror.status_code,
            )
        except:
            raise Exception(sys.exc_info()[0])

        if not data or not "code" in data:
            raise UnableToAuthenticate(
                "Could not retrieve authentication code from API"
            )

        token_payload["code"] = data["code"]
        try:
            data = await self.api_post("oauth2/token", token_payload)
        except TrackimoAPI as apierror:
            raise UnableToAuthenticate(
                "Could not swap a code for a token", apierror.status_code
            )
        except:
            raise Exception(sys.exc_info()[0])

        if not data or not "access_token" in data:
            raise UnableToAuthenticate("Could not retrieve access token code from API")

        self.__api_token = data["access_token"]
        if "refresh_token" in data:
            self.__refresh_token = data["refresh_token"]

        if "expires_in" in data:
            self.__api_expires = datetime.now() + timedelta(
                seconds=int(data["expires_in"]) / 1000
            )

        await self.__post_login()

        return {
            "token": self.__api_token,
            "refresh": self.__refresh_token,
            "expires": self.__api_expires,
        }

    async def __token_refresh(self):

        if not self.__refresh_token:
            _logger.debug("No refresh token available. Logging in.")
            return await self.login()

        refresh_payload = {
            "client_id": self.__clientid,
            "client_secret": self.__clientsecret,
            "refresh_token": self.__refresh_token,
        }

        self.__session = requests.Session()
        self.__api_token = None
        self.__refresh_token = None
        self.__api_expires = None

        try:
            data = await self.api_post("oauth2/token/refresh", refresh_payload)
        except TrackimoAPI as apierror:
            _logger.debug("Could not refresh. Trying to log in.")
            return await self.login()
        except:
            raise Exception(sys.exc_info()[0])

        if not data or not "access_token" in data:
            _logger.debug("Could not refresh. Trying to log in.")
            return await self.login()

        self.__api_token = data["access_token"]
        if "refresh_token" in data:
            _logger.debug("Token refreshed. Updating token.")
            self.__refresh_token = data["refresh_token"]

        if "expires_in" in data:
            _logger.debug("Token refreshed. Updating expiry time.")
            self.__api_expires = datetime.now() + timedelta(
                seconds=int(data["expires_in"]) / 1000
            )

        await self.__post_login()

        return {
            "token": self.__api_token,
            "refresh": self.__refresh_token,
            "expires": self.__api_expires,
        }

    async def __post_login(self):

        handler = UserHandler(self)
        user = await handler.get()

        if not user:
            raise UnableToAuthenticate("Could not fetch user information.")

        self.__user = user
        self.__trackimo_accountid = user.accountId
        return user

    async def api(self, method="GET", path="", data=None, headers={}):
        if not self.__session:
            raise NoSession("There is no current API session. Please login() first.")

        if self.__api_expires and datetime.now() > self.__api_expires:
            _logger.debug("Refreshing token, it has expired.")
            self.__token_refresh()

        url = f"{self.__api_url}/{path}"

        method = method.upper()
        json = None
        params = None

        if method == "GET":
            if data:
                params = data
        elif method == "POST":
            if data:
                json = data
        elif method == "DELETE":
            if data:
                json = data
        elif method == "PUT":
            if data:
                json = data

        if self.__api_token:
            headers["Authorization"] = f"Bearer {self.__api_token}"

        _logger.debug({"url": url, "params": params, "data": json})

        def process_request():
            return self.__session.request(
                method, url, params=params, json=json, headers=headers
            )

        future = self.__loop.run_in_executor(None, process_request)

        response = await future
        success = 200 <= response.status_code <= 299
        try:
            data = response.json()
        except:
            data = None
        if not success:
            body = response.body if hasattr(response, "body") else None
            _logger.error(response.headers)
            raise TrackimoAPI(
                "Trackimo API Call failed.",
                response.status_code,
                body,
                data,
                response.headers,
            )

        if not data:
            data = {}
        return data

    async def api_get(self, path=None, data=None):
        """Make a get request to the Trackimo API

        Attributes:
            path (str): The path of the API endpoint
            data (object): Data to be passed as a querystring
        """
        return await self.api("GET", path=path, data=data)

    async def api_post(self, path=None, data=None):
        """Make a post request to the Trackimo API

        Attributes:
            path (str): The path of the API endpoint
            data (object): Data to be passed as a json payload
        """
        return await self.api("POST", path=path, data=data)

    async def api_delete(self, path=None, data=None):
        """Make a delete request to the Trackimo API

        Attributes:
            path (str): The path of the API endpoint
            data (object): Data to be passed as a json payload
        """
        return await self.api("DELETE", path=path, data=data)

    async def api_put(self, path=None, data=None):
        """Make a put request to the Trackimo API

        Attributes:
            path (str): The path of the API endpoint
            data (object): Data to be passed as a json payload
        """
        return await self.api("PUT", path=path, data=data)
