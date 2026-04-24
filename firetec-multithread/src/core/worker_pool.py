"""Pool de workers com PriorityQueue e graceful shutdown."""
import queue
import threading
import time
from typing import Callable, List, Tuple


class WorkerPool:
    def __init__(self, max_workers: int, queue_size: int, worker_fn: Callable[[object], None]):
        self.worker_fn = worker_fn
        self.queue: queue.PriorityQueue[Tuple[int, float, object]] = queue.PriorityQueue(maxsize=queue_size)
        self.max_workers = max_workers
        self.shutdown = threading.Event()
        self.workers: List[threading.Thread] = []

    def start(self) -> None:
        for index in range(self.max_workers):
            thread = threading.Thread(target=self._loop, name=f"Worker-{index + 1}", daemon=True)
            thread.start()
            self.workers.append(thread)

    def stop(self, timeout: float = 5.0) -> None:
        self.shutdown.set()
        for worker in self.workers:
            worker.join(timeout=timeout)

    def submit(self, priority: int, payload: object) -> None:
        self.queue.put_nowait((priority, time.time(), payload))

    def size(self) -> int:
        return self.queue.qsize()

    def _loop(self) -> None:
        while not self.shutdown.is_set():
            try:
                _, _, payload = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self.worker_fn(payload)
            finally:
                self.queue.task_done()
