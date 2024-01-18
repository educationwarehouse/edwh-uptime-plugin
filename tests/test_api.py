import warnings

import edwh
import pytest

from src.edwh_uptime_plugin.uptimerobot import UptimeRobot, UptimeRobotException
from src.edwh_uptime_plugin.uptimerobot import uptime_robot as illegal

# if the name registered in the account does not match, exit immediately because that's not good!!!
REQUIRED_NAME = edwh.get_env_value("REQUIRED_NAME", "EDWH-pytest")

# global safety measure:
pytest.allowed_apikey = None


# FIXME: Note - Free Plans rate limits: 10 requests/minute

def new_safe_uptimerobot():
    instance = UptimeRobot()

    account = instance.get_account_details()
    if account.get("firstname", "") != REQUIRED_NAME:
        warnings.warn(
            f"!!! INVALID API KEY, EXIT NOW TO PREVENT UPDATING ACTUAL DATA !!! "
            f"({account.get('firstname', '')} != {REQUIRED_NAME})",
            category=UserWarning,
        )
        exit(1)

    pytest.allowed_apikey = instance._api_key
    return instance


@pytest.fixture
def uptime_robot():
    """
    Get a guaranteed-safe UptimeRobot instance (= test account only) to prevent horrors
    """
    illegal._api_key = "<DON'T USE ME>"

    if pytest.allowed_apikey:
        instance = UptimeRobot()
        instance._api_key = pytest.allowed_apikey
        yield instance

        return

    # else: first validate the API key:
    yield new_safe_uptimerobot()


@pytest.fixture()
def clean_uptimerobot(uptime_robot):
    # remove all monitors
    monitors = uptime_robot.get_monitors()
    for monitor in monitors:
        uptime_robot.delete_monitor(monitor['id'])

    assert not uptime_robot.get_monitors(), "Some monitors were not removed - can not continue test!"


def test_000_prevent_horrors(uptime_robot):
    # check AGAIN just to be safe
    assert uptime_robot.get_account_details().get("firstname") == REQUIRED_NAME


def test_001_prevent_horrors():
    # check the original instance to make sure we're not allowed to mess anything up:
    with pytest.raises(UptimeRobotException):
        assert not illegal.get_account_details()


# continue testing on proper test instance:
def test_simple(uptime_robot, clean_uptimerobot):
    # add one + check
    idx = uptime_robot.new_monitor("Monitor 1", "https://first.monitor/")
    assert idx
    monitor = uptime_robot.get_monitor(idx)

    assert uptime_robot.get_monitor(str(idx)) == uptime_robot.get_monitor(int(idx))

    assert monitor

    assert monitor['friendly_name'] == "Monitor 1"

    assert len(uptime_robot.get_monitors()) == 1
    uptime_robot.delete_monitor(monitor['monitor_id'])

    assert len(uptime_robot.get_monitors()) == 0
