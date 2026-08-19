"""
Connection-retry helper for outbound HTTP to Meta / Facebook Graph API.

This VPS has flaky upstream routing to Facebook's network (AS32934): a large
share of TCP connects to graph.facebook.com fail with "No route to host" /
connection timeout, while other destinations (Groq, Telegram, Discord) are
fine. Retrying re-resolves DNS and re-dials, usually landing on a reachable
Facebook edge after a few attempts.

We retry ONLY on connection-level failures. Once any HTTP response is received
(even 4xx/5xx), it is returned unchanged — real API errors are NOT retried.
"""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

# Connection-level failures worth retrying (routing/timeout, not HTTP errors).
_RETRYABLE = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)

# Short connect timeout so a hung dial fails fast and we can re-dial another IP.
_DEFAULT_TIMEOUT = httpx.Timeout(connect=6.0, read=25.0, write=25.0, pool=6.0)


def request_with_retries(
    method: str,
    url: str,
    *,
    attempts: int = 10,
    base_delay: float = 0.5,
    max_delay: float = 4.0,
    timeout: httpx.Timeout | float | None = None,
    **kwargs,
) -> httpx.Response:
    """
    Execute an httpx request, retrying on connection-level failures only.

    A fresh httpx.Client is used per attempt so DNS is re-resolved each time
    (important — the bad Facebook IP often rotates out on the next lookup).

    Raises the last connection exception if every attempt fails.
    """
    last_exc: Exception | None = None
    to = timeout if timeout is not None else _DEFAULT_TIMEOUT

    for i in range(1, attempts + 1):
        try:
            with httpx.Client(timeout=to) as client:
                return client.request(method, url, **kwargs)
        except _RETRYABLE as exc:
            last_exc = exc
            if i < attempts:
                delay = min(base_delay * (2 ** (i - 1)), max_delay)
                logger.warning(
                    "Outbound %s %s attempt %d/%d failed (%s); retrying in %.1fs",
                    method, url.split("?")[0], i, attempts, type(exc).__name__, delay,
                )
                time.sleep(delay)

    logger.error(
        "Outbound %s %s failed after %d attempts: %s",
        method, url.split("?")[0], attempts, last_exc,
    )
    assert last_exc is not None
    raise last_exc
