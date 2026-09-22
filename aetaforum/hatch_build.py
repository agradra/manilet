from hatchling.builders.hooks.plugin.interface import BuildHookInterface
import subprocess
import os
import shutil
import sys

class RustBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):

        print("Starting Tauri (Rust) compilation...")
        
        frontend_dir = os.path.join(os.path.dirname(__file__), "gui")
        
        # Tauri 빌드 (프론트엔드 + Rust 백엔드)
        try:
            # 윈도우 환경에서는 npm.cmd, 맥/리눅스에서는 npm 사용
            npm_cmd = "npm.cmd" if sys.platform.startswith("win") else "npm"
            subprocess.run([npm_cmd, "run", "tauri", "build"], cwd=frontend_dir, check=True)
        except subprocess.CalledProcessError:
            print("Tauri build failed: Please ensure npm and Rust (Tauri) are installed.")
            raise
            
        # 생성된 실행파일을 aetaforum/bin 경로로 복사
        # 윈도우는 app.exe, 맥/리눅스는 app
        exe_name = "app.exe" if sys.platform.startswith("win") else "app"
        
        exe_src = os.path.join(frontend_dir, "src-tauri", "target", "release", exe_name)
        bin_dir = os.path.join(os.path.dirname(__file__), "aetaforum", "bin")
        exe_dest = os.path.join(bin_dir, exe_name)
        
        os.makedirs(bin_dir, exist_ok=True)
        
        if os.path.exists(exe_src):
            shutil.copy2(exe_src, exe_dest)
            print(f"Build complete. Binary copied to: {exe_dest}")
        else:
            raise FileNotFoundError(f"Tauri build output not found: {exe_src}")
        
        build_data["pure_python"] = False # 패키지 순수 파이썬 아님

        # 'py3-none-any' -> 'cp312-cp312-win_amd64' (운영체제 분석 및 이름 자동 변경)
        if self.target_name == "wheel":
            from packaging.tags import sys_tags
            tag = next(sys_tags())
            tag_string = f"{tag.interpreter}-{tag.abi}-{tag.platform}"
            build_data["tag"] = tag_string