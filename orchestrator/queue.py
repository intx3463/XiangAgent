import queue
import time
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TokenEvent:
    task_id: str
    token_type: Literal["token", "done", "error", "status", "tool_call", "tool_result", "thinking"]
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class TokenQueue:
    """线程安全的 Token 队列，所有子 Agent 的输出汇入此处"""

    def __init__(self):
        self._queue = queue.Queue()
        self._pending = 0

    def put(self, event: TokenEvent):
        self._queue.put(event)
        if event.token_type == "status" and "开始" in event.content:
            self._pending += 1
        elif event.token_type in ("done", "error"):
            self._pending -= 1

    def get(self, timeout: float = 0.1) -> TokenEvent | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def is_all_done(self) -> bool:
        return self._pending == 0 and not self._queue.empty()

    def pending_count(self) -> int:
        return self._pending
