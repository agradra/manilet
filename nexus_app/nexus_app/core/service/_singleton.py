from threading import RLock


class Singleton(type):
    _sgt_instances = {}
    _sgt_locks = {}
    _sgt_global_lock = RLock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._sgt_instances:
            # 각 클래스 전용 RLock 생성 (동일 스레드 재진입 허용)
            with cls._sgt_global_lock:
                if cls not in cls._sgt_locks:
                    cls._sgt_locks[cls] = RLock()

            # 해당 클래스 전용 락으로 인스턴스 생성
            with cls._sgt_locks[cls]:
                if cls not in cls._sgt_instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._sgt_instances[cls] = instance

        return cls._sgt_instances[cls]
