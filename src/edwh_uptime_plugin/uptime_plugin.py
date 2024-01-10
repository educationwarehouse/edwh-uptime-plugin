import json

import edwh
from invoke import task

from .uptimerobot import uptime_robot


@task()
def status(_, url: str):
    """
    Show a specific monitor

    :type _: invoke.Context
    :param url: required positional argument of the URL to show the status for
    """
    monitors = uptime_robot.get_monitors(url)
    if not monitors:
        print("No monitor found!")
        return

    for monitor in monitors:
        print(f"- {monitor['url']}:", uptime_robot.format_status(monitor["status"]))


@task(name="monitors")
def monitors_verbose(_, search: str = ""):
    """
    Show all monitors (with an optional search), full data as dict.

    :type _: invoke.Context
    :param search: (partial) URL or monitor name to filter by
    """
    print(json.dumps(uptime_robot.get_monitors(search), indent=2))


@task(name="list")
def list_statuses(_, search: str = ""):
    """
    Show the status for each monitor.

    :type _: invoke.Context
    :param search: (partial) URL or monitor name to filter by
    """
    for monitor in uptime_robot.get_monitors(search):
        print(f"- {monitor['url']}:", uptime_robot.format_status(monitor["status"]))


@task()
def up(_, strict=False):
    """
    List all monitors that are (probably) down.

    :type _: invoke.Context
    :param strict: If strict is True, only status 2 is allowed
    """
    min_status = 2 if strict else 0
    max_status = 3

    monitors = uptime_robot.get_monitors()
    monitors = [_ for _ in monitors if min_status <= _["status"] < max_status]

    for monitor in monitors:
        print(f"- {monitor['url']}:", uptime_robot.format_status(monitor["status"]))


@task()
def down(_, strict=False):
    """
    List all monitors that are (probably) down.

    :type _: invoke.Context
    :param strict: If strict is True, 'seems down' is ignored
    """
    min_status = 9 if strict else 8

    monitors = uptime_robot.get_monitors()
    monitors = [_ for _ in monitors if _["status"] >= min_status]

    for monitor in monitors:
        print(f"- {monitor['url']}:", uptime_robot.format_status(monitor["status"]))


def extract_friendly_name(url: str):
    name = url.split("/")[2]

    return name.removesuffix(".edwh.nl").removesuffix(".meteddie.nl").removeprefix("www.")


@task()
def add(_, url: str, friendly_name: str = ""):
    """
    :type _: invoke.Context
    :param url: Which domain name to add
    :param friendly_name: Human-readable label (defaults to part of URL)
    """
    if not url.startswith(("https://", "http://")):
        if "://" in url:
            protocol = url.split("://")[0]
            print(f"protocol {protocol} not supported, please use http(s)://")
            return
        url = f"https://{url}"

    # search for existing and confirm:
    domain = url.split("/")[2]
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


@task()
def remove(_, url: str):
    """
    :type _: invoke.Context
    :param url: Which domain name to remove
    """
    monitors = uptime_robot.get_monitors(url)
    if not monitors:
        print(f"No such monitor could be found {url}")
        return
    if len(monitors) > 1:
        print(f"Ambiguous url {url} could mean:")
        for idx, monitor in enumerate(monitors):
            print(idx + 1, monitor["friendly_name"], monitor["url"])

        print("0", "Exit")

        _which_one = input("Which monitor would you like to remove? ")
        if not _which_one.isdigit():
            print(f"Invalid number {_which_one}!")
            return

        which_one = int(_which_one)
        if which_one > len(monitors):
            print(f"Invalid selection {which_one}!")
            return

        elif which_one == 0:
            return
        else:
            # zero-index:
            which_one -= 1

    else:
        which_one = 0

    monitor = monitors[which_one]

    monitor_id = monitor["id"]

    if uptime_robot.delete_monitor(monitor_id):
        print(f"Monitor {url} removed!")
    else:
        print(f"Monitor {url} could not be deleted.")


@task()
def account(_):
    """
    :type _: invoke.Context
    """

    print(json.dumps(uptime_robot.get_account_details(), indent=2))
