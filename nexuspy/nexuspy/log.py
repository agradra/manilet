from ._stream import send_log

__all__ = ['error', 'warn', 'info', 'debug']

def error(message: str) -> None:
    send_log('error', message)

def warn(message: str) -> None:
    send_log('warn', message)

def info(message: str) -> None:
    send_log('info', message)

def debug(message: str) -> None:
    send_log('debug', message)

