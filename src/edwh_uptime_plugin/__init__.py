# SPDX-FileCopyrightText: 2023-present Remco Boerma <remco.b@educationwarehouse.nl>
#
# SPDX-License-Identifier: MIT

from . import tasks
from .uptimerobot import UptimeRobot, uptime_robot

__all__ = [
    "UptimeRobot",  # cls
    "uptime_robot",  # default instance
    "tasks",
]
