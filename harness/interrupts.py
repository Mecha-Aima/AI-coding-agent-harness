import asyncio
import signal
import threading
from typing import Any, Callable, List, Optional, Union

interrupt_queue: Optional[asyncio.Queue] = None

stream_abort_event = threading.Event()
_loop_for_sigint: Optional[asyncio.AbstractEventLoop] = None
_prev_sigint_handler: Optional[Union[Callable[..., Any], int]] = None

STREAM_INTERRUPT_USER_TEXT = (
    "[INTERRUPT] The user pressed Ctrl+C. Stop, summarize progress, and wait for instructions."
)


def set_interrupt_queue(q: asyncio.Queue) -> None:
    global interrupt_queue
    interrupt_queue = q


def clear_stream_abort() -> None:
    stream_abort_event.clear()


def request_stream_abort() -> None:
    stream_abort_event.set()


def _sigint_during_stream(_signum: int, _frame: object | None) -> None:
    stream_abort_event.set()
    q = interrupt_queue
    loop = _loop_for_sigint
    if q is None or loop is None or not loop.is_running():
        return

    def _enqueue() -> None:
        try:
            q.put_nowait(STREAM_INTERRUPT_USER_TEXT)
        except asyncio.QueueFull:
            pass

    try:
        loop.call_soon_threadsafe(_enqueue)
    except RuntimeError:
        pass


def install_sigint_for_stream_abort(loop: asyncio.AbstractEventLoop) -> Union[Callable[..., Any], int, None]:
    """
    While the Anthropic stream runs in a thread pool, route SIGINT to abort the
    stream and enqueue the same interrupt text used elsewhere.
    Returns the previous handler for restoration, or None if SIGINT could not be hooked.
    """
    global _loop_for_sigint, _prev_sigint_handler
    _loop_for_sigint = loop
    try:
        _prev_sigint_handler = signal.signal(signal.SIGINT, _sigint_during_stream)
        return _prev_sigint_handler
    except (ValueError, OSError):
        _loop_for_sigint = None
        _prev_sigint_handler = None
        return None


def restore_sigint(handler: Union[Callable[..., Any], int, None]) -> None:
    global _loop_for_sigint, _prev_sigint_handler
    if handler is not None:
        try:
            signal.signal(signal.SIGINT, handler)
        except (ValueError, OSError):
            pass
    _loop_for_sigint = None
    _prev_sigint_handler = None


async def drain_interrupts() -> List[str]:
    if interrupt_queue is None:
        return []
    msgs: List[str] = []
    while True:
        try:
            msgs.append(interrupt_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return msgs
