# -*- coding: utf-8 -*-
"""
Geocoder for Trackimo
"""

from datetime import datetime
import requests
import json
import logging
from shapely.geometry import Point, Polygon

_LOGGER = logging.getLogger(__name__)
_SESSION = None
_REFRENCE = "https://github.com/troykelly/python-trackimo"
_CONTACT_EMAIL = None
_USER_AGENT = f"Mozilla/5.0 (compatible; Trackimo; +{_REFRENCE})"
_HOST = "nominatim.openstreetmap.org"
_PROTOCOL = "https"


class __GEO_CACHE(object):
    def __init__(self):
        super().__init__()

    def __cleanup(self):
        pass


def get_session():
    global _SESSION
    if _SESSION:
        return _SESSION
    _SESSION = requests.session()
    _SESSION.headers = {"User-Agent": _USER_AGENT, "Referer": _REFRENCE}
    return _SESSION


async def reverse_geocode(device):
    global __GEO_CACHE

    if not (device.latitude and device.longitude):
        return None

    try:
        device_point = Point(device.latitude, device.longitude)
    except:
        device_point = None

    if not device_point:
        return None

    point_id = " ".join(map(str, device_point.coords[:]))

    from_cache = getattr(__GEO_CACHE, point_id, None)

    if from_cache:
        return from_cache["data"]

    def get_nominatim_reverse():
        session = get_session()
        params = {
            "lat": device_point.x,
            "lon": device_point.y,
            "polygon_geojson": 1,
            "format": "geocodejson",
            "addressdetails": 1,
            "extratags": 1,
            "namedetails": 1,
        }

        if _CONTACT_EMAIL:
            params["email"] = _CONTACT_EMAIL

        response = session.get(f"{_PROTOCOL}://{_HOST}/reverse", params=params)

        status_code = getattr(response, "status_code", None)

        if status_code != 200:
            raise OSMReverseFailed(
                "Unable to fetch from Open Street Map",
                response=response,
            )

        try:
            data = response.json()
        except:
            data = None

        return Address(data)

    try:
        address = await device.loop.run_in_executor(None, get_nominatim_reverse)
    except Exception as err:
        _LOGGER.exception(err)
        raise err

    if not address:
        return None

    setattr(__GEO_CACHE, point_id, {"ts": datetime.now(), "address": address})
    return address


class Address(object):
    def __init__(self, payload={}):
        super().__init__()
        self.__payload = payload
        if "geocoding" in payload:
            if "attribution" in payload["geocoding"]:
                self.__attribution = payload["geocoding"]["attribution"]
            if "query" in payload["geocoding"]:
                self.__query = payload["geocoding"]["query"]
        if "features" in payload and payload["features"][0]:
            feature = payload["features"][0]
            if "properties" in feature and "geocoding" in feature["properties"]:
                geocoding = feature["properties"]["geocoding"]
                if "place_id" in geocoding:
                    self.__place_id = geocoding["place_id"]
                if "osm_type" in geocoding:
                    self.__osm_type = geocoding["osm_type"]
                if "osm_id" in geocoding:
                    self.__osm_id = geocoding["osm_id"]
                if "type" in geocoding:
                    self.__type = geocoding["type"]
                if "accuracy" in geocoding:
                    self.__accuracy = geocoding["accuracy"]
                if "label" in geocoding:
                    self.__label = geocoding["label"]
                if "name" in geocoding:
                    self.__name = geocoding["name"]
                if "country" in geocoding:
                    self.__country = geocoding["country"]
                if "postcode" in geocoding:
                    self.__postcode = geocoding["postcode"]
                if "state" in geocoding:
                    self.__state = geocoding["state"]
                if "city" in geocoding:
                    self.__city = geocoding["city"]
                if "district" in geocoding:
                    self.__district = geocoding["district"]
                if "street" in geocoding:
                    self.__street = geocoding["street"]
            if (
                "geometry" in feature
                and "type" in feature["geometry"]
                and "coordinates" in feature["geometry"]
                and feature["geometry"]["type"].lower() == "polygon"
                and feature["geometry"]["coordinates"][0]
            ):
                self.__polygon = []
                for point_data in feature["geometry"]["coordinates"][0]:
                    if not point_data:
                        continue
                    self.__polygon.append(Point(point_data[0], point_data[1]))

    @property
    def raw(self):
        try:
            return self.__payload
        except AttributeError:
            return None

    @property
    def attribution(self):
        try:
            return self.__attribution
        except AttributeError:
            return None

    @property
    def point(self):
        if not (self.latitude and self.longitude):
            return None
        return Point(self.latitude, self.longitude)

    @property
    def polygon(self):
        if not self.__polygon:
            return None
        return Polygon([[p.x, p.y] for p in self.__polygon])

    @property
    def latitude(self):
        try:
            return float(self.__query.split(",")[0])
        except AttributeError:
            return None

    @property
    def longitude(self):
        try:
            return float(self.__query.split(",")[1])
        except AttributeError:
            return None

    @property
    def place_id(self):
        try:
            return self.__place_id
        except AttributeError:
            return None

    @property
    def osm_type(self):
        try:
            return self.__osm_type
        except AttributeError:
            return None

    @property
    def osm_id(self):
        try:
            return self.__osm_id
        except AttributeError:
            return None

    @property
    def location_type(self):
        try:
            return self.__type
        except AttributeError:
            return None

    @property
    def accuracy(self):
        try:
            return self.__accuracy
        except AttributeError:
            return None

    @property
    def label(self):
        try:
            return self.__label
        except AttributeError:
            return None

    @property
    def name(self):
        try:
            return self.__name
        except AttributeError:
            return None

    @property
    def country(self):
        try:
            return self.__country
        except AttributeError:
            return None

    @property
    def postcode(self):
        try:
            return self.__postcode
        except AttributeError:
            return None

    @property
    def state(self):
        try:
            return self.__state
        except AttributeError:
            return None

    @property
    def city(self):
        try:
            return self.__city
        except AttributeError:
            return None

    @property
    def district(self):
        try:
            return self.__district
        except AttributeError:
            return None

    @property
    def street(self):
        try:
            return self.__street
        except AttributeError:
            return None


class OSMReverseFailed(Exception):
    """Execption raised when fetching from open street map fails

    Attributes:
        message (str): explanation of the error
        response (object): Response object
    """

    def __init__(self, message, response=None):
        super().__init__()
        self.message = message
        self.response = response
