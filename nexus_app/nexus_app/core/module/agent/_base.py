from nexus_app.core.module.base import Pane
from ._agent_list import AgentListPane

class AgPane(Pane):
    """
    에이전트 선택 상태(now_agent_name)를 공유받아야 하는 모든 Pane의 부모 클래스.
    자식 클래스의 on_mount가 완료된 후 자동으로 AgentListPane과의 watch를 연결합니다.

    Note:
        watch_now_agent_name(self, new_name: str | None) -> None
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 자식 클래스가 watch_now_agent_name을 구현하지 않았으면 앱 실행 시점에 즉시 에러 발생
        if "watch_now_agent_name" not in cls.__dict__:
            raise TypeError(f"'{cls.__name__}' 클래스는 'watch_now_agent_name' 메서드를 반드시 구현해야 합니다.")

    def on_mount(self) -> None:
        if hasattr(super(), "on_mount"):
            super().on_mount() # type: ignore

        try:
            list_pane = self.app.query_one(AgentListPane)
            self.watch(list_pane, "now_agent_name", self.watch_now_agent_name) # type: ignore
        except Exception:
            pass
