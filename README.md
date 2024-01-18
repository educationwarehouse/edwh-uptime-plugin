# edwh-uptime-plugin

[![PyPI - Version](https://img.shields.io/pypi/v/edwh-uptime-plugin.svg)](https://pypi.org/project/edwh-uptime-plugin)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/edwh-uptime-plugin.svg)](https://pypi.org/project/edwh-uptime-plugin)

-----

UptimeRobot API integration for the `edwh` tool.

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install edwh-uptime-plugin
```

But probably you want to install the whole edwh package:

```console
pipx install edwh[uptime]
# or
pipx install edwh[plugins,omgeving]
```

## Usage

```bash
# set your api key and see your profile info:
edwh uptime.account

# see the other available commands:
edwh help uptime
```

`UPTIMEROBOT_APIKEY` is saved in a `.env` file. You can also set `IS_DEBUG=1` if you want to see verbose logging (every
request and response).

## License

`edwh-uptime-plugin` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
