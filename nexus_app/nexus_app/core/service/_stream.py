import json

from .log import LogLevel, Log


def parse(stream_str: str) -> Log:
    try:
        log_dict = json.loads(stream_str)
        return Log(
            msg=log_dict["m"],
            level=LogLevel[log_dict["l"].upper()],
        )
    except Exception:
        return Log(
            msg=stream_str.rstrip(),
            level=LogLevel.PRINT,
        )
