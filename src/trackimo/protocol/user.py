# -*- coding: utf-8 -*-
"""
User class for Trackimo
"""
import logging

_logger = logging.getLogger(__name__)


class UserHandler(object):
    def __init__(self, protocol):
        super().__init__()
        self.__protocol = protocol

    async def get(self):
        data = await self.__protocol.api_get("user")
        if not data:
            return

        user = User()

        if "email" in data:
            user.email = data["email"]
        if "firstName" in data:
            user.givenName = data["firstName"]
        if "lastName" in data:
            user.familyName = data["lastName"]
        if "user_id" in data:
            user.id = data["user_id"]
        if "user_name" in data:
            user.username = data["user_name"]
        if "account_id" in data:
            user.accountId = data["account_id"]

        return user


class User(object):
    def __init__(
        self,
        id=None,
        email=None,
        givenName=None,
        familyName=None,
        username=None,
        accountId=None,
    ):
        super().__init__()
        self.__id = id if id else None
        self.__email = email if email else None
        self.__givenName = givenName if givenName else None
        self.__familyName = familyName if familyName else None
        self.__username = username if username else None
        self.__accountId = accountId if accountId else None

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, val=None):
        if not val:
            self.__id = None
        else:
            self.__id = int(val)

    @property
    def email(self):
        return self.__email

    @email.setter
    def email(self, val=None):
        if not val:
            self.__email = None
        else:
            self.__email = val

    @property
    def givenName(self):
        return self.__givenName

    @givenName.setter
    def givenName(self, val=None):
        if not val:
            self.__givenName = None
        else:
            self.__givenName = val

    @property
    def familyName(self):
        return self.__familyName

    @familyName.setter
    def familyName(self, val=None):
        if not val:
            self.__familyName = None
        else:
            self.__familyName = val

    @property
    def username(self):
        return self.__username

    @username.setter
    def username(self, val=None):
        if not val:
            self.__username = None
        else:
            self.__username = val

    @property
    def accountId(self):
        return self.__accountId

    @accountId.setter
    def accountId(self, val=None):
        if not val:
            self.__accountId = None
        else:
            self.__accountId = int(val)