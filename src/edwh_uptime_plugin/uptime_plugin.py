"""
UptimeRobot API integration for the `edwh` tool.
"""

import json
from typing import Optional

import edwh
from invoke import Context, task

from .uptimerobot import MonitorType, UptimeRobotMonitor, uptime_robot


@task()
def status(_: Context, url: str) -> None:
    """
    Show a specific monitor by (partial) url or label.

    :param url: required positional argument of the URL to show the status for
    """
    monitors = uptime_robot.get_monitors(url)
    if not monitors:
        print("No monitor found!")
        return

    for monitor in monitors:
        print(f"- {monitor['url']}:", uptime_robot.format_status(monitor["status"]))


@task(name="monitors")
def monitors_verbose(_: Context, search: str = "") -> None:
    """
    Show all monitors full data as dict.
    You can optionally add a search term, which will look in the URL and label.

    :param search: (partial) URL or monitor name to filter by
    """
    print(json.dumps(uptime_robot.get_monitors(search), indent=2))


@task(name="list")
def list_statuses(_: Context, search: str = "") -> None:
    """
    Show the status for each monitor.

    :param search: (partial) URL or monitor name to filter by
    """
    for monitor in uptime_robot.get_monitors(search):
        print(f"- {monitor['url']}:", uptime_robot.format_status(monitor["status"]))


@task()
def up(_: Context, strict: bool = False) -> None:
    """
    List monitors that are up (probably).

    :param strict: If strict is True, only status 2 is allowed
    """
    min_status = 2 if strict else 0
    max_status = 3

    monitors = uptime_robot.get_monitors()
    monitors = [_ for _ in monitors if min_status <= _["status"] < max_status]

    for monitor in monitors:
        print(f"- {monitor['url']}:", uptime_robot.format_status(monitor["status"]))


@task()
def down(_: Context, strict: bool = False) -> None:
    """
    List monitors that are down (probably).

    :param strict: If strict is True, 'seems down' is ignored
    """
    min_status = 9 if strict else 8

    monitors = uptime_robot.get_monitors()
    monitors = [_ for _ in monitors if _["status"] >= min_status]

    for monitor in monitors:
        print(f"- {monitor['url']}:", uptime_robot.format_status(monitor["status"]))


def extract_friendly_name(url: str) -> str:
    name = url.split("/")[2]

    return name.removesuffix(".edwh.nl").removesuffix(".meteddie.nl").removeprefix("www.")


def normalize_url(url: str) -> tuple[str, str]:
    if not url.startswith(("https://", "http://")):
        if "://" in url:
            protocol = url.split("://")[0]
            raise ValueError(f"protocol {protocol} not supported, please use http(s)://")
        url = f"https://{url}"

    # search for existing and confirm:
    domain = url.split("/")[2]

    return url, domain


@task(aliases=("create",))
def add(_: Context, url: str, friendly_name: str = "") -> None:
    """
    Create a new monitor.
    Requires a positional argument 'url' and an optional --friendly-name label

    :param url: Which domain name to add
    :param friendly_name: Human-readable label (defaults to part of URL)
    """
    url, domain = normalize_url(url)

    if existing := uptime_robot.get_monitors(domain):
        print("A similar domain was already added:")
        for monitor in existing:
            print(monitor["friendly_name"], monitor["url"])
        if not edwh.confirm("Are you sure you want to continue? [yN]", default=False):
            return

    friendly_name = friendly_name or extract_friendly_name(url)

    monitor_id = uptime_robot.new_monitor(
        friendly_name,
        url,
    )

    if not monitor_id:
        print("No monitor was added")
    else:
        print(f"Monitor '{friendly_name}' was added: {monitor_id}")


def select_monitor(url: str) -> UptimeRobotMonitor | None:
    """
    Interactively select a monitor by url.

    :param url: Which domain name to select
    :return: Selected monitor
    """
    monitors = uptime_robot.get_monitors(url)
    if not monitors:
        print(f"No such monitor could be found {url}")
        return None
    if len(monitors) > 1:
        print(f"Ambiguous url {url} could mean:")
        for idx, monitor in enumerate(monitors):
            print(idx + 1, monitor["friendly_name"], monitor["url"])

        print("0", "Exit")

        _which_one = input("Which monitor would you like to select? ")
        if not _which_one.isdigit():
            print(f"Invalid number {_which_one}!")
            return None

        which_one = int(_which_one)
        if which_one > len(monitors):
            print(f"Invalid selection {which_one}!")
            return None

        elif which_one == 0:
            return None
        else:
            # zero-index:
            which_one -= 1

    else:
        which_one = 0

    return monitors[which_one]


@task(aliases=("delete",))
def remove(_: Context, url: str) -> None:
    """
    Remove a specific monitor by url.

    :param url: Which domain name to remove
    """
    if not (monitor := select_monitor(url)):
        return

    monitor_id = monitor["id"]

    if uptime_robot.delete_monitor(monitor_id):
        print(f"Monitor {monitor['friendly_name']} removed!")
    else:
        print(f"Monitor {monitor['friendly_name']} could not be deleted.")


@task(aliases=("update",))
def edit(_: Context, url: str, friendly_name: Optional[str] = None) -> None:
    """
    Edit a specific monitor by url.

    :param url: Which domain name to edit
    :param friendly_name: new human-readable label
    """
    monitor = select_monitor(url)
    if monitor is None:
        return

    monitor_id = monitor["id"]

    url, _domain = normalize_url(url)

    # Here you can define the new data for the monitor
    new_data = {
        "url": url,
        "friendly_name": friendly_name or monitor.get("friendly_name", ""),
        "monitor_type": monitor.get("type", MonitorType.HTTP),  # todo: support more?
        # ...
    }

    if uptime_robot.edit_monitor(monitor_id, new_data):
        print(f"Monitor {monitor['friendly_name']} updated!")
    else:
        print(f"Monitor {monitor['friendly_name']} could not be updated.")


@task()
def reset(_: Context, url: str) -> None:
    """
    Reset a specific monitor by url.

    :param url: Which domain name to reset
    """
    if not (monitor := select_monitor(url)):
        return

    monitor_id = monitor["id"]

    if uptime_robot.reset_monitor(monitor_id):
        print(f"Monitor {monitor['friendly_name']} reset!")
    else:
        print(f"Monitor {monitor['friendly_name']} could not be reset.")


@task()
def account(_: Context) -> None:
    """
    Show information about the acccount related to the current API key.
    """

    print(json.dumps(uptime_robot.get_account_details(), indent=2))
