"""
UptimeRobot API integration for the `edwh` tool.
"""

import atexit
import signal
import sys
import typing
from datetime import datetime
from pathlib import Path
from typing import Optional

import edwh
from edwh.helpers import (
    confirm,
    interactive_selected_checkbox_values,
    interactive_selected_radio_value,
)
from edwh.tasks import dc_config, get_hosts_for_service
from invoke import Context, task
from termcolor import cprint

from .dumpers import DEFAULT_PLAINTEXT, DEFAULT_STRUCTURED, SUPPORTED_FORMATS, dumpers
from .helpers import first
from .uptimerobot import MonitorType, UptimeRobotMonitor, uptime_robot


@task(iterable=("monitor_ids",))
def auto_add_to_dashboard(ctx: Context, monitor_ids: list[str | int], dashboard_id: int | str = None):
    """
    Add some monitors to a dashboard.

    Usually done via 'auto_add'.
    """
    if not dashboard_id:
        # auto pick or ask:
        dashboards = uptime_robot.get_psps()
        dashboard_ids = {_["id"]: _["friendly_name"] for _ in dashboards}
        if not dashboard_ids:
            cprint("No dashboards available!", color="red", file=sys.stderr)
            return
        elif len(dashboard_ids) == 1:
            dashboard_id = first(dashboard_ids)
        else:
            dashboard_id = interactive_selected_radio_value(dashboard_ids)

    edit_dashboard(ctx, dashboard_id, add_monitors=monitor_ids)


@task()
def auto_add(ctx: Context, directory: str = None, force: bool = False, quiet: bool = False):
    """
    Find domains based on traefik labels and add them (if desired).

    :param ctx: invoke/fab context
    :param directory: where to look for a docker-compose file? Default is current directory
    :param force: perform auto-add even if UPTIME_AUTOADD_DONE flag is already set
    :param quiet: don't print in color on error (useful for `ew setup`)
    """
    if not uptime_robot.has_api_key:
        # don't even query the user then!
        return

    ran_before = edwh.get_env_value("UPTIME_AUTOADD_DONE", "0") == "1"
    if ran_before and not force:
        cprint(
            "Auto-add flag already set; "
            "Remove 'UPTIME_AUTOADD_DONE' from your .env to allow rerunning, or set --force. "
            "Stopping now.",
            color=None if quiet else "yellow",
            file=sys.stderr,
        )
        return

    directory = directory or "."

    existing_monitors = uptime_robot.get_monitors()
    existing_domains = {_["url"].split("/")[2] for _ in existing_monitors}

    with ctx.cd(directory):
        config = dc_config(ctx)

        domains = set()
        services = config.get("services", {})

        for service in services.values():
            domains.update(get_hosts_for_service(service))

        if not domains:
            cprint(
                "No docker services/domains found; " "Could not auto-add anything.",
                color=None if quiet else "red",
                file=sys.stderr,
            )
            return

        to_add = interactive_selected_checkbox_values(
            list(domains),
            prompt="Which domains would you like to add to Uptime Robot? "
            "(use arrow keys, spacebar, or digit keys, press 'Enter' to finish):",
            selected=existing_domains,
        )

        indices = []
        for url in to_add:
            if url in existing_domains:
                # no need to re-add!
                continue

            if monitor_id := add(ctx, url):
                indices.append(monitor_id)

        if indices and confirm(
            (
                "Do you want to add this monitor to a dashboard? [Yn] "
                if len(indices) == 1
                else "Do you want to add these monitors to a dashboard? [Yn] "
            ),
            default=True,
        ):
            auto_add_to_dashboard(ctx, indices)

    # todo: Path(directory) / .env may be better, but `set_env_value` doesn't work with -H on remote servers at all yet
    edwh.set_env_value(Path(".env"), "UPTIME_AUTOADD_DONE", "1")


def output_statuses_plaintext(monitors: typing.Iterable[UptimeRobotMonitor]) -> None:
    for monitor in monitors:
        status = uptime_robot.format_status(monitor["status"])
        color = uptime_robot.format_status_color(monitor["status"])

        cprint(f"- {monitor['url']}: {status}", color=color)


def output_statuses_structured(
    monitors: typing.Iterable[UptimeRobotMonitor], fmt: SUPPORTED_FORMATS = DEFAULT_STRUCTURED
) -> None:
    statuses = {}
    for monitor in monitors:
        statuses[monitor["url"]] = uptime_robot.format_status(monitor["status"])

    dumpers[fmt](
        {
            "statuses": statuses,
        }
    )


def output_statuses(monitors: typing.Iterable[UptimeRobotMonitor], fmt: SUPPORTED_FORMATS) -> None:
    match fmt:
        case "json" | "yml" | "yaml":
            output_statuses_structured(monitors, fmt)
        case _:
            output_statuses_plaintext(monitors)


@task()
def status(_: Context, url: str, fmt: SUPPORTED_FORMATS = DEFAULT_PLAINTEXT) -> None:
    """
    Show a specific monitor by (partial) url or label.

    :param url: required positional argument of the URL to show the status for
    :param fmt: Output format (plaintext, json or yaml)
    """
    monitors = uptime_robot.get_monitors(url)
    if not monitors:
        cprint("No monitor found!", color="red", file=sys.stderr)
        return

    output_statuses(monitors, fmt)


@task(name="monitors")
def monitors_verbose(_: Context, search: str = "", fmt: SUPPORTED_FORMATS = DEFAULT_STRUCTURED) -> None:
    """
    Show all monitors full data as dict.
    You can optionally add a search term, which will look in the URL and label.

    :param search: (partial) URL or monitor name to filter by
    :param fmt: output format (json or yaml)
    """
    monitors = uptime_robot.get_monitors(search)
    dumpers[fmt]({"monitors": monitors})


@task(name="list")
def list_statuses(_: Context, search: str = "", fmt: SUPPORTED_FORMATS = DEFAULT_PLAINTEXT) -> None:
    """
    Show the status for each monitor.

    :param search: (partial) URL or monitor name to filter by
    :param fmt: text (default), json or yaml
    """
    monitors = uptime_robot.get_monitors(search)

    output_statuses(monitors, fmt)


@task(aliases=("up",))
def list_up(_: Context, strict: bool = False, fmt: SUPPORTED_FORMATS = DEFAULT_PLAINTEXT) -> None:
    """
    List monitors that are up (probably).

    :param strict: If strict is True, only status 2 is allowed
    :param fmt: output format (default is plaintext)
    """
    min_status = 2 if strict else 0
    max_status = 3

    monitors = uptime_robot.get_monitors()
    monitors = [_ for _ in monitors if min_status <= _["status"] < max_status]

    output_statuses(monitors, fmt)


@task(aliases=("down",))
def list_down(_: Context, strict: bool = False, fmt: SUPPORTED_FORMATS = DEFAULT_PLAINTEXT) -> None:
    """
    List monitors that are down (probably).

    :param strict: If strict is True, 'seems down' is ignored
    :param fmt: output format (default is plaintext)
    """
    min_status = 9 if strict else 8

    monitors = uptime_robot.get_monitors()
    monitors = [_ for _ in monitors if _["status"] >= min_status]

    output_statuses(monitors, fmt)


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
def add(_: Context, url: str, friendly_name: str = "") -> int | None:
    """
    Create a new monitor.
    Requires a positional argument 'url' and an optional --friendly-name label

    :param url: Which domain name to add
    :param friendly_name: Human-readable label (defaults to part of URL)
    """
    url, domain = normalize_url(url)

    if existing := uptime_robot.get_monitors(domain):
        cprint("A similar domain was already added:", color="yellow", file=sys.stderr)
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
        cprint("No monitor was added", color="red")
    else:
        cprint(f"Monitor '{friendly_name}' was added: {monitor_id}", color="green")

    return monitor_id


def select_monitor(url: str) -> UptimeRobotMonitor | None:
    """
    Interactively select a monitor by url.

    :param url: Which domain name to select
    :return: Selected monitor
    """
    monitors = uptime_robot.get_monitors(url)
    if not monitors:
        cprint(f"No such monitor could be found {url}", color="red")
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
        cprint(f"Monitor {monitor['friendly_name']} removed!", color="green")
    else:
        cprint(f"Monitor {monitor['friendly_name']} could not be deleted.", color="green")


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
        "monitor_type": monitor.get("type", MonitorType.HTTP),  # todo: support more types?
        # ...
    }

    if uptime_robot.edit_monitor(monitor_id, new_data):
        cprint(f"Monitor {monitor['friendly_name']} updated!", color="green")
    else:
        cprint(f"Monitor {monitor['friendly_name']} could not be updated.", color="red")


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
        cprint(f"Monitor {monitor['friendly_name']} reset!", color="green")
    else:
        cprint(f"Monitor {monitor['friendly_name']} could not be reset.", color="red")


@task()
def account(_: Context, fmt: SUPPORTED_FORMATS = DEFAULT_STRUCTURED) -> None:
    """
    Show information about the account related to the current API key.

    :param fmt: Output format (plaintext, json or yaml)
    """
    data = {"account": uptime_robot.get_account_details()}
    dumpers[fmt](data)


@task()
def dashboards(_: Context, fmt: SUPPORTED_FORMATS = DEFAULT_STRUCTURED):
    """
    Show all dashboards.

    :param fmt: Output format (plaintext, json or yaml)
    """
    data = {"dashboards": uptime_robot.get_psps()}
    dumpers[fmt](data)


@task()
def dashboard(_: Context, dashboard_id: str, fmt: SUPPORTED_FORMATS = DEFAULT_STRUCTURED):
    """
    Show a specific dashboard by dashboard_id.

    :param dashboard_id: id of the dashboard you want to show.
    :param fmt: Output format (plaintext, json or yaml)
    """
    dashboard_info = uptime_robot.get_psp(dashboard_id)
    data = {"dashboard": dashboard_info}
    if dashboard_info:
        # resolve monitor names
        dashboard_info["monitors"] = uptime_robot.get_monitors(monitor_ids=dashboard_info["monitors"])

    dumpers[fmt](data)


@task(iterable=("add_monitors",))
def edit_dashboard(
    _: Context, dashboard_id: int, friendly_name: str = None, add_monitors: typing.Iterable[int | str] = ()
):
    """
    Edit a dashboard.

    :param dashboard_id: id of the dashboard you want to edit.
    :param friendly_name: Human-readable label (defaults to part of URL)
    :param add_monitors: id of the monitor you want to add to the dashboard.
    """
    dashboard_info = uptime_robot.get_psp(dashboard_id)
    if not dashboard_info:
        print("Invalid dashboard id.", file=sys.stderr)
        return

    friendly_name = friendly_name or dashboard_info["friendly_name"]

    monitors = uptime_robot.get_monitors()

    available = {int(_["id"]): _["friendly_name"] for _ in monitors}
    selected = dashboard_info["monitors"] + [int(_) for _ in add_monitors]

    new_monitors = interactive_selected_checkbox_values(
        available,
        f"Which monitors should be shown on the dashboard '{friendly_name}'?",
        selected=selected,
    )

    if sorted(new_monitors) == sorted(dashboard_info["monitors"]):
        cprint("List of monitors is the same as before, exiting.", color="yellow", file=sys.stderr)
        return

    dashboard_info["friendly_name"] = friendly_name
    dashboard_info["monitors"] = new_monitors

    if uptime_robot.edit_psp(
        dashboard_id,
        **dashboard_info,
    ):
        cprint(f"Dashboard {dashboard_info['friendly_name']} updated!", color="green")
    else:
        cprint(f"Dashboard {dashboard_info['friendly_name']} could not be updated.", color="red")


def defer(callback: typing.Callable[[], None]):
    """
    When using atexit, you also have to listen to SIGTERM to ensure atexit runs.
    This sigterm doesn't really have to do anything though!

    Returns a function you can call to 'undefer'
    """

    atexit.register(callback)
    signal.signal(signal.SIGTERM, lambda *_: exit())

    return lambda: atexit.unregister(callback)


@task
def maintenance(_: Context, friendly_name: str, duration: int = 60):
    """
    Start a new maintenance window.

    Args:
        _: invoke Context
        friendly_name: descriptive name for the window (e.g. the version you're releasing)
        duration: time in minutes the window will stay if you don't end it manually

    usage:
    ew uptime.maintenance <friendly_name> <duration>
    """
    # 1. make window
    window_id = uptime_robot.new_maintenance_window(
        friendly_name, type="once", start_time=datetime.now(), duration=int(duration)
    )

    # 2. on kill/done remove window

    def cleanup(*_):
        cprint("Removing maintenance window", color="blue")
        if uptime_robot.delete_maintenance_window(window_id):
            cprint("Removed maintenance window!", color="green")
        else:
            cprint("Something went wrong removing the window...", color="red")

    cancel = defer(cleanup)

    # 3 wait for user to do maintenance
    try:
        input(
            "Press enter to end the maintenance window. Press Ctrl-D to exit but keep the maintenance window open for the specified duration. "
        )
    except EOFError:
        # ctrl-d pressed, keep window open:
        cancel()
        print("Not removing maintenance window")
        exit(0)

    # atexit/signal runs here

@task
def get_maintenance(_: Context):
    """Show all maintenance windows."""
    print("Active maintenance windows:", uptime_robot.get_m_windows())

@task
def unmaintenance(_: Context, window: int | str):
    """
    Remove a specific maintenance window by friendly_name or window_id.

    :param window: window_id or friendly_name of the maintenance window you want to remove.

    usage:
    ew uptime.unmaintenance <friendly_name>
    or: ew uptime.unmaintenance <window_id>
    """
    window_data = uptime_robot.get_m_windows()  # Get all maintenance windows.
    if window_data["mwindows"]: # Is the list in "mwindows" truthy / not empty
        for active_maintenance_window in window_data.get("mwindows"): # loop through the active maintenance windows in window_data.
            try:
                window_id = int(window)  # If the window is castable into an int window is A window_id
                if active_maintenance_window["id"] == window_id:  # If the id matches the user input.
                    removal_status = uptime_robot.delete_maintenance_window(window_id=window_id)  # Window removal.
                    print("Removed", window) if removal_status else print("Removal of", window, "failed.")
                else:
                    print("Maintenance window not removed, '" + window + "' could not be found.")
            except ValueError:
                if active_maintenance_window["friendly_name"] == window:  # If the friendly name matches the user input.
                    removal_status = uptime_robot.delete_maintenance_window(window_id=active_maintenance_window["id"])
                    print("Removed", window) if removal_status else print("Removal of '" + window + "' failed.")
                else:
                    print("Maintenance window not removed, '" + window + "' could not be found.")
    else:
        print("No active maintenance windows found.")

@task
def unmaintenance_all(_: Context):
    """Remove all maintenance windows."""
    yes_set = {"y", "yes"}
    verification = input("This will remove all maintenance windows. Are you sure? (y/N)").lower()
    print("Removed", uptime_robot.clean_maintenance_windows(), "one-time maintenance windows.")\
        if verification in yes_set else print("Removal aborted.")


