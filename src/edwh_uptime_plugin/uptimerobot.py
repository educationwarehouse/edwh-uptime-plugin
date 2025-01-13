import datetime as dt
import enum
import json
import sys
import typing
import warnings
from typing import Any, Optional

import edwh
import requests
from edwh import check_env
from typing_extensions import NotRequired, Required
from yayarl import URL

if typing.TYPE_CHECKING:
    from termcolor._types import Color

AnyDict: typing.TypeAlias = dict[str, Any]


class UptimeRobotException(Exception):
    status_code: int
    message: str
    response: requests.Response
    extra: Optional[Any]

    def __init__(self, response: requests.Response, extra: Any = None):
        self.response = response
        self.status_code = response.status_code
        self.message = response.text
        self.extra = extra


class UptimeRobotRatelimit(UptimeRobotException): ...


class UptimeRobotErrorResponse(typing.TypedDict):
    type: str
    message: str

    parameter_name: NotRequired[str]
    passed_value: NotRequired[str]


class UptimeRobotPagination(typing.TypedDict):
    offset: int
    limit: int
    total: int


class UptimeRobotAccount(typing.TypedDict, total=False):
    email: str
    user_id: int
    firstname: str
    # ...


class UptimeRobotDashboard(typing.TypedDict, total=False):
    id: int
    friendly_name: str
    monitors: list[int]
    sort: int
    status: int
    standard_url: str
    custom_url: str


class UptimeRobotMaintenanceWindow(typing.TypedDict, total=False):
    id: int
    type: str
    duration: int
    status: int
    friendly_name: str


class UptimeRobotResponse(typing.TypedDict, total=False):
    stat: typing.Literal["ok", "fail"]
    error: NotRequired[UptimeRobotErrorResponse]
    pagination: NotRequired[UptimeRobotPagination]
    # actual data differs per endpoint:
    account: NotRequired[UptimeRobotAccount]

    monitor: NotRequired["UptimeRobotMonitor"]
    monitors: NotRequired[list["UptimeRobotMonitor"]]

    psp: NotRequired[UptimeRobotDashboard]
    psps: NotRequired[list[UptimeRobotDashboard]]

    mwindow: NotRequired[UptimeRobotMaintenanceWindow]
    mwindows: NotRequired[list[UptimeRobotMaintenanceWindow]]


class UptimeRobotMonitor(typing.TypedDict, total=False):
    id: Required[int]

    # may or may not be there:
    friendly_name: NotRequired[str]
    url: NotRequired[str]
    type: NotRequired[int]
    sub_type: NotRequired[str]
    keyword_type: NotRequired[Optional[str]]
    keyword_case_type: NotRequired[Optional[str]]
    keyword_value: NotRequired[str]
    http_username: NotRequired[str]
    http_password: NotRequired[str]
    port: NotRequired[str]
    interval: NotRequired[int]
    timeout: NotRequired[int]
    status: NotRequired[int]
    create_datetime: NotRequired[int]


class MonitorType(enum.Enum):
    HTTP = 1
    KEYWORD = 2
    PING = 3
    PORT = 4
    HEARTBEAT = 5


class UptimeRobot:
    base = URL("https://api.uptimerobot.com/v2/")

    _api_key: str = ""  # cached version from .env
    _verbose: bool = False

    @property
    def api_key(self) -> str:
        if not self._api_key:
            self._api_key = check_env(
                "UPTIMEROBOT_APIKEY",
                default="",
                comment="The API key used to manage UptimeRobot monitors.",
            )

        return self._api_key

    @api_key.setter
    def api_key(self, key: str) -> None:
        self._api_key = key

    @property
    def has_api_key(self) -> bool:
        result = bool(self.api_key)
        if not result:
            warnings.warn("Uptime Robot API key empty - can't perform requests!")
        return result

    def set_verbosity(self, verbose: bool = None) -> None:
        if verbose is None:
            verbose = edwh.get_env_value("IS_DEBUG", "0") == "1"

        self._verbose = verbose

    def _log(self, *args: Any) -> None:
        if not self._verbose:
            return

        print(*args, file=sys.stderr)

    def _post(self, endpoint: str, **input_data: Any) -> UptimeRobotResponse:
        """
        :raise UptimeRobotError: if the request returns an error status code
        """
        if not self.has_api_key:
            return {}

        input_data.setdefault("format", "json")
        input_data["api_key"] = self.api_key

        self._log("POST", self.base / endpoint, input_data)

        resp = (self.base / endpoint).post(json=input_data)

        self._log("RESP", resp.__dict__)

        if not resp.ok:
            match resp.status_code:
                case 429:
                    raise UptimeRobotRatelimit(resp)
                case _:
                    raise UptimeRobotException(resp)

        try:
            output_data = resp.json()  # type: UptimeRobotResponse
        except json.JSONDecodeError as e:
            raise UptimeRobotException(resp, str(e)) from e

        if output_data.get("stat") == "fail":
            raise UptimeRobotException(resp, output_data.get("error", output_data))

        return output_data

    @classmethod
    def format_list(cls, values: typing.Iterable[typing.Any]) -> str:
        """
        UptimeRobot specific way to format a list: "-"-separated.

        Examples:
             UptimeRobot.format_list([1, 2, 3])
             # -> "1-2-3"
        """
        return "-".join([str(_) for _ in values])

    def get_account_details(self) -> Optional[UptimeRobotAccount]:
        resp = self._post("getAccountDetails")

        return resp.get("account", {})

    def get_monitors(self, search: str = "", monitor_ids: typing.Iterable[str | int] = (), mwindows = 0) -> list[UptimeRobotMonitor]:
        data = {}
        if search:
            data["search"] = search

        if monitor_ids:
            data["monitors"] = self.format_list(monitor_ids)

        if mwindows:
            data["mwindows"] = mwindows

        result = self._post("getMonitors", **data).get("monitors")
        if result is None:
            return []

        return result

    def get_monitor(self, monitor_id: str, mwindows = 0) -> Optional[UptimeRobotMonitor]:
        if monitors := self.get_monitors(monitor_ids=[monitor_id], mwindows=mwindows):
            return monitors[0]

        return None

    def new_monitor(self, friendly_name: str, url: str, monitor_type: MonitorType = MonitorType.HTTP) -> Optional[int]:
        data = {
            "friendly_name": friendly_name,
            "url": url,
            "type": monitor_type.value,
        }
        response = self._post("newMonitor", **data)

        return response.get("monitor", {}).get("id")

    def edit_monitor(self, monitor_id: int, new_data: AnyDict) -> bool:
        resp = self._post("editMonitor", id=monitor_id, **new_data)

        return str(resp.get("monitor", {}).get("id")) == str(monitor_id)

    def delete_monitor(self, monitor_id: int) -> bool:
        resp = self._post("deleteMonitor", id=monitor_id)

        return str(resp.get("monitor", {}).get("id")) == str(monitor_id)

    def reset_monitor(self, monitor_id: int) -> bool:
        resp = self._post("resetMonitor", id=monitor_id)

        return str(resp.get("monitor", {}).get("id")) == str(monitor_id)

    # def get_alert_contacts(self):
    #     return self._post("getAlertContacts")
    #
    # def new_alert_contact(self, contact_data):
    #     return self._post("newAlertContact", input_data=contact_data)
    #
    # def edit_alert_contact(self, contact_id, new_data):
    #     return self._post("editAlertContact", input_data={"contact_id": contact_id, "new_data": new_data})
    #
    # def delete_alert_contact(self, contact_id):
    #     return self._post("deleteAlertContact", input_data={"contact_id": contact_id})
    #
    def get_m_windows(self, mwindow_id: typing.Iterable[str | int] = ()):
        data = {}
        if mwindow_id:
            data["mwindows"] = self.format_list(mwindow_id)

        result = self._post("getMWindows", **data).get("mwindows")
        if result is None:
            return []

        return result

    def get_m_window(self, mwindow_id) -> Optional[UptimeRobotMaintenanceWindow]:
        if mwindows := self.get_m_windows(mwindow_id=[mwindow_id]):
            return mwindows[0]

        return None

    def new_maintenance_window(self, friendly_name: str, start_time: dt.datetime, type: str | int, **window_data):
        window_type = {
            "once": 1,
            "daily": 2,
            "weekly": 3,
            "montly": 4,
        }.get(type, type)

        resp = self._post(
            "newMWindow",
            friendly_name=friendly_name,
            start_time=int(start_time.timestamp()) + 10,  # add some seconds buffer to ensure it's in the future
            type=window_type,
            **window_data,
        )
        return resp.get("mwindow", {}).get("id", 0)

    def edit_m_window(self,new_data):
        return self._post("editMWindow", **new_data)

    def delete_maintenance_window(self, window_id: int) -> bool:
        resp = self._post("deleteMWindow", id=int(window_id))

        return resp.get("stat", "") == "ok"

    def clean_maintenance_windows(self) -> int:
        removed = 0
        for window in self._post("getMWindows").get("mwindows", []):
            # you can't query on type directly so filter all non-once here:
            if window["type"] != "once":
                continue

            self.delete_maintenance_window(window["id"])
            removed += 1

        return removed

    def get_psps(self) -> list[UptimeRobotDashboard]:
        resp = self._post("getPSPs")

        return resp.get("psps")

    def get_psp(self, idx: str) -> UptimeRobotDashboard | None:
        resp = self._post("getPSPs", psps=str(idx))

        psps = resp.get("psps")

        return psps[0] if psps else None

    # def new_psp(self, psp_data):
    #     return self._post("newPSP", input_data=psp_data)

    def edit_psp(self, psp_id: str, monitors: list[str | int], **kwargs: typing.Any) -> bool:
        data = {"id": psp_id, "monitors": self.format_list(monitors), **kwargs}
        resp = self._post("editPSP", **data)
        return str(resp.get("psp", {}).get("id")) == str(psp_id)

    # def delete_psp(self, psp_id):
    #     return self._post("deletePSP", input_data={"psp_id": psp_id})

    @staticmethod
    def format_status(status_code: int) -> str:
        return {
            0: "paused",
            1: "not checked yet",
            2: "up",
            8: "seems down",
            9: "down",
        }.get(status_code, f"Unknown status '{status_code}'!")

    @staticmethod
    def format_status_color(status_code: int) -> "Color":
        colors: dict[int, "Color"] = {
            0: "grey",
            1: "grey",
            2: "green",
            8: "red",
            9: "red",
        }

        return colors.get(status_code, "grey")


class LazyUptimeRobot:
    """
    Allows 'uptime_robot' to be defined globally (so every task can use it),
    but don't init at import time
    (because then it could complain about missing docker-compose.yml before actually needing config)
    """

    def __init__(self):
        self._instance = None

    def __getattr__(self, item):
        if self._instance is None:
            self._instance = UptimeRobot()
            self._instance.set_verbosity()  # uses 'edwh.get_env_value', which warns if dc.yml is missing
        return getattr(self._instance, item)


uptime_robot = typing.cast(UptimeRobot, LazyUptimeRobot())
