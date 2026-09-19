from hatchling.builders.hooks.plugin.interface import BuildHookInterface
import subprocess

class RustBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):

        print("Rust 코어 엔진 컴파일 시작...")
        try:
            subprocess.run(["cargo", "build", "--release"], check=True)
        except subprocess.CalledProcessError:
            print("Rust 빌드 실패: Cargo가 설치되어 있는지 확인하세요.")
            raise
        
        build_data["pure_python"] = False # 패키지 순수 파이썬 아님

        # 'py3-none-any' -> 'cp312-cp312-win_amd64' (운영체제 분석 및 이름 자동 변경)
        if self.target_name == "wheel":
            from packaging.tags import sys_tags
            tag = next(sys_tags())
            tag_string = f"{tag.interpreter}-{tag.abi}-{tag.platform}"
            build_data["tag"] = tag_string