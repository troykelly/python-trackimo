# -*- coding: utf-8 -*-
"""
Device handler for Trackimo
"""

import logging
import sys
import os
from datetime import datetime, timedelta
import geocoder

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

    async def get(self, limit=20, page=1):
        allDevices = await self.__listall(limit=limit, page=page)
        while allDevices:
            for deviceReference in allDevices:
                if "deviceId" in deviceReference:
                    id = int(deviceReference["deviceId"])
                    self.__devices[id] = Device(self, id)
                    await self.__devices[id].get()
            page += 1
            allDevices = await self.__listall(limit=limit, page=page)
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


class Device(object):
    def __init__(self, handler, id=None):
        super().__init__()
        if handler:
            self.__handler = handler
        if id:
            self.__id = id

    async def refresh(self):
        if not self.__id:
            return
        locationData = await self.__handler.location(self.__id)
        if locationData:
            self.__locationUpdated = (
                datetime.fromtimestamp(int(locationData["updated"]) / 1000.0)
                if "updated" in locationData and locationData["updated"]
                else None
            )
            self.__locationAge = (
                int(locationData["age"])
                if "age" in locationData and locationData["age"]
                else None
            )
            self.__altitude = (
                float(locationData["altitude"])
                if "altitude" in locationData and locationData["altitude"]
                else None
            )
            self.__battery = (
                int(locationData["battery"])
                if "battery" in locationData and locationData["battery"]
                else None
            )
            self.__locationType = (
                locationData["type"]
                if "type" in locationData and locationData["type"]
                else None
            )
            self.__latitude = (
                float(locationData["lat"])
                if "lat" in locationData and locationData["lat"]
                else None
            )
            self.__longitude = (
                float(locationData["lng"])
                if "lng" in locationData and locationData["lng"]
                else None
            )
            self.__speed = (
                float(locationData["speed"])
                if "speed" in locationData
                and locationData["speed"]
                or locationData["speed"] == 0
                else None
            )
            self.__speedUnit = (
                locationData["speed_unit"]
                if "speed_unit" in locationData and locationData["speed_unit"]
                else None
            )
            self.__locationTriangulated = (
                locationData["is_triangulated"]
                if "is_triangulated" in locationData and locationData["is_triangulated"]
                else False
            )
        else:
            self.__locationUpdated = None
            self.__locationAge = None
            self.__altitude = None
            self.__battery = None
            self.__locationType = None
            self.__latitude = None
            self.__longitude = None
            self.__speed = None
            self.__speedUnit = None
            self.__locationTriangulated = None

        geocode = await self.__reverseGeocode()
        if geocode:
            self.__address = geocode
        else:
            self.__address = None

        return self.location

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

        future = self.__handler.loop.run_in_executor(None, getGeoData)
        g = await future

        if not g:
            return None
        GEO_CACHE[location_text] = g.json
        return GEO_CACHE[location_text]

    async def get(self):
        detailsData = await self.__handler.details(self.__id)

        if detailsData:
            self.__imsi = (
                detailsData["imsi"]
                if "imsi" in detailsData and detailsData["imsi"]
                else None
            )
            self.__msisdn = (
                detailsData["msisdn"]
                if "msisdn" in detailsData and detailsData["msisdn"]
                else None
            )
            self.__name = (
                detailsData["name"]
                if "name" in detailsData and detailsData["name"]
                else None
            )
            self.__status = (
                detailsData["status"]
                if "status" in detailsData and detailsData["status"]
                else None
            )
            self.__type = (
                detailsData["type"]
                if "type" in detailsData and detailsData["type"]
                else None
            )
            self.__typeId = (
                int(detailsData["typeId"])
                if "typeId" in detailsData and detailsData["typeId"]
                else None
            )
            self.__accountId = (
                int(detailsData["account_id"])
                if "account_id" in detailsData and detailsData["account_id"]
                else None
            )
            self.__userId = (
                int(detailsData["user_id"])
                if "user_id" in detailsData and detailsData["user_id"]
                else None
            )
            self.__iconId = (
                int(detailsData["icon_id"])
                if "icon_id" in detailsData and detailsData["icon_id"]
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

        await self.refresh()

        return self

    @property
    def id(self):
        if not self.__id:
            return None
        return self.__id

    @property
    def location(self):
        if not (self.__latitude and self.__longitude):
            return None
        data = {"latitude": self.__latitude, "longitude": self.__longitude}
        if self.__altitude:
            data["altitude"] = self.__altitude
        if self.__locationUpdated:
            data["ts"] = self.__locationUpdated
        if self.__address and "address" in self.__address:
            data["address"] = self.__address["address"]
        return data

    @property
    def attribution(self):
        if (
            self.__address
            and "raw" in self.__address
            and "licence" in self.__address["raw"]
        ):
            return self.__address["raw"]["licence"]
        return None

    @property
    def address(self):
        if self.__address and "address" in self.__address:
            return self.__address["address"]
        return None

    @property
    def city(self):
        if self.__address and "city" in self.__address:
            return self.__address["city"]
        return None

    @property
    def country(self):
        if self.__address and "country" in self.__address:
            return self.__address["country"]
        return None

    @property
    def postalcode(self):
        if self.__address and "postal" in self.__address:
            return self.__address["postal"]
        return None

    @property
    def region(self):
        if self.__address and "region" in self.__address:
            return self.__address["region"]
        return None

    @property
    def state(self):
        if self.__address and "state" in self.__address:
            return self.__address["state"]
        return None

    @property
    def street(self):
        if self.__address and "street" in self.__address:
            return self.__address["street"]
        return None

    @property
    def suburb(self):
        if self.__address and "suburb" in self.__address:
            return self.__address["suburb"]
        return None

    @property
    def latitude(self):
        if not (self.__latitude and self.__longitude):
            return None
        return self.__latitude

    @property
    def longitude(self):
        if not (self.__latitude and self.__longitude):
            return None
        return self.__longitude

    @property
    def altitude(self):
        if not self.__altitude:
            return None
        return self.__altitude

    @property
    def updated(self):
        if not (self.__latitude and self.__longitude and self.__locationUpdated):
            return None
        return self.__locationUpdated

    @property
    def age(self):
        if not (self.__latitude and self.__longitude and self.__locationUpdated):
            return None
        time_delta = datetime.now() - self.__locationUpdated
        return time_delta.total_seconds()

    @property
    def battery(self):
        if not self.__battery:
            return None
        return self.__battery

    @property
    def locationType(self):
        if not self.__locationType:
            return None
        return self.__locationType

    @property
    def speedKMH(self):
        if not (self.__speed and self.__speedUnit):
            return None
        if self.__speedUnit.lower() == "kph":
            return self.__speed
        if self.__speedUnit.lower() == "mph":
            return 1.60934 * self.__speed
        return None

    @property
    def speedMPH(self):
        if not (self.__speed and self.__speedUnit):
            return None
        if self.__speedUnit.lower() == "mph":
            return self.__speed
        if self.__speedUnit.lower() == "kph":
            return 0.6214 * self.__speed
        return None

    @property
    def speedMPS(self):
        if not (self.__speed and self.__speedUnit):
            return None
        if self.__speedUnit.lower() == "mph":
            return self.__speed / 2.237
        if self.__speedUnit.lower() == "kph":
            return self.__speed / 3.6
        return None

    @property
    def triangulated(self):
        if not self.__locationTriangulated:
            return None
        return self.__locationTriangulated

    @property
    def imsi(self):
        if not self.__imsi:
            return None
        return self.__imsi

    @property
    def msisdn(self):
        if not self.__msisdn:
            return None
        return self.__msisdn

    @property
    def name(self):
        if not self.__name:
            return None
        return self.__name

    @property
    def status(self):
        if not self.__status:
            return None
        return self.__status

    @property
    def typeName(self):
        if not self.__type:
            return None
        return self.__type

    @property
    def typeId(self):
        if not self.__typeId:
            return None
        return self.__typeId

    @property
    def iconId(self):
        if not self.__iconId:
            return None
        return self.__iconId


sample = {
    "accuracy": 0.001,
    "address": "Belcastro, Belcastro Lane, Eight Mile Plains, Brisbane, Queensland, 4113, Australia",
    "bbox": {
        "northeast": [-27.5854166, 153.0867724],
        "southwest": [-27.5857226, 153.0865314],
    },
    "city": "Brisbane",
    "confidence": 10,
    "country": "Australia",
    "country_code": "au",
    "importance": 0.001,
    "lat": -27.585563649999997,
    "lng": 153.08665216347964,
    "ok": True,
    "osm_id": 621636139,
    "osm_type": "way",
    "place_id": 210004813,
    "place_rank": 30,
    "postal": "4113",
    "quality": "house",
    "raw": {
        "place_id": 210004813,
        "licence": "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
        "osm_type": "way",
        "osm_id": 621636139,
        "boundingbox": ["-27.5857226", "-27.5854166", "153.0865314", "153.0867724"],
        "lat": "-27.585563649999997",
        "lon": "153.08665216347964",
        "display_name": "Belcastro, Belcastro Lane, Eight Mile Plains, Brisbane, Queensland, 4113, Australia",
        "place_rank": 30,
        "category": "building",
        "type": "house",
        "importance": 0.001,
        "address": {
            "building": "Belcastro",
            "road": "Belcastro Lane",
            "suburb": "Eight Mile Plains",
            "city": "Brisbane",
            "state": "Queensland",
            "postcode": "4113",
            "country": "Australia",
            "country_code": "au",
        },
    },
    "region": "Queensland",
    "state": "Queensland",
    "status": "OK",
    "street": "Belcastro Lane",
    "suburb": "Eight Mile Plains",
    "type": "house",
}
