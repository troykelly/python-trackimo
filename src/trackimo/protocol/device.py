# -*- coding: utf-8 -*-
"""
Device handler for Trackimo
"""

import logging
import sys
import os
from datetime import datetime, timedelta
import geocoder
import asyncio

_logger = logging.getLogger(__name__)

GEO_CACHE = {}


class DeviceHandler(object):
    def __init__(self, protocol):
        super().__init__()
        self.__protocol = protocol
        self.__devices = {}

    @property
    def loop(self):
        if not self.__protocol.loop:
            return None
        return self.__protocol.loop

    @property
    def __list(self):
        if not self.__devices:
            return []
        return [*self.__devices]

    async def build(self, limit=20, page=1):
        allDevices = await self.__listall(limit=limit, page=page)
        while allDevices:
            for deviceReference in allDevices:
                if "deviceId" in deviceReference:
                    id = int(deviceReference["deviceId"])
                    self.__devices[id] = Device(self, id)
                    await self.__devices[id].build()
            page += 1
            allDevices = await self.__listall(limit=limit, page=page)
        await self.__locations()
        return self.__devices

    async def __listall(self, limit=20, page=1):
        pagination = {"limit": limit, "page": page}
        return await self.__protocol.api_get(
            f"accounts/{self.__protocol.accountid}/devices", pagination
        )

    async def details(self, id):
        """Get device details

        Attributes:
            id (int): The device id
        """
        return await self.__protocol.api_get(
            f"accounts/{self.__protocol.accountid}/devices/{id}"
        )

    async def location(self, id):
        """Get device location

        Attributes:
            id (int): The device id
        """
        return await self.__protocol.api_get(
            f"accounts/{self.__protocol.accountid}/devices/{id}/location"
        )

    async def history(self, id, start_date=None, end_date=None, limit=20, page=1):
        """Get device history

        Attributes:
            id (int): The device id
            start_date (datetime): Starting date for the history
            end_date (datetime): End date for the history
            limit (int): Results per page
            page (int): Page number
        """
        if not start_date:
            start_date = datetime.now() - timedelta(hours=24)
        if not end_date:
            end_date = datetime.now()
        data = {
            "from": int(start_date.timestamp()),
            "to": int(end_date.timestamp()),
            "limit": limit,
            "page": page,
        }
        return await self.__protocol.api_get(
            f"accounts/{self.__protocol.accountid}/devices/{id}/history", data
        )

    async def ops(self, id, operation="beep", options={}):
        options["devices"] = [id]
        return await self.__protocol.api_post(
            f"accounts/{self.__protocol.accountid}/devices/ops/{operation}", options
        )

    async def get_features(self, id):
        options = {}
        options["deviceIds"] = id
        return await self.__protocol.api(
            path="devices/features/deviceIds", data=options, use_internal_api=True
        )

    async def __locations(self):
        device_ids = self.__list
        changed_devices = list()
        pagination = {"limit": len(device_ids), "page": 1}
        url = f"accounts/{self.__protocol.accountid}/locations/filter"
        location_data = await self.__protocol.api_post(
            url, data={"device_ids": device_ids}, query_string=pagination
        )
        while location_data:
            pagination["page"] += 1
            _logger.debug(location_data)
            for device_location_data in location_data:
                if (
                    "device_id" in device_location_data
                    and device_location_data["device_id"] in self.__devices
                ):
                    await self.__devices[
                        device_location_data["device_id"]
                    ].location_event(device_location_data)
                    if self.__devices[device_location_data["device_id"]].changed:
                        changed_devices.append(device_location_data["device_id"])
            location_data = await self.__protocol.api_post(
                url, data={"device_ids": device_ids}, query_string=pagination
            )
        return changed_devices

    async def __track(self, interval, event_receiver=None):
        while True:
            _logger.debug("track is checking for changes...")
            changed_devices = await self.__locations()
            if changed_devices:
                _logger.debug(
                    "Devices changed: %s", ", ".join(map(str, changed_devices))
                )
                if event_receiver:
                    for device_id in changed_devices:
                        device = self.__devices[device_id]
                        try:
                            event_receiver(
                                event_type="location",
                                device_id=device_id,
                                device=device,
                                ts=datetime.now(),
                            )
                            _logger.debug(
                                "Change sent to event handler for %s (%d)",
                                device.name,
                                device.id,
                            )
                        except Exception as err:
                            _logger.exception(err)
            await asyncio.sleep(interval.total_seconds())

    def track(self, interval=None, event_receiver=None):
        if not self.__protocol.loop:
            return None

        if not interval:
            interval = timedelta(seconds=60)

        if not isinstance(interval, timedelta):
            interval = timedelta(seconds=interval)

        _logger.debug("Tracking devices every %d seconds...", interval.total_seconds())

        task = self.__protocol.loop.create_task(
            self.__track(interval=interval, event_receiver=event_receiver)
        )

        return task


class Device(object):
    def __init__(self, handler, id=None):
        super().__init__()

        if handler:
            self.__handler = handler
        if id:
            self.__id = id

        self.__previous_latitude = None
        self.__previous_longitude = None
        self.__previous_altitude = None
        self.__previous_battery = None
        self.__previous_hdop = None
        self.__previous_gps = None
        self.__previous_locationTriangulated = None
        self.__previous_locationType = None

    async def location_event(self, location_data):
        if not self.__id:
            return
        _logger.debug("Updating device %d location data: %s", self.__id, location_data)
        if location_data:
            if "time" in location_data:
                self.__locationUpdated = datetime.fromtimestamp(
                    int(location_data["time"])
                )
            elif "updated" in location_data:
                self.__locationUpdated = datetime.fromtimestamp(
                    int(location_data["updated"]) / 1000.0
                )
            else:
                self.__locationUpdated = None
            self.__locationAge = (
                int(location_data["age"])
                if "age" in location_data and location_data["age"]
                else None
            )
            self.__altitude = (
                float(location_data["altitude"])
                if "altitude" in location_data and location_data["altitude"]
                else None
            )
            self.__battery = (
                int(location_data["battery"])
                if "battery" in location_data and location_data["battery"]
                else None
            )
            self.__gps = (
                location_data["gps"]
                if "gps" in location_data and location_data["gps"]
                else False
            )
            self.__hdop = (
                float(location_data["hdop"])
                if "hdop" in location_data and location_data["hdop"]
                else None
            )
            self.__latitude = (
                float(location_data["lat"])
                if "lat" in location_data and location_data["lat"]
                else None
            )
            self.__longitude = (
                float(location_data["lng"])
                if "lng" in location_data and location_data["lng"]
                else None
            )
            self.__location_id = (
                int(location_data["location_id"])
                if "location_id" in location_data
                and location_data["location_id"]
                and location_data["location_id"] != -1
                else None
            )
            self.__manual_location = (
                location_data["manual_location"]
                if "manual_location" in location_data
                and location_data["manual_location"]
                else False
            )
            self.__moving = (
                location_data["moving"]
                if "moving" in location_data and location_data["moving"]
                else False
            )
            self.__speed = (
                float(location_data["speed"])
                if "speed" in location_data
                and location_data["speed"]
                or location_data["speed"] == 0
                else None
            )
            self.__speedUnit = (
                location_data["speed_unit"]
                if "speed_unit" in location_data and location_data["speed_unit"]
                else None
            )
            self.__locationTriangulated = (
                location_data["is_triangulated"]
                if "is_triangulated" in location_data
                and location_data["is_triangulated"]
                else False
            )
            self.__locationType = (
                location_data["type"]
                if "type" in location_data and location_data["type"]
                else None
            )
        else:
            self.__locationUpdated = None
            self.__locationAge = None
            self.__altitude = None
            self.__battery = None
            self.__gps = None
            self.__hdop = None
            self.__latitude = None
            self.__longitude = None
            self.__location_id = None
            self.__manual_location = None
            self.__moving = None
            self.__speed = None
            self.__speedUnit = None
            self.__locationTriangulated = None
            self.__locationType = None

        await self.__reverseGeocode()
        self.__changed = self.__check_changed()
        return self.location

    def __check_changed(self):
        changed = False
        if not self.__previous_latitude == self.__latitude:
            changed = True
        if not self.__previous_longitude == self.__longitude:
            changed = True
        if not self.__previous_altitude == self.__altitude:
            changed = True
        if not self.__previous_battery == self.__battery:
            changed = True
        if not self.__previous_hdop == self.__hdop:
            changed = True
        if not self.__previous_gps == self.__gps:
            changed = True
        if not self.__previous_locationTriangulated == self.__locationTriangulated:
            changed = True
        if not self.__previous_locationType == self.__locationType:
            changed = True

        self.__previous_latitude = self.__latitude
        self.__previous_longitude = self.__longitude
        self.__previous_altitude = self.__altitude
        self.__previous_battery = self.__battery
        self.__previous_hdop = self.__hdop
        self.__previous_gps = self.__gps
        self.__previous_locationTriangulated = self.__locationTriangulated
        self.__previous_locationType = self.__locationType

        return changed

    async def refresh(self):
        if not self.__id:
            return
        location_data = await self.__handler.location(self.__id)
        return await self.location_event(location_data)

    async def __reverseGeocode(self):
        global GEO_CACHE

        if not (self.__latitude and self.__longitude):
            return None
        location = [self.__latitude, self.__longitude]
        location_text = str(self.__latitude) + " " + str(self.__longitude)
        if location_text in GEO_CACHE:
            return GEO_CACHE[location_text]

        def getGeoData():
            return geocoder.osm(location, method="reverse")

        try:
            g = await self.__handler.loop.run_in_executor(None, getGeoData)
        except Exception as err:
            _logger.error("Geocoder unavailable")
            _logger.error(err)

        if not g and g.json:
            self.__address = None
            return None

        GEO_CACHE[location_text] = g.json
        self.__address = GEO_CACHE[location_text]
        return GEO_CACHE[location_text]

    async def build(self):
        details_data = await self.__handler.details(self.__id)
        features_data = await self.__get_features()

        if details_data:
            self.__imsi = (
                details_data["imsi"]
                if "imsi" in details_data and details_data["imsi"]
                else None
            )
            self.__msisdn = (
                details_data["msisdn"]
                if "msisdn" in details_data and details_data["msisdn"]
                else None
            )
            self.__name = (
                details_data["name"]
                if "name" in details_data and details_data["name"]
                else None
            )
            self.__status = (
                details_data["status"]
                if "status" in details_data and details_data["status"]
                else None
            )
            self.__type = (
                details_data["type"]
                if "type" in details_data and details_data["type"]
                else None
            )
            self.__typeId = (
                int(details_data["typeId"])
                if "typeId" in details_data and details_data["typeId"]
                else None
            )
            self.__accountId = (
                int(details_data["account_id"])
                if "account_id" in details_data and details_data["account_id"]
                else None
            )
            self.__userId = (
                int(details_data["user_id"])
                if "user_id" in details_data and details_data["user_id"]
                else None
            )
            self.__iconId = (
                int(details_data["icon_id"])
                if "icon_id" in details_data and details_data["icon_id"]
                else None
            )
        else:
            self.__imsi = None
            self.__msisdn = None
            self.__name = None
            self.__status = None
            self.__type = None
            self.__typeId = None
            self.__accountId = None
            self.__userId = None
            self.__iconId = None

        return self

    async def beep(self, period=2, sound=1):
        beep_data = {"beepPeriod": period, "beepType": sound}
        return await self.__handler.ops(self.__id, "beep", beep_data)

    async def get_location(self, force_gps_read=True, send_gsm_before_lock=True):
        get_location_data = {
            "forceGpsRead": force_gps_read,
            "sendGsmBeforeLock": send_gsm_before_lock,
        }
        return await self.__handler.ops(self.__id, "getLocation", get_location_data)

    async def __get_features(self):
        features_data = await self.__handler.get_features(self.__id)
        if not features_data:
            return None
        _logger.debug("Updating device %d features data: %s", self.__id, features_data)
        self.__features = Features(features_data)
        return self.__features

    @property
    def id(self):
        try:
            return self.__id
        except AttributeError:
            return None

    @property
    def changed(self):
        try:
            return self.__changed
        except AttributeError:
            return None

    @property
    def location(self):
        data = {}
        try:
            data["latitude"] = self.__latitude
        except AttributeError:
            data["latitude"] = None
        try:
            data["longitude"] = self.__longitude
        except AttributeError:
            data["longitude"] = None
        try:
            data["atitude"] = self.__altitude
        except AttributeError:
            data["atitude"] = None
        try:
            data["ts"] = self.__locationUpdated
        except AttributeError:
            data["ts"] = None
        try:
            data["address"] = self.__address
        except AttributeError:
            data["address"] = None

        return data

    @property
    def attribution(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "raw" in address and "licence" in address["raw"]:
            return address["raw"]["licence"]
        return None

    @property
    def address(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "address" in address:
            return address["address"]
        return None

    @property
    def city(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "city" in address:
            return address["city"]
        return None

    @property
    def country(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "country" in address:
            return address["country"]
        return None

    @property
    def postalcode(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "postal" in address:
            return address["postal"]
        return None

    @property
    def region(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "region" in address:
            return address["region"]
        return None

    @property
    def state(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "state" in address:
            return address["state"]
        return None

    @property
    def street(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "street" in address:
            return address["street"]
        return None

    @property
    def suburb(self):
        try:
            address = self.__address
        except AttributeError:
            return None
        if "suburb" in address:
            return address["suburb"]
        return None

    @property
    def latitude(self):
        data = {}
        try:
            data["latitude"] = self.__latitude
        except AttributeError:
            data["latitude"] = None
        try:
            data["longitude"] = self.__longitude
        except AttributeError:
            data["longitude"] = None

        if not (data["latitude"] and data["longitude"]):
            return None

        return data["latitude"]

    @property
    def longitude(self):
        data = {}
        try:
            data["latitude"] = self.__latitude
        except AttributeError:
            data["latitude"] = None
        try:
            data["longitude"] = self.__longitude
        except AttributeError:
            data["longitude"] = None

        if not (data["latitude"] and data["longitude"]):
            return None

        return data["longitude"]

    @property
    def altitude(self):
        try:
            return self.__altitude
        except AttributeError:
            return None

    @property
    def updated(self):
        data = {}
        try:
            data["latitude"] = self.__latitude
        except AttributeError:
            data["latitude"] = None
        try:
            data["longitude"] = self.__longitude
        except AttributeError:
            data["longitude"] = None
        try:
            data["ts"] = self.__locationUpdated
        except AttributeError:
            data["ts"] = None

        if not (data["ts"] and data["longitude"] and data["latitude"]):
            return None

        return data["ts"]

    @property
    def age(self):
        if not self.updated:
            return None

        time_delta = datetime.now() - self.updated
        return round(time_delta.total_seconds())

    @property
    def battery(self):
        try:
            return self.__battery
        except AttributeError:
            return None

    @property
    def locationType(self):
        try:
            return self.__locationType
        except AttributeError:
            return None

    @property
    def speedKMH(self):
        data = {}
        try:
            data["unit"] = self.__speedUnit
        except AttributeError:
            return None
        try:
            data["speed"] = self.__speed
        except AttributeError:
            return None

        if not (data["speed"] and data["unit"]):
            return None

        if data["unit"] == "kph":
            return data["speed"]
        if data["unit"] == "mph":
            return 1.60934 * data["speed"]

        return None

    @property
    def speedMPH(self):
        data = {}
        try:
            data["unit"] = self.__speedUnit
        except AttributeError:
            return None
        try:
            data["speed"] = self.__speed
        except AttributeError:
            return None

        if not (data["speed"] and data["unit"]):
            return None

        if data["unit"] == "kph":
            return data["speed"]
        if data["unit"] == "mph":
            return 0.6214 * data["speed"]

        return None

    @property
    def speedMPS(self):
        data = {}
        try:
            data["unit"] = self.__speedUnit
        except AttributeError:
            return None
        try:
            data["speed"] = self.__speed
        except AttributeError:
            return None

        if not (data["speed"] and data["unit"]):
            return None

        if data["unit"] == "kph":
            return data["speed"] / 3.6
        if data["unit"] == "mph":
            return data["speed"] / 2.237

    @property
    def triangulated(self):
        try:
            return self.__locationTriangulated
        except AttributeError:
            return None

    @property
    def imsi(self):
        try:
            return self.__imsi
        except AttributeError:
            return None

    @property
    def msisdn(self):
        try:
            return self.__msisdn
        except AttributeError:
            return None

    @property
    def name(self):
        try:
            return self.__name
        except AttributeError:
            return None

    @property
    def status(self):
        try:
            return self.__status
        except AttributeError:
            return None

    @property
    def typeName(self):
        try:
            return self.__type
        except AttributeError:
            return None

    @property
    def typeId(self):
        try:
            return self.__typeId
        except AttributeError:
            return None

    @property
    def iconId(self):
        try:
            return self.__iconId
        except AttributeError:
            return None

    @property
    def features(self):
        try:
            return self.__features
        except AttributeError:
            return None


class Features(object):
    def __init__(self, payload={}):
        super().__init__()
        for device in payload:
            if "id" in device:
                self.id = device["id"]
            if "fwVer" in device:
                self.firmware = device["fwVer"]
            if "fwVerExternal" in device:
                self.external = device["fwVerExternal"]
            if "features" in device:
                for attribute, value in device["features"].items():
                    if str(value) == "not-supported":
                        setattr(self, attribute, False)
                    elif str(value) == "supported":
                        setattr(self, attribute, True)
                    else:
                        setattr(self, attribute, value)
