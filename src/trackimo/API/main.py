# -*- coding: utf-8 -*-
import logging
import asyncio

from ..protocol import device, account, protocol
from ..exceptions import UnableToAuthenticate

_logger = logging.getLogger(__name__)


class Trackimo(object):
    def __init__(self, loop=None):
        super().__init__()
        self.__loop = loop if loop else asyncio.get_event_loop()
        self.__devices = None
        self.__account = None

    async def login(self, clientid, clientsecret, username, password):
        """Login to the Trackimo API

        Attributes:
            clientid (str): The API Client or App ID
            clientsecret (str): The API Client or APP Secret
            username (str): The Trackimo Username
            password (str): The Trackimo Password
        """
        self.__protocol = protocol.Protocol(
            clientid=clientid,
            clientsecret=clientsecret,
            username=username,
            password=password,
            loop=self.__loop,
        )
        authData = await self.__protocol.login()
        if not authData:
            raise UnableToAuthenticate("Not authenticated with Trackimo API")

        accountHandler = account.AccountHandler(self.__protocol)
        deviceHandler = device.DeviceHandler(self.__protocol)

        self.__account = await accountHandler.get()
        self.__devices = await deviceHandler.get()

        return self

    @property
    def auth(self):
        if not self.__protocol:
            _logger.error("Not currently connected. login() first.")
            return None
        return self.__protocol.auth

    @property
    def devices(self):
        if not self.__devices:
            _logger.error("No known devices. Make sure to login() first.")
            return {}
        return self.__devices

    @property
    def account(self):
        if not self.__account:
            _logger.error("No account details. Make sure to login() first.")
            return {}
        return self.__account