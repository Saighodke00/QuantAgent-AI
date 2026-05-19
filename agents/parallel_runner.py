"""
Parallel runner — fires background agents in a daemon thread so the
main LangGraph pipeline is never blocked waiting for Strategist results.

Usage:
    task = BackgroundTask().start(generate_suggestions, prompt, ticker, name)
    # ... do expensive work ...
    result = task.wait(timeout=10.0)   # already done by the time you call this
"""
import threading
from typing import Callable, Any


class BackgroundTask:
    """
    Runs any callable in a daemon thread and lets you collect the result later.
    Thread is daemon so it never blocks app shutdown.
    """

    def __init__(self):
        self.result: Any = None
        self.done: bool = False
        self.error: str | None = None
        self._thread: threading.Thread | None = None

    def start(self, fn: Callable, *args, **kwargs) -> "BackgroundTask":
        """Kick off `fn(*args, **kwargs)` in a background daemon thread."""
        def _run():
            try:
                self.result = fn(*args, **kwargs)
            except Exception as e:
                self.error = str(e)
                self.result = None
            finally:
                self.done = True

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        return self  # fluent API: BackgroundTask().start(fn, ...)

    def wait(self, timeout: float = 30.0) -> Any:
        """Block until the task finishes (or timeout) and return the result."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        return self.result
