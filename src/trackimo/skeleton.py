# -*- coding: utf-8 -*-
"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
[options.entry_points] section in setup.cfg:

    console_scripts =
         fibonacci = trackimo.skeleton:run

Then run `python setup.py install` which will install the command `fibonacci`
inside your current environment.
Besides console scripts, the header (i.e. until _logger...) of this file can
also be used as template for Python modules.

Note: This skeleton file can be safely removed if not needed!
"""

import argparse
import sys
import logging
import asyncio

from trackimo import __version__
from trackimo import Trackimo

__author__ = "Troy Kelly"
__copyright__ = "Troy Kelly"
__license__ = "mit"

_logger = logging.getLogger(__name__)


async def track(devices=None, interval=60):
    """Track all device

    Args:
      devices (object): The device object
      interval (int): Seconds between updates (0 for one and exit)

    Returns:
      object: The device location information
    """
    for device in devices:
        location = await devices[device].refresh()
        _logger.debug("%s: %s", devices[device].name, location)
    return {}

def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Demonstration of Lat/Lon tracking of a device")
    parser.add_argument(
        "--version",
        action="version",
        version="trackimo {ver}".format(ver=__version__))
    parser.add_argument(
        dest="id",
        help="The trackimo device id",
        type=int,
        metavar="DEVICEID")
    parser.add_argument(
        "-i",
        "--interval",
        dest="interval",
        help="The tracking interval in seconds",
        type=int,
        metavar="INT")
    parser.add_argument(
        "-u",
        "--username",
        dest="username",
        help="Trackimo app username",
        type=str,
        metavar="STR")
    parser.add_argument(
        "-p",
        "--password",
        dest="password",
        help="Trackimo app password",
        type=str,
        metavar="STR")
    parser.add_argument(
        "-a",
        "--appid",
        dest="app_id",
        help="Trackimo API App ID",
        type=str,
        metavar="STR")
    parser.add_argument(
        "-s",
        "--appsecret",
        dest="app_secret",
        help="Trackimo API App Secret",
        type=str,
        metavar="STR")
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO)
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG)
    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


async def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    _logger.debug("Logging in...")
    api = Trackimo()
    await api.login(args.app_id, args.app_secret, args.username, args.password)
    _logger.debug("Starting tracking...")
    await track(api.devices)
    _logger.info("Script ends here")


def run():
    """Entry point for console_scripts
    """
    task = main(sys.argv[1:])
    res = asyncio.get_event_loop().run_until_complete( task )


if __name__ == "__main__":
    run()
