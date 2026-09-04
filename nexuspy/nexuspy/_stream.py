import json
from typing import Any, Literal

__all__ = ["send", "send_log"]


def send(send_type: Literal["log"], *args: Any):
    match send_type:
        case "log":
            send_log(*args)

        case _:
            raise TypeError(f"send_type {send_type} not supported")


def send_log(level: Literal["error", "warn", "info", "debug"], msg: str) -> None:
    log_data = {
        "l": level,
        "m": msg,
    }
    log_str = json.dumps(log_data)
    print(log_str, flush=True)
