"""Circuit breaker pattern for inter-service resilience.

Prevents cascading failures by temporarily stopping requests to
unhealthy downstream services. Implements the half-open state
to automatically recover when the service becomes healthy again.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    def __init__(self, service: str, state: CircuitState):
        self.service = service
        self.state = state
        super().__init__(
            f"Circuit breaker for '{service}' is {state.value}. Service temporarily unavailable."
        )


class CircuitBreaker:
    """Circuit breaker for a single downstream service.

    States:
    - CLOSED: Normal operation, requests pass through.
    - OPEN: Service is failing, requests fail fast.
    - HALF_OPEN: Allow one probe request to test recovery.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(
                    "Circuit '%s' transitioning to HALF_OPEN", self.name
                )
        return self._state

    @property
    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if not self.is_available:
            raise CircuitBreakerError(self.name, self.state)

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except CircuitBreakerError:
            raise
        except Exception as exc:
            await self._on_failure()
            logger.warning(
                "Circuit '%s' call failed: %s (failures=%d)",
                self.name, exc, self._failure_count,
            )
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(self.name, self.state)
            raise

    async def _on_success(self):
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info("Circuit '%s' CLOSED - service recovered", self.name)
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit '%s' OPEN - probe request failed", self.name
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        "Circuit '%s' OPEN after %d failures",
                        self.name, self._failure_count,
                    )

    async def reset(self):
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            logger.info("Circuit '%s' manually reset", self.name)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 3,
    ) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
            )
        return self._breakers[name]

    def reset_all(self):
        for breaker in self._breakers.values():
            asyncio.create_task(breaker.reset())


registry = CircuitBreakerRegistry()
