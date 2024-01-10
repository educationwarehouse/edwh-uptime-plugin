import enum
import json
import typing
from typing import Any, Optional

import requests
from edwh import check_env
from typing_extensions import NotRequired, Required
from yayarl import URL

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


class UptimeRobotResponse(typing.TypedDict, total=False):
    stat: typing.Literal["ok", "fail"]
    error: NotRequired[UptimeRobotErrorResponse]
    pagination: NotRequired[UptimeRobotPagination]
    # actual data differs per endpoint:
    monitor: NotRequired["UptimeRobotMonitor"]
    monitors: NotRequired[list["UptimeRobotMonitor"]]
    account: NotRequired[UptimeRobotAccount]


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

    def __init__(self):
        self.api_key = check_env(
            "UPTIMEROBOT_APIKEY",
            default=None,
            comment="The API key used to manage UptimeRobot monitors.",
        )

    def _post(self, endpoint: str, **input_data: Any) -> UptimeRobotResponse:
        """
        :raise UptimeRobotError: if the request returns an error status code
        """
        input_data.setdefault("format", "json")
        input_data["api_key"] = self.api_key
        resp = (self.base / endpoint).post(json=input_data)

        if not resp.ok:
            raise UptimeRobotException(resp)

        try:
            output_data = resp.json()  # type: UptimeRobotResponse
        except json.JSONDecodeError as e:
            raise UptimeRobotException(resp, str(e)) from e

        if output_data.get("stat") == "fail":
            raise UptimeRobotException(resp, output_data.get("error", output_data))

        return output_data

    def get_account_details(self):
        resp = self._post("getAccountDetails")

        return resp.get("account", {})

    def get_monitors(self, search: str = "") -> list[UptimeRobotMonitor]:
        data = {}
        if search:
            data["search"] = search
        result = self._post("getMonitors", **data).get("monitors")
        if result is None:
            return []

        return result
        # return typing.cast(list[UptimeRobotMonitor], result)

    def new_monitor(self, friendly_name: str, url: str, monitor_type: MonitorType = MonitorType.HTTP) -> Optional[int]:
        data = {
            "friendly_name": friendly_name,
            "url": url,
            "type": monitor_type.value,
        }
        response = self._post("newMonitor", **data)

        return response.get("monitor", {}).get("id")

    def edit_monitor(self, monitor_id, new_data):
        return self._post("editMonitor", input_data={"monitor_id": monitor_id, "new_data": new_data})

    def delete_monitor(self, monitor_id: int) -> bool:
        resp = self._post("deleteMonitor", id=monitor_id)

        return resp.get("monitor", {}).get("id") == monitor_id

    def reset_monitor(self, monitor_id):
        return self._post("resetMonitor", input_data={"monitor_id": monitor_id})

    def get_alert_contacts(self):
        return self._post("getAlertContacts")

    def new_alert_contact(self, contact_data):
        return self._post("newAlertContact", input_data=contact_data)

    def edit_alert_contact(self, contact_id, new_data):
        return self._post("editAlertContact", input_data={"contact_id": contact_id, "new_data": new_data})

    def delete_alert_contact(self, contact_id):
        return self._post("deleteAlertContact", input_data={"contact_id": contact_id})

    def get_m_windows(self):
        return self._post("getMWindows")

    def new_m_window(self, window_data):
        return self._post("newMWindow", input_data=window_data)

    def edit_m_window(self, window_id, new_data):
        return self._post("editMWindow", input_data={"window_id": window_id, "new_data": new_data})

    def delete_m_window(self, window_id):
        return self._post("deleteMWindow", input_data={"window_id": window_id})

    def get_psps(self):
        return self._post("getPSPs")

    def new_psp(self, psp_data):
        return self._post("newPSP", input_data=psp_data)

    def edit_psp(self, psp_id, new_data):
        return self._post("editPSP", input_data={"psp_id": psp_id, "new_data": new_data})

    def delete_psp(self, psp_id):
        return self._post("deletePSP", input_data={"psp_id": psp_id})

    @staticmethod
    def format_status(status_code: int) -> str:
        return {
            0: "paused",
            1: "not checked yet",
            2: "up",
            8: "seems down",
            9: "down",
        }.get(status_code, f"Unknown status '{status_code}'!")


uptime_robot = UptimeRobot()
