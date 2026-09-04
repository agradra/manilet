import atexit
import os
import queue
import signal
import subprocess
import threading
import time
from enum import IntEnum
from pathlib import Path
from queue import Queue

from ._singleton import Singleton
from ._stream import parse
from .db import CryptoDB
from .discord import Discord
from .log import SystemLogger, Log, LogLevel
from .time import NtpTimer

__all__ = ["Agent", "AgentManager", "AgentSendMode", "AgentStatus"]


class _InvalidVirtualEnvError(Exception):
    """지정된 경로가 유효한 파이썬 가상환경이 아닐 때 발생하는 예외"""
    pass

class _InvalidPythonFileError(Exception):
    """지정된 경로가 유효한 파이썬 파일이 아닐 때 발생하는 예외"""
    pass

def _validate_dir(path: str | Path) -> Path:
    """
        주어진 경로가 존재하는 폴더인지 확인하고 아닐 시 에러를 발생시킵니다.

        Args:
            path: 검증할 폴더 경로

        Raises:
            FileNotFoundError: 존재하지 않을 경우
            NotADirectoryError: 폴더가 아닐 경우

        Returns:
            path: Path(path)
    """
    dir_path = Path(path) if isinstance(path, str) else path

    if not dir_path.exists() or not dir_path.is_absolute():
        raise FileNotFoundError

    if not dir_path.is_dir():
        raise NotADirectoryError

    return dir_path

def _validate_venv(path: str | Path) -> Path:
    """
    주어진 경로가 유효한 파이썬 가상환경인지 검증하고 아닐 시 에러를 발생시킵니다.
    (Windows, Linux, macOS 및 모든 가상환경 생성 도구 지원)

    Args:
        path: 검증할 가상환경 경로

    Returns:
        path: Path(path)

    Raises:
        FileNotFoundError: 존재하지 않을 경우
        NotADirectoryError: 폴더가 아닐 경우
        InvalidVirtualEnvError: 파이썬 가상환경이 아닐 경우
    """

    venv_path = _validate_dir(path)

    if os.name == 'nt':  # Windows
        python_exe = venv_path / "Scripts" / "python.exe"
    else:  # Linux / macOS
        python_exe = venv_path / "bin" / "python"

    pyvenv_cfg = venv_path / "pyvenv.cfg"
    conda_meta = venv_path / "conda-meta"

    if python_exe.is_file() and (pyvenv_cfg.is_file() or conda_meta.is_dir()):
        return venv_path

    else:
        raise _InvalidVirtualEnvError


def _validate_py(path: str | Path) -> Path:
    """
    주어진 경로가 존재하는 파이썬 파일(.py)인지 검증하고 Path 객체를 반환합니다.

    Args:
        path (str | Path): 검증할 파일 경로

    Returns:
        Path: 검증이 완료된 pathlib.Path 객체

    Raises:
        FileNotFoundError: 경로가 존재하지 않을 때
        _InvalidPythonFileError: 파이썬 파일이 아닐 때
    """
    py_path = Path(path) if isinstance(path, str) else path

    if not py_path.exists() or not py_path.is_absolute():
        raise FileNotFoundError

    if py_path.is_file() and py_path.suffix == '.py':
            return py_path
    raise _InvalidPythonFileError

# ======================================================================================================================

class AgentStatus(IntEnum):
    """에이전트 상태 Enum 클라스

    Attributes:
        SLEEPING: 초기
        RUNNING: 작동중
        STOPPING: 정지중
        STOPPED: 정지
    """
    SLEEPING = 0
    RUNNING  = 1
    STOPPING = 2
    STOPPED  = 3


class AgentSendMode(IntEnum):
    """에이전트 로그 전송 모드 Enum 클라스

        Attributes:
            NoSend: 미전송
            Send: 정상
            SendTest: 테스트 전송
        """
    NoSend   = 0
    Send     = 1
    SendTest = 2

class Agent:
    """에이전트 데이터클라스

    Attributes:

    """
    _logger = SystemLogger()
    _ntp_timer = NtpTimer()
    _discord = Discord()

    def __init__(self, py_path: str | Path):
        # only read
        # 불변
        self._file_path: Path | None = _validate_py(py_path)
        self._name: str = self._file_path.stem

        # 가변
        self._status: AgentStatus = AgentStatus.SLEEPING
        self._start_time: float | None = None
        self._end_time: float | None = None

        # 외부 변경
        self._venv_path: Path | None = None
        self._send_mode: AgentSendMode = AgentSendMode.NoSend

        # 내부 변경
        self._process: subprocess.Popen | None = None
        self._pid: int | None = None
        self._logs: Queue[Log] = Queue()

        self._lock = threading.Lock()

    # getter ===========================================================================================================

    @property
    def file_path(self) -> Path | None:
        return self._file_path

    @property
    def name(self) -> str:
        return self._name

    # ---

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def start_time(self) -> float | None:
        return self._start_time

    @property
    def end_time(self) -> float | None:
        return self._end_time

    # ---

    @property
    def venv_path(self) -> Path | None :
        return self._venv_path

    @property
    def send_mode(self) -> AgentSendMode:
        return self._send_mode

    @property
    def pid(self) -> int | None:
        return self._pid

    # ---


    @property
    def is_file_exist(self) -> bool:
        if self._file_path is None:
            return False
        else:
            return True

    @property
    def run_time(self) -> float | None:
        with self._lock:
            start = self._start_time
            end = self._end_time

        if start is None:
            return None
        if end is None:
            return Agent._ntp_timer.now() - start
        return end - start

    # setter ===========================================================================================================

    def set_venv_path(self, path: str | Path) -> Path | None:
        """에이전트의 가상환경을 변경하고 현재 가상환경 경로를 반환합니다.

        Args:
            path: 새로 설정할 가상환경 경로

        Returns:
            현재 가상환경 경로 (설정되어 있지 않다면 None)
        """
        if self.status in (AgentStatus.RUNNING, AgentStatus.STOPPING):
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트는 현재 작동중이므로 가상환경을 변경할 수 없습니다.")
            return self._venv_path

        try:
            venv_path = _validate_venv(path)
            with self._lock:
                self._venv_path = venv_path
            self._logger.emit(LogLevel.PASS, f"'{self._name}'의 가상환경을 변경하였습니다.")

        except FileNotFoundError:
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'의 가상환경을 변경할 수 없습니다.'{path}' 경로는 존재하지 않는 경로입니다.")

        except (NotADirectoryError, _InvalidVirtualEnvError):
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'의 가상환경을 변경할 수 없습니다.'{path}' 경로는 가상환경이 아닙니다.")

        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"에이전트({self._name}) 가상환경 변경 중 알 수 없는 에러 발생 - {e}")

        return self._venv_path

    def set_send_mode(self, send_mode: AgentSendMode) -> None:
        """에이전트의 전송 모드를 변경합니다.

        Args:
            send_mode: 새로 설정할 전송 모드
        """

        if not isinstance(send_mode, AgentSendMode):
            raise TypeError("send_mode는 AgentSendMode클라스여야 함")

        if self._send_mode != send_mode:
            with self._lock:
                self._send_mode = send_mode

            match send_mode:
                case AgentSendMode.NoSend:
                    self._logger.emit(LogLevel.PASS, f"'{self._name}'의 로그 전송을 종료합니다.")
                case AgentSendMode.Send:
                    self._logger.emit(LogLevel.PASS, f"'{self._name}'의 로그 전송을 시작합니다.")
                case AgentSendMode.SendTest:
                    self._logger.emit(LogLevel.PASS, f"'{self._name}'의 로그를 테스르 채널로 전송합니다.")
                case _:
                    raise ValueError("set_send_mode send_mode가ㅓㄹㅇ;ㅏㅣㅁㄴ얾ㅇㄴ 말이 안됨")

    # 조작 =============================================================================================================

    def run(self) -> None:
        """에이전트 실행"""
        # 상태 확인
        if self.status in (AgentStatus.RUNNING, AgentStatus.STOPPING):
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트는 현재 작동중이므로 실행할 수 없습니다.")
            return

        # 실행 파일 증명
        if self._file_path is None:
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트는 실행 파일을 잃어버린 에이전트 입니다.")
            return
        try:
            _validate_py(self._file_path)
        except FileNotFoundError:
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트의 실행 파일을 찾을 수 없습니다.")
            with self._lock: self._file_path = None
            return

        except _InvalidPythonFileError:
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트의 실행 파일이 .py파일이 아닙니다.")
            with self._lock: self._file_path = None
            return

        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"'{self._name}'에이전트 실행 실패: '{self._name}'실행 파일 증명 중 알 수 없는 에러 발생 - {e}", is_alert=True)
            with self._lock: self._file_path = None
            return

        # 가상환경 증명
        if self._venv_path is None:
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트의 가상환경 경로가 설정되어있지 않아 실행할 수 없습니다.")
            return

        try:
            _validate_venv(self._venv_path)

        except FileNotFoundError:
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트의 가상환경 경로 상에 실제 가상환경이 존재하지 않습니다.")
            return
        except (NotADirectoryError, _InvalidVirtualEnvError):
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트의 가상환경 경로 상에 존재하는 파일은 가상환경이 아닙니다.")
            return
        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"'{self._name}'에이전트 실행 실패: 가상환경 증명 중 알 수 없는 에러 발생 - {e}", is_alert=True)
            return

        # 실행
        try:
            cmd = [str(self._venv_path / ("Scripts/python.exe" if os.name == 'nt' else "bin/python")), '-u', str(self._file_path)]

            process = subprocess.Popen(
                cmd,
                cwd=self._file_path.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            with self._lock:
                self._status = AgentStatus.RUNNING
                self._process = process
                self._pid = process.pid
                self._start_time = Agent._ntp_timer.now()
                self._end_time = None

            def life_cycle() -> None:
                """life_cycle 스레드 본인이 stdout을 읽고, stderr만 1개의 서브 스레드로 병렬 수집"""
                exit_code = None

                def emit_log(log_item: Log) -> None:
                    self._logs.put_nowait(log_item)
                    if self._send_mode != AgentSendMode.NoSend:
                        try:
                            Agent._discord.send_log(self._name, log_item, self._send_mode == AgentSendMode.SendTest )
                        except Exception as discord_err:
                            self._logger.emit(LogLevel.WARN, f"'{self._name}' 디스코드 전송 실패: {discord_err}")

                def read_stderr(pipe) -> None:
                    """stderr 전용 서브 스레드 (에이전트당 딱 1개만 추가 생성)"""
                    err_buffer: list[str] = []
                    try:
                        for line in iter(pipe.readline, ""):
                            err_buffer.append(line)

                        if err_buffer:
                            full_err = "".join(err_buffer).rstrip()
                            emit_log(Log(msg=full_err, level=LogLevel.FATAL))
                    finally:
                        if not pipe.closed:
                            pipe.close()

                try:
                    t_err = None
                    if self._process:
                        # 1. stderr 수집용 스레드 1개만 백그라운드로 실행
                        if self._process.stderr:
                            t_err = threading.Thread(target=read_stderr, args=(self._process.stderr,), daemon=True)
                            t_err.start()

                        # 2. stdout은 현재 스레드(life_cycle)가 직접 읽음 (별도 스레드 생성 X)
                        if self._process.stdout:
                            try:
                                for line in iter(self._process.stdout.readline, ""):
                                    emit_log(parse(line))
                            finally:
                                if not self._process.stdout.closed:
                                    self._process.stdout.close()

                        # 3. stderr 읽기 완료 대기
                        if t_err:
                            t_err.join()

                        # 프로세스 완전 종료 대기
                        exit_code = self._process.wait()

                    if self._status == AgentStatus.RUNNING and exit_code != 0:
                        self._logger.emit(
                            LogLevel.WARN,
                            f"'{self._name}'에이전트의 비정상 종료가 감지되었습니다. (exit code: {exit_code})"
                        )

                    self._logs.put_nowait(Log(LogLevel.DEBUG, f"{self._name} 에이전트 정지 ({exit_code})"))

                except Exception as e:
                    self._logs.put_nowait(Log(LogLevel.ERROR, f"{self._name} 에이전트 관리 쓰레드 내부 에러 발생 - {e}"))

                finally:
                    with self._lock:
                        self._status = AgentStatus.STOPPED
                        self._end_time = Agent._ntp_timer.now()
                        self._process = None
                        self._pid = None

            threading.Thread(target=life_cycle, daemon=True).start()

            self._logs.put_nowait(Log(LogLevel.DEBUG, f"{self._name} 에이전트 작동 시작"))

        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"'{self._name}'에이전트 실행 실패: 프로세스 생성 및 실행 중 에러 발생 - {e}")

    def stop(self) -> None:
        """에이전트 종료"""

        # 실행 상태 검증
        if self._status in (AgentStatus.STOPPED, AgentStatus.SLEEPING, AgentStatus.STOPPING):
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트는 이미 중지했거나 정지 중인 상태이므로 정지 신호를 보낼 수 없습니다.")
            return

        # 프로세스 객체 유무 검증
        if self._process is None or self._process.poll() is not None:
            self._logger.emit(LogLevel.WARN, f"'{self._name}'에이전트는 실행 중인 상태값이나 내부 프로세스가 없거나 죽어있습니다. 에이전트를 정지 처리합니다.")
            with self._lock:
                self._status = AgentStatus.STOPPED
                self._end_time = Agent._ntp_timer.now()
                self._process = None
                self._pid = None
            return

        # 정지 시도
        with self._lock: self._status = AgentStatus.STOPPING

        def kill_and_wait():
            if self._process:
                try:
                    if os.name == 'nt':  # 원도우: 종료 요청 (SIGTERM / CTRL_BREAK)
                        self._process.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        self._process.terminate()  # Linux/Mac: SIGTERM 전송

                    self._process.wait(timeout=3.0)

                except subprocess.TimeoutExpired:
                    self._logger.emit(LogLevel.WARN, f"'{self._name}'에이전트가 응답하지 않아 강제 종료(SIGKILL)를 시도합니다.")
                    try:

                        self._process.kill()  # 3초 지나도 안 꺼지면 하드 강제 종료 (SIGKILL)
                        self._process.wait(timeout=2.0)  # 좀비 프로세스 방지를 위한 완전 수거
                    except Exception as e:
                        self._logger.emit(LogLevel.ERROR, f"'{self._name}'에이전트 강제 종료 실패하였습니다. 프로세스(pid:{self._pid})를 직접 확인하여 조치해주십시오 - {e}")

                except Exception as e:
                    self._logger.emit(LogLevel.ERROR, f"'{self._name}'에이전트(pid:{self._pid}) 정지 시도 중 예상치 못한 오류 발생 - {e}")

        threading.Thread(target=kill_and_wait, daemon=True).start()


    def reset(self) -> None:
        """에이전트 초기화"""

        if self.status == AgentStatus.SLEEPING:
            return
        if self.status != AgentStatus.STOPPED:
            self._logger.emit(LogLevel.FAIL, f"'{self._name}'에이전트는 작동 중이라서 초기화 할 수 없습니다.")
            return

        with self._lock:
            self._status = AgentStatus.SLEEPING
            self._start_time = None
            self._end_time = None
            self._send_mode = AgentSendMode.NoSend

    def get_log(self, block: bool = False, timeout: float | None = None) -> Log | None:
        try:
            return self._logs.get(block=block, timeout=timeout)
        except queue.Empty:
            return None


    def check_file(self) -> bool:
        """에이전트 실행 파일이 실제 존재하는지 확인하고 존재 여부 업데이트 및 반환"""

        if self._file_path is None:
            return False
        try:
            _ = _validate_py(self._file_path)
            return True

        except Exception:
            with self._lock: self._file_path = None
            return False


# ======================================================================================================================
# ======================================================================================================================

class AgentManager(metaclass=Singleton):
    """에이전트를 통합 관리하고 여러 편의 기능을 지원하는 싱글톤 클라스

    """

    def __init__(self):
        self._lock = threading.Lock()
        self._logger = SystemLogger()

        self._db = CryptoDB("AgentManager")

        self._agents_dir_path: str = self._db.create("agents_dir_path", "", encrypt=True, exist_ok=True)
        self._default_venv_path: str = self._db.create("default_venv_path", "", encrypt=True, exist_ok=True)

        try:
            self._agents_dir_path = str(_validate_dir(self._agents_dir_path))
        except Exception:
            pass
        try:
            self._default_venv_path = str(_validate_venv(self._default_venv_path))
        except Exception:
            pass

        self._agent_dict: dict[str, Agent] = {}
        self._reload_agents()
        self._is_die: bool = False

        threading.Thread(target=self._loop_check_all_file, daemon=True).start()
        atexit.register(self.kill)

    # getter ──────────────────────────────────────────────────────────────

    @property
    def agents_dir_path(self) -> str:
        return self._agents_dir_path

    @property
    def default_venv_path(self) -> str:
        return self._default_venv_path

    # setter ──────────────────────────────────────────────────────────────

    def set_agents_dir(self, path: str):
        """에이전트 폴더 경로를 변경 및 설정합니다.

            Args:
                path: 설정할 에이전트 폴더 경로
        """
        if self._agents_dir_path == path.strip():
            return

        for agent in self._agent_dict.values():
            if agent.status in (AgentStatus.RUNNING, AgentStatus.STOPPING):
                self._logger.emit(LogLevel.FAIL, f"에이전트용 폴더 경로를 변경할 수 없습니다. 아직 작동 중인 에이전트({agent.name})가 남아있습니다.")
                return
        try:

            dir_path = str(_validate_dir(path.strip()))

            with self._lock:
                self._agents_dir_path = dir_path

            self._db.update("agents_dir_path", dir_path)

            is_pass = self._reload_agents()
            if is_pass:
                self._logger.emit(LogLevel.PASS, f"에이전트 폴더 경로를 변경하였습니다.")
            else:
                self._logger.emit(LogLevel.FAIL, f"에이전트 폴더 경로를 변경하였으니 파일 조회 중 오류가 발생하였습니다.")

        except FileNotFoundError:
            self._logger.emit(LogLevel.FAIL, f"에이전트용 폴더 경로를 변경할 수 없습니다.'{path}' 경로는 존재하지 않는 경로입니다.")

        except NotADirectoryError:
            self._logger.emit(LogLevel.FAIL, f"에이전트용 폴더 경로를 변경할 수 없습니다.'{path}' 경로는 폴더가 아닙니다.")

        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"에이전트용 폴더 경로 변경 중 알 수 없는 에러 발생 - {e}")

    def set_default_venv(self, path: str):
        """기본 가상환경 경로를 변경합니다.

            Args:
                path: 설정할 가상환경 경로
        """
        try:
            venv_path = str(_validate_venv(path.strip()))
            self._db.update("default_venv_path", venv_path)
            with self._lock:
                self._default_venv_path = venv_path

            self._logger.emit(LogLevel.PASS, f"에이전트 기본 가상환경 경로를 변경하였습니다.")

        except FileNotFoundError:
            self._logger.emit(LogLevel.FAIL, f"에이전트 기본 가상환경 경로를 변경할 수 없습니다.'{path}' 경로는 존재하지 않는 경로입니다.")

        except (NotADirectoryError, _InvalidVirtualEnvError):
            self._logger.emit(LogLevel.FAIL, f"에이전트 기본 가상환경 경로를 변경할 수 없습니다.'{path}' 경로는 가상환경이 아닙니다.")

        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"에이전트 기본 가상환경 경로 변경 중 알 수 없는 에러 발생 - {e}")

    # 전체 에이전트 조작 ────────────────────────────────────────────────────────────────

    def apply_venv_agents(self, only_none_venv: bool = True):
        """에이전트들의 가상환경을 디폴트값으로 적용합니다.

        Args:
            only_none_venv: 가상환경이 없는 에이전트만 적용할지 여부
        """
        if self._default_venv_path == "":
            self._logger.emit(LogLevel.FAIL, f"에이전트들에게 적용할 가상환경 경로가 없습니다.")
            return

        if not self._agent_dict:
            self._logger.emit(LogLevel.FAIL, f"가상환경을 적용할 에이전트가 없습니다.")
            return

        try:
            apply_venv_path = _validate_venv(self._default_venv_path)

        except FileNotFoundError:
            self._logger.emit(LogLevel.FAIL, f"에이전트들에 가상환경 경로를 적용할 수 없습니다.'{self._default_venv_path}' 경로는 존재하지 않는 경로입니다.")
            return
        except (NotADirectoryError, _InvalidVirtualEnvError):
            self._logger.emit(LogLevel.FAIL, f"에이전트들에 가상환경 경로를 적용할 수 없습니다.'{self._default_venv_path}' 경로는 가상환경이 아닙니다.")
            return
        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"에이전트들 가상환경 경로 변경 중 알 수 없는 에러 발생 - {e}")
            return

        if only_none_venv:
            applied_count = 0
            for agent in self._agent_dict.values():
                if agent.venv_path is None and agent.status in (AgentStatus.SLEEPING, AgentStatus.STOPPED):
                    agent._venv_path = apply_venv_path
                    applied_count += 1

            if applied_count > 0:
                self._logger.emit(LogLevel.PASS, f"{applied_count}개의 에이전트(미설정/정지 상태)에 기본 가상환경을 적용했습니다.")
            else:
                self._logger.emit(LogLevel.INFO, f"기본 가상환경을 적용할 에이전트가 없습니다. (모두 설정되어 있거나 작동 중)", is_alert=True)

        else:
            applied_count = 0
            for agent in self._agent_dict.values():
                if agent.status in (AgentStatus.SLEEPING, AgentStatus.STOPPED):
                    agent._venv_path = apply_venv_path
                    applied_count += 1

            if applied_count > 0:
                self._logger.emit(LogLevel.PASS, f"{applied_count}개의 에이전트(정지 상태)에 기본 가상환경을 일괄 적용했습니다.")
            else:
                self._logger.emit(LogLevel.INFO, f"기본 가상환경을 적용할 에이전트가 없습니다. (모두 작동 중)", is_alert=True)


    def reload_agents(self):
        """에이전트 폴더에서 파이썬 파일을 불러화 에이전트로 변환 및 저장합니다."""
        if self._agents_dir_path == "":
            self._logger.emit(LogLevel.FAIL, f"아직 에이전트용 폴더가 설정되지 않았습니다.")

        is_pass = self._reload_agents()
        if is_pass:
            self._logger.emit(LogLevel.PASS, f"에이전트 목록을 최신 상태로 갱신하였습니다.")

    def _reload_agents(self) -> bool:
        """reload_agents 메소드의 실제 로직, 성공 시 True 반환"""

        if self._agents_dir_path == "":
            return False

        # 폴더 증명
        try:
            agents_dir = _validate_dir(self._agents_dir_path)

        except FileNotFoundError:
            self._logger.emit(LogLevel.FAIL, f"현재 에이전트용 폴더를 읽을 수 없습니다. '{self._agents_dir_path}'는 존재하지 않는 경로입니다.")
            return False
        except NotADirectoryError:
            self._logger.emit(LogLevel.FAIL, f"현재 에이전트용 폴더를 읽을 수 없습니다. '{self._agents_dir_path}'는 폴더가 아닙니다.")
            return False
        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"에이전트용 폴더 읽는 중 알 수 없는 에러 발생 - {e}")
            return False

        # 파이썬 파일 수집
        try:
            py_path_list = list(agents_dir.glob("*.py"))
        except Exception as e:
            self._logger.emit(LogLevel.ERROR, f"현재 에이전트용 폴더 내 파이썬 파일들을 읽을 수 없습니다. - {e}")
            return False

        disk_agents = {py_path.stem: py_path for py_path in py_path_list}

        # 딕셔너리에 있는데 디스크에 없고 SLEEPING인 에이전트 제거
        for agent_name, target_agent in list(self._agent_dict.items()):
            if agent_name not in disk_agents or not target_agent.is_file_exist:
                if target_agent.status == AgentStatus.SLEEPING:
                    with self._lock:
                        del self._agent_dict[agent_name]

        # 디스크에 있는데 딕셔너리에 없는 에이전트 추가
        for agent_name, py_path in disk_agents.items():
            if agent_name not in self._agent_dict:
                try:
                    new_agent = Agent(py_path)
                    try:
                        new_agent._venv_path = _validate_venv(self.default_venv_path)
                    except Exception:
                        pass
                    with self._lock:
                        self._agent_dict[agent_name] = new_agent
                except Exception as e:
                    self._logger.emit(LogLevel.ERROR, f"'{agent_name}' 에이전트 생성 중 에러 발생 - {e}")

        return True

    def _loop_check_all_file(self):
        while not self._is_die:
            time.sleep(10)
            self.check_all_file()

    def check_all_file(self):
        """모든 에이전트의 실행 파일 확인"""
        with self._lock:
            for agent in self._agent_dict.values():
                agent.check_file()

    def kill(self):
        self._is_die = True
        for agent in self._agent_dict.values():
            if agent.status in (AgentStatus.RUNNING, AgentStatus.STOPPING):
                if agent._process:
                    try:
                        agent._process.kill()
                        agent._process.wait(timeout=1.0)
                    except Exception:
                        pass

    # 조회 ────────────────────────────────────────────────────────────────

    def search_agent(self, agent_name: str) -> Agent | None:
        """이름으로 특정 에이전트를 조회하여 반환합니다.

        Returns:
            Agent | None: 조회 성공 시 해당 에이전트 객체, 실패 시 None 반환
        """
        with self._lock:
            target_agent = self._agent_dict.get(agent_name, None)
        if target_agent is None:
            self._logger.emit(LogLevel.ERROR, f"존재하지 않는 에이전트 탐색 시도 (search name : {agent_name})")
        return target_agent

    def get_agent_list(self) -> list[Agent]:
        """에이전트 리스르를 반환합니다.

        Returns:
            list[Agent]: list[에이전트1, 에이전트2, ...]
        """
        with self._lock:
            agent_list = list(self._agent_dict.values())
        return agent_list

    def get_agent_pid_map(self) -> dict[int, str]:
        """현재 실행 중인(RUNNING) 에이전트들의 {pid: name} 스냅샷을 안전하게 반환합니다."""
        pid_map = {}
        with self._lock:
            for name, agent in self._agent_dict.items():
                if agent.status == AgentStatus.RUNNING: # 작동 상태
                    pid_map[agent.pid] = name

        return pid_map

    # dummy?
    """
    def generate_log_file(self, agent_name: str) -> bool:
        try:
            target_name = agent_name.strip()
            target_agent = self.agent_dict.get(target_name)

            if not target_agent:
                self._logger.emit(LogLevel.WARN, f"'{target_name}' 로그 저장 실패: 에이전트를 찾을 수 없습니다.")
                return False

            if not target_agent.logs:
                self._logger.emit(LogLevel.FAIL, f"'{target_name}' 로그 저장 실패: 로그가 없습니다.")
                return False

            start_t = target_agent.start_time
            end_t = target_agent.end_time if target_agent.end_time else Util.get_time_str()

            raw_filename = f"{target_agent.name}({start_t} ~ {end_t}).txt"
            safe_filename = re.sub(r'[\\/*?:"<>|]', "-", raw_filename)

            log_dir = self._cf.PATH.LOGS
            log_dir.mkdir(parents=True, exist_ok=True)

            file_path = log_dir / safe_filename

            with open(file_path, "w", encoding="utf-8") as f:
                for log in reversed(target_agent.logs):
                    f.write(f"[{log.time}] {log.level} : {log.msg}\n")

            return True

        except Exception as e:
            self.put_sys_log(f"'{agent_name}' 로그 파일 생성 중 오류 발생: {e}")
            return False
    """

