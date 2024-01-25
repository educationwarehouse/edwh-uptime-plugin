import json
import typing
from collections import defaultdict

import yaml


def noop(*_, **__):
    raise ValueError("Invalid output format.")


dumpers = defaultdict(noop)
dumpers["text"] = dumpers["plaintext"] = print
dumpers["json"] = lambda data, *a, **kw: print(
    json.dumps(
        data,
        *a,
        indent=2,
        **kw,
    )
)
dumpers["yaml"] = dumpers["yml"] = lambda data, *a, **kw: print(
    yaml.dump(
        data,
        *a,
        indent=2,
        **kw,
    )
)

SUPPORTED_FORMATS = typing.Literal["plaintext", "text", "json", "yaml", "yml"]

DEFAULT_PLAINTEXT: SUPPORTED_FORMATS = "text"
DEFAULT_STRUCTURED: SUPPORTED_FORMATS = "json"
DEFAULT_YAML: SUPPORTED_FORMATS = "yaml"