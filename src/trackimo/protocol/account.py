# -*- coding: utf-8 -*-
"""
Account class for Trackimo
"""
import logging
from distutils.util import strtobool

_logger = logging.getLogger(__name__)


class AccountHandler(object):
    def __init__(self, protocol):
        super().__init__()
        self.__protocol = protocol

    async def get(self):
        data = await self.__protocol.api_get(f"accounts/{self.__protocol.accountid}")

        if not data:
            return

        return Account(apiObject=data)


class Account(object):
    def __init__(
        self,
        apiObject=None,
        id=None,
        name=None,
        address=None,
        phone=None,
        email=None,
        forceWifiOverGsmEnabled=None,
        trusted=None,
        parentId=None,
        logoUrl=None,
        preferences=None,
    ):
        super().__init__()
        if apiObject:
            self.__fromApi(apiObject)
        if id:
            self.id = id
        if name:
            self.name = name
        if address:
            self.address = address
        if phone:
            self.phone = phone
        if email:
            self.email = email
        if forceWifiOverGsmEnabled:
            self.forceWifiOverGsmEnabled = forceWifiOverGsmEnabled
        if trusted:
            self.trusted = trusted
        if parentId:
            self.parentId = int(parentId)
        if logoUrl:
            self.logoUrl = logoUrl
        if preferences:
            self.preferences = Preferences(apiObject=preferences)

    def __fromApi(self, apiObject):
        if not apiObject:
            _logger.error("Called fromAPI but no object passed")
            return False
        if "id" in apiObject:
            self.id = apiObject["id"]
        if "name" in apiObject:
            self.name = apiObject["name"]
        if "address" in apiObject:
            self.address = apiObject["address"]
        if "phone" in apiObject:
            self.phone = apiObject["phone"]
        if "email" in apiObject:
            self.email = apiObject["email"]
        if "forceWifiOverGsmEnabled" in apiObject:
            self.forceWifiOverGsmEnabled = apiObject["forceWifiOverGsmEnabled"]
        if "trusted" in apiObject:
            self.trusted = apiObject["trusted"]
        if "parent_id" in apiObject:
            self.parentId = int(apiObject["parent_id"])
        if "logo_url" in apiObject:
            self.logoUrl = apiObject["logo_url"]
        if "preferences" in apiObject:
            self.preferences = Preferences(apiObject=apiObject["preferences"])

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
    def name(self):
        return self.__name

    @name.setter
    def name(self, val=None):
        if not val:
            self.__name = None
        else:
            self.__name = val

    @property
    def address(self):
        return self.__address

    @address.setter
    def address(self, val=None):
        if not val:
            self.__address = None
        else:
            self.__address = val

    @property
    def phone(self):
        return self.__phone

    @phone.setter
    def phone(self, val=None):
        if not val:
            self.__phone = None
        else:
            self.__phone = val

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
    def forceWifiOverGsmEnabled(self):
        return self.__forceWifiOverGsmEnabled

    @forceWifiOverGsmEnabled.setter
    def forceWifiOverGsmEnabled(self, val=None):
        if not val or val is None:
            self.__forceWifiOverGsmEnabled = None
        else:
            self.__forceWifiOverGsmEnabled = strtobool(str(val))

    @property
    def trusted(self):
        return self.__trusted

    @trusted.setter
    def trusted(self, val=None):
        if not val or val is None:
            self.__trusted = None
        else:
            self.__trusted = strtobool(str(val))

    @property
    def parentId(self):
        return self.__parentId

    @parentId.setter
    def parentId(self, val=None):
        if not val:
            self.__parentId = None
        else:
            self.__parentId = int(val)

    @property
    def logoUrl(self):
        return self.__logoUrl

    @logoUrl.setter
    def logoUrl(self, val=None):
        if not val:
            self.__logoUrl = None
        else:
            self.__logoUrl = val

    @property
    def preferences(self):
        return self.__preferences

    @preferences.setter
    def preferences(self, val=None):
        if not val:
            self.__preferences = None
        else:
            if type(val) is Preferences:
                self.__preferences = val
            else:
                self.__preferences = Preferences(val)


class Preferences(object):
    def __init__(self, apiObject=None):
        super().__init__()
        self.__language = None
        self.__dateFormat = None
        self.__sentEvents = None
        self.__speedUnit = None
        self.__sosAlarmSound = None
        self.__alwaysAlertContacts = None
        self.__emailNotifications = None
        self.__pushNotifications = None
        self.__sosEnabled = None
        self.__turnOffNotification = None
        self.__turnOnNotification = None
        if apiObject:
            self.__fromApi(apiObject)

    def __fromApi(self, apiObject):
        if not apiObject:
            _logger.error("Called fromAPI but no object passed")
            return False
        if "language" in apiObject:
            self.language = apiObject["language"]
        if "date_format" in apiObject:
            self.dateFormat = apiObject["date_format"]
        if "sent_events" in apiObject:
            self.sentEvents = apiObject["sent_events"]
        if "speed_unit" in apiObject:
            self.speedUnit = apiObject["speed_unit"]
        if "sos_alarm_sound" in apiObject:
            self.sosAlarmSound = apiObject["sos_alarm_sound"]
        if "always_alert_contacts" in apiObject:
            self.alwaysAlertContacts = apiObject["always_alert_contacts"]
        if "email_notifications" in apiObject:
            self.emailNotifications = apiObject["email_notifications"]
        if "push_notifications" in apiObject:
            self.pushNotifications = apiObject["push_notifications"]
        if "sqs_enabled" in apiObject:
            self.sosEnabled = apiObject["sqs_enabled"]
        if "turn_off_notification" in apiObject:
            self.turnOffNotification = apiObject["turn_off_notification"]
        if "turn_on_notification" in apiObject:
            self.turnOnNotification = apiObject["turn_on_notification"]

    @property
    def language(self):
        return self.__language

    @language.setter
    def language(self, val=None):
        if not val:
            self.__language = None
        else:
            self.__language = val

    @property
    def dateFormat(self):
        return self.__dateFormat

    @dateFormat.setter
    def dateFormat(self, val=None):
        if not val:
            self.__dateFormat = None
        else:
            self.__dateFormat = val

    @property
    def sentEvents(self):
        return self.__sentEvents

    @sentEvents.setter
    def sentEvents(self, val=None):
        if not val or val is None:
            self.__sentEvents = None
        else:
            self.__sentEvents = strtobool(str(val))

    @property
    def speedUnit(self):
        return self.__speedUnit

    @speedUnit.setter
    def speedUnit(self, val=None):
        if not val:
            self.__speedUnit = None
        else:
            self.__speedUnit = val

    @property
    def sosAlarmSound(self):
        return self.__sosAlarmSound

    @sosAlarmSound.setter
    def sosAlarmSound(self, val=None):
        if not val or val is None:
            self.__sosAlarmSound = None
        else:
            self.__sosAlarmSound = strtobool(str(val))

    @property
    def alwaysAlertContacts(self):
        return self.__alwaysAlertContacts

    @alwaysAlertContacts.setter
    def alwaysAlertContacts(self, val=None):
        if not val or val is None:
            self.__alwaysAlertContacts = None
        else:
            self.__alwaysAlertContacts = strtobool(str(val))

    @property
    def emailNotifications(self):
        return self.__emailNotifications

    @emailNotifications.setter
    def emailNotifications(self, val=None):
        if not val or val is None:
            self.__emailNotifications = None
        else:
            self.__emailNotifications = strtobool(str(val))

    @property
    def pushNotifications(self):
        return self.__pushNotifications

    @pushNotifications.setter
    def pushNotifications(self, val=None):
        if not val or val is None:
            self.__pushNotifications = None
        else:
            self.__pushNotifications = strtobool(str(val))

    @property
    def sosEnabled(self):
        return self.__sosEnabled

    @sosEnabled.setter
    def sosEnabled(self, val=None):
        if not val or val is None:
            self.__sosEnabled = None
        else:
            self.__sosEnabled = strtobool(str(val))

    @property
    def turnOffNotification(self):
        return self.__turnOffNotification

    @turnOffNotification.setter
    def turnOffNotification(self, val=None):
        if not val or val is None:
            self.__turnOffNotification = None
        else:
            self.__turnOffNotification = strtobool(str(val))

    @property
    def turnOnNotification(self):
        return self.__turnOnNotification

    @turnOnNotification.setter
    def turnOnNotification(self, val=None):
        if not val or val is None:
            self.__turnOnNotification = None
        else:
            self.__turnOnNotification = strtobool(str(val))
