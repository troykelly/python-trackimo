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
        self.validateConfig()

    def validateConfig(self):
        if not 'trackimo' in self._config:
            self._config['trackimo'] = {}
        if not 'username' in self._config['trackimo']:
            self._config['trackimo']['username'] = None
        if not 'password' in self._config['trackimo']:
            self._config['trackimo']['password'] = None
        if not 'update_frequency' in self._config['trackimo']:
            self._config['trackimo']['update_frequency'] = 1

        if not self._config['trackimo']['username'] and not self._config['trackimo']['password']:
            raise ConfigError(
                'Must supply both a username and password for the trackimo service')
        elif not self._config['trackimo']['password']:
            raise ConfigError(
                'Must supply a password for the trackimo service')
        elif not self._config['trackimo']['username']:
            raise ConfigError(
                'Must supply a username for the trackimo service')

        if not 'api' in self._config:
            self._config['api'] = {}
        if not 'protocol' in self._config['api']:
            self._config['api']['protocol'] = 'https'
        if not 'host' in self._config['api']:
            self._config['api']['host'] = 'app.trackimo.com'
        if not 'version' in self._config['api']:
            self._config['api']['version'] = '3'
        if not 'client_id' in self._config['api']:
            self._config['api']['client_id'] = '943f9b0f-73c8-4435-8801-0260db687f05'
        if not 'client_secret' in self._config['api']:
            self._config['api']['client_secret'] = '96ca64b0ae5f7005fd18387a28019615'
        if not 'endpoint' in self._config['api']:
            self._config['api']['endpoint'] = self._config['api']['protocol'] + '://' + \
                self._config['api']['host'] + '/api/v' + \
                self._config['api']['version'] + '/'
        if not 'endpointInternal' in self._config['api']:
            self._config['api']['endpointInternal'] = self._config['api']['protocol'] + \
                '://' + self._config['api']['host'] + '/api/internal/v1/'

    def connect(self):
        self.getToken()
        self.getUser()
        self.getDevices()

    def addListener(self, listenerFunction):
        self._listeners.append(listenerFunction)

    async def getToken(self):
        taskToken = self.loop.create_task(self._getToken())
        await taskToken

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

    async def getUser(self):
        taskUser = self.loop.create_task(self._getUser())
        await taskUser

    @asyncio.coroutine
    def _getUser(self):
        headers = {'Authorization': 'Bearer ' + self._token['access_token']}
        r = requests.get(self._config['api']
                         ['endpoint'] + 'user', headers=headers)
        user_response = r.json()
        if 'account_id' not in user_response:
            raise ConfigError('No user data received')

        self._user = user_response

    async def getDevices(self):
        taskDevices = self.loop.create_task(self._getDevices())
        await taskDevices

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
