#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import logging
import asyncio
import json
import time

LOG = logging.getLogger(__name__)


class TokenError(Exception):
    def __init__(self, message):
        self.message = message


class ConfigError(Exception):
    def __init__(self, message):
        self.message = message


class Trackimo:

    def __init__(self, config, loop=None):
        self.loop = loop if loop else asyncio.get_event_loop()
        self._config = config
        self._token = {}
        self._user = {}
        self._devices = {}
        self._locations = {}
        self._listeners = []

    def connect(self):
        self.getToken()
        self.getUser()
        self.getDevices()

    def addListener(self, listenerFunction):
        self._listeners.append(listenerFunction)

    def getToken(self):
        self.loop.run_until_complete(self._getToken())

    @asyncio.coroutine
    def _getToken(self):
        username = self._config['trackimo']['username']
        password = self._config['trackimo']['password']
        api = self._config['api']
        LOG.debug("Getting Token for %s" % username)
        LOG.debug("Using Login API Endpoint: %s" % api['endpointInternal'])
        LOG.debug("Using API Endpoint: %s" % api['endpoint'])

        # Create a session to manage the login
        session = requests.session()
        jar = requests.cookies.RequestsCookieJar()

        # Get the session cookie
        payload = {"username": username,
                   "password": password, "remember_me": True}
        r = session.post(api['endpointInternal'] + 'user/login',
                         json=payload, allow_redirects=False, cookies=jar)

        if 'JSESSIONID' not in session.cookies:
            LOG.debug(session.cookies)
            raise ConfigError('No session identity received')

        # Get a token code
        payload = {
            'client_id': api['client_id'],
            'scope': 'locations,notifications,devices,accounts,settings,geozones',
            'redirect_uri': 'https://app.trackimo.com/api/internal/v1/oauth_redirect',
            'response_type': 'code'
        }
        r = session.get(api['endpoint'] + 'oauth2/auth',
                        params=payload, cookies=jar)
        code_response = r.json()
        if 'code' not in code_response:
            raise ConfigError('No token code received')

        # Swap token code for token
        payload = {
            "client_id": api['client_id'],
            "client_secret": api['client_secret'],
            "code": code_response['code']
        }
        r = session.post(api['endpoint'] + 'oauth2/token',
                         json=payload, allow_redirects=False, cookies=jar)

        token_response = r.json()
        if 'access_token' not in token_response:
            raise ConfigError('No token received')

        self._token = token_response

    def getUser(self):
        self.loop.run_until_complete(self._getUser())

    @asyncio.coroutine
    def _getUser(self):
        headers = {'Authorization': 'Bearer ' + self._token['access_token']}
        r = requests.get(self._config['api']
                         ['endpoint'] + 'user', headers=headers)
        user_response = r.json()
        if 'account_id' not in user_response:
            raise ConfigError('No user data received')

        self._user = user_response

    def getDevices(self):
        self.loop.run_until_complete(self._getDevices())

    @asyncio.coroutine
    def _getDevices(self):
        if not 'account_id' in self._user:
            return
        headers = {'Authorization': 'Bearer ' + self._token['access_token']}
        r = requests.get(self._config['api']['endpoint'] + 'accounts/' + str(
            self._user['account_id']) + '/devices', headers=headers)
        devices_response = r.json()
        for device in devices_response:
            self._devices[device['deviceId']] = device['deviceName']

    def updateLocations(self, updateDelay=None):
        self.loop.create_task(self._updateLocations(updateDelay))

    @asyncio.coroutine
    def _updateLocations(self, updateDelay=None):
        if not 'account_id' in self._user:
            return
        headers = {'Authorization': 'Bearer ' + self._token['access_token']}
        r = requests.get(self._config['api']['endpoint'] + 'accounts/' + str(
            self._user['account_id']) + '/locations', headers=headers)
        locations_response = r.json()
        ts = time.time()
        locations = {}
        for device in locations_response:
            if 'device_id' in device and device['device_id'] in self._devices:
                locations[device['device_id']] = device
                locations[device['device_id']
                          ]['name'] = self._devices[device['device_id']]
                locations[device['device_id']]['ts'] = ts
        self._locations = locations
        self.loop.create_task(self._updateListeners(locations, ts))
        if updateDelay is not None:
            LOG.debug("Waiting for %d seconds..." % updateDelay)
            self.loop.call_later(
                updateDelay, self.updateLocations, updateDelay)

    def monitor(self):
        self.loop.create_task(self._monitor())

    @asyncio.coroutine
    def _monitor(self):
        if not self._config['trackimo']['update_frequency'] > 0:
            return
        delay = self._config['trackimo']['update_frequency'] * 60
        self.loop.create_task(self._updateLocations(updateDelay=delay))

    @asyncio.coroutine
    def _updateListeners(self, locations=None, ts=None):
        for listener in self._listeners:
            self.loop.create_task(listener(locations=locations, ts=ts))