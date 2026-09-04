import socket
import sys
import traceback

# 소켓 객체가 가비지 컬렉터(GC)에 의해 해제되지 않도록 전역 유지
_instance_lock_socket = None

def _enforce_single_instance(port: int = 58291):
    """
    로컬 루프백(127.0.0.1) 소켓 바인딩을 이용한 크로스 플랫폼 중복 실행 방지
    - 프로세스가 강제 종료되어도 OS가 즉시 포트를 해제하므로 부작용 없음
     """
    global _instance_lock_socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # SO_REUSEADDR를 설정하지 않아 타 프로세스가 포트를 가로채지 못하도록 설정
        sock.bind(("127.0.0.1", port))
        _instance_lock_socket = sock
    except (OSError, socket.error):
        print(f"\r\033[2K\033[38;2;255;60;60mNexus가 이미 실행 중입니다.\033[0m")
        sys.exit(0)

def _print_title():
    start_rgb = (255, 127, 80)
    end_rgb = (120, 80, 255)

    ascii_art = """
╭──────────────────────────────────────────────────╮
│  ███╗   ██╗ ███████╗ ██╗  ██╗ ██╗   ██╗ ███████╗ │
│  ████╗  ██║ ██╔════╝ ╚██╗██╔╝ ██║   ██║ ██╔════╝ │
│  ██╔██╗ ██║ █████╗    ╚███╔╝  ██║   ██║ ███████╗ │
│  ██║╚██╗██║ ██╔══╝    ██╔██╗  ██║   ██║ ╚════██║ │
│  ██║ ╚████║ ███████╗ ██╔╝ ██╗ ╚██████╔╝ ███████║ │
│  ╚═╝  ╚═══╝ ╚══════╝ ╚═╝  ╚═╝  ╚═════╝  ╚══════╝ │
╰────────────── 𝘋𝘦𝘷𝘦𝘭𝘰𝘱𝘦𝘥 𝘣𝘺 𝐀𝐠𝐫𝐚𝐝𝐫𝐚 ──────────────╯
"""

    lines = ascii_art.strip("\n").split("\n")
    max_len = max(len(line) for line in lines) if lines else 1

    result_lines = []
    for line in lines:
        colored_line = []
        for x, char in enumerate(line):
            t = x / (max_len - 1) if max_len > 1 else 0

            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t)

            colored_line.append(f"\033[38;2;{r};{g};{b}m{char}")

        result_lines.append("".join(colored_line) + "\033[0m")

    print("\n".join(result_lines))

def _color_print(text,
                 red: int = 255, green: int = 255, blue: int = 255,
                 end: str | None = "\n", flush: bool = False) -> None | str:
    r, g, b = (max(0, min(255, c)) for c in (red, green, blue))
    print(f"\r\033[2K\033[38;2;{r};{g};{b}m{text}\033[0m", end=end, flush=flush)

#================================================================================================

def main():
    _print_title()
    print()

    try:
        _enforce_single_instance()

        # 버전 검증
        if sys.version_info < (3, 12):
            print(f"\033[2K\033[38;2;255;255;60m파이썬 3.12 이상 버전이 필요합니다.\033[0m", end="", flush=True)

        from nexus_app.core.service.db import CryptoDB, is_password_setting

        # 비번 입력 & 검증
        if is_password_setting():  # 이미 비번 있음
            while True:
                pw = input("Input Password: ")

                if CryptoDB.initialize(pw):
                    _color_print("\033[2K\r\033[1A\033[2K\rPassword verification completed", 100, 255, 100, end="", flush=True)
                    break
                else:
                    _color_print("\033[2K\r\033[1A\033[2K\rPassword Incorrect", 255, 100, 100)

        else:
            _color_print("비밀번호를 생성하세요. 비밀번호를 분실할 경우 저장된 데이터는 절대 복구할 수 없습니다.", 255, 255, 60)
            while True:
                pw1 = input("Create Password: ")

                if not pw1.strip():
                    _color_print("\033[2K\r\033[1A\033[2K\rPassword cannot be empty", red=255, green=100, blue=100)
                    continue

                pw2 = input("Confirm Password: ")

                if pw1 == pw2:
                    break
                else:
                    _color_print("\033[2K\r\033[1A\033[2K\r\033[2K\r\033[1A\033[2K\rPasswords do not match", 255, 100, 100)
            if not CryptoDB.initialize(pw1):
                print(f"\033[2K\033[38;2;255;255;60m초기 db세팅인데 비번이 틀렸다는디??\033[0m", end="", flush=True)
                return

        # 앱 시작
        from nexus_app.core.nexus_app import NexusApp
        app = NexusApp()
        app.run()

    except Exception:
        print("\033[38;2;255;60;60m", end="", flush=True)
        traceback.print_exc()
        print("\033[0m", end="", flush=True)


if __name__ == "__main__":
    main()