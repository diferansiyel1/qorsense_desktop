"""
Circuit Breaker Pattern Implementation for Modbus Devices.

Prevents cascading failures by temporarily blocking requests to
unresponsive devices, allowing them time to recover while the
rest of the system continues operating.
"""
import time
import threading
from typing import Callable, Optional, Any, Dict
from dataclasses import dataclass, field

from .models import CircuitState, DeviceStatus


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 3          # Failures before opening circuit
    recovery_timeout: float = 10.0      # Seconds before trying half-open
    max_recovery_timeout: float = 60.0  # Maximum backoff timeout
    success_threshold: int = 1          # Successes in half-open to close
    backoff_multiplier: float = 2.0     # Exponential backoff multiplier


@dataclass
class CircuitBreakerStats:
    """Statistics for monitoring circuit breaker behavior."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    state_changes: int = 0
    last_state_change_time: Optional[float] = None


class CircuitBreaker:
    """
    Circuit Breaker implementation for fault-tolerant Modbus communication.
    
    The circuit breaker has three states:
    
    1. **CLOSED**: Normal operation. Requests flow through. If failures exceed
       the threshold, the circuit OPENS.
       
    2. **OPEN**: Device marked offline. All requests are immediately rejected
       without attempting communication. After recovery_timeout, transitions
       to HALF_OPEN.
       
    3. **HALF_OPEN**: A probe request is allowed through to test if the device
       has recovered. If successful, circuit CLOSES. If failed, circuit OPENS
       with increased timeout (exponential backoff).
    
    Example:
        >>> cb = CircuitBreaker("sensor_1")
        >>> 
        >>> def read_sensor():
        ...     # Actual Modbus read
        ...     return 42.0
        >>> 
        >>> # Execute with circuit breaker protection
        >>> result = cb.execute(read_sensor)
        >>> 
        >>> # Check state
        >>> print(cb.state)  # CircuitState.CLOSED
    
    Attributes:
        device_id: Unique identifier for the device
        state: Current circuit state (CLOSED/OPEN/HALF_OPEN)
        config: Circuit breaker configuration
        stats: Runtime statistics
    """

    def __init__(
        self,
        device_id: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None
    ):
        """
        Initialize a circuit breaker for a device.
        
        Args:
            device_id: Unique identifier for the device
            config: Optional configuration (uses defaults if not provided)
            on_state_change: Optional callback(device_id, old_state, new_state)
        """
        self.device_id = device_id
        self.config = config or CircuitBreakerConfig()
        self._on_state_change = on_state_change
        
        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._current_timeout = self.config.recovery_timeout
        self._open_time: Optional[float] = None
        
        # Statistics
        self.stats = CircuitBreakerStats()
        
        # Thread safety
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._check_state_transition()
            return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN

    @property
    def failure_count(self) -> int:
        """Get current consecutive failure count."""
        with self._lock:
            return self._failure_count

    @property
    def time_until_retry(self) -> Optional[float]:
        """
        Get remaining time until next retry attempt (when OPEN).
        
        Returns:
            Seconds until retry, or None if not in OPEN state
        """
        with self._lock:
            if self._state != CircuitState.OPEN or self._open_time is None:
                return None
            elapsed = time.time() - self._open_time
            remaining = self._current_timeout - elapsed
            return max(0.0, remaining)

    def _check_state_transition(self) -> None:
        """Check if state should transition based on timeout (OPEN -> HALF_OPEN)."""
        if self._state == CircuitState.OPEN and self._open_time is not None:
            elapsed = time.time() - self._open_time
            if elapsed >= self._current_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """
        Transition to a new state.
        
        Args:
            new_state: Target state
        """
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        self.stats.state_changes += 1
        self.stats.last_state_change_time = time.time()

        # State-specific initialization
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._current_timeout = self.config.recovery_timeout

        elif new_state == CircuitState.OPEN:
            self._open_time = time.time()
            self._success_count = 0

        elif new_state == CircuitState.HALF_OPEN:
            self._open_time = None
            self._failure_count = 0
            self._success_count = 0

        # Notify callback
        if self._on_state_change:
            try:
                self._on_state_change(self.device_id, old_state, new_state)
            except Exception:
                pass  # Don't let callback errors affect operation

    def record_success(self) -> None:
        """
        Record a successful request.
        
        In CLOSED state, resets failure count.
        In HALF_OPEN state, may transition to CLOSED after enough successes.
        """
        with self._lock:
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self._last_success_time = time.time()
            self._failure_count = 0
            self._success_count += 1

            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def record_failure(self) -> None:
        """
        Record a failed request.
        
        In CLOSED state, may transition to OPEN after threshold failures.
        In HALF_OPEN state, transitions back to OPEN with increased timeout.
        """
        with self._lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self._last_failure_time = time.time()
            self._failure_count += 1
            self._success_count = 0

            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.HALF_OPEN:
                # Increase timeout with exponential backoff
                self._current_timeout = min(
                    self._current_timeout * self.config.backoff_multiplier,
                    self.config.max_recovery_timeout
                )
                self._transition_to(CircuitState.OPEN)

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed through.
        
        Returns:
            True if request should proceed, False if it should be rejected
        """
        with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.HALF_OPEN:
                # Allow one probe request
                return True

            if self._state == CircuitState.OPEN:
                self.stats.rejected_requests += 1
                return False

            return False

    def execute(
        self,
        operation: Callable[[], Any],
        fallback: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        Execute an operation with circuit breaker protection.
        
        Args:
            operation: Function to execute
            fallback: Optional fallback function if circuit is open
            
        Returns:
            Result from operation or fallback
            
        Raises:
            CircuitOpenError: If circuit is open and no fallback provided
            Exception: Any exception from the operation (after recording failure)
        """
        if not self.allow_request():
            if fallback:
                return fallback()
            raise CircuitOpenError(
                f"Circuit breaker OPEN for device '{self.device_id}'. "
                f"Retry in {self.time_until_retry:.1f}s"
            )

        try:
            result = operation()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    def reset(self) -> None:
        """
        Force reset the circuit breaker to CLOSED state.
        
        Use this for manual recovery or testing.
        """
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._current_timeout = self.config.recovery_timeout

    def get_device_status(self) -> DeviceStatus:
        """
        Get device status based on circuit state.
        
        Returns:
            DeviceStatus enum value
        """
        state = self.state
        if state == CircuitState.CLOSED:
            return DeviceStatus.ONLINE
        elif state == CircuitState.OPEN:
            return DeviceStatus.OFFLINE
        else:  # HALF_OPEN
            return DeviceStatus.RECONNECTING

    def get_status_dict(self) -> Dict[str, Any]:
        """
        Get complete status information as dictionary.
        
        Returns:
            Dictionary with all status fields
        """
        with self._lock:
            return {
                "device_id": self.device_id,
                "state": self._state.value,
                "device_status": self.get_device_status().value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "current_timeout": self._current_timeout,
                "time_until_retry": self.time_until_retry,
                "last_success_time": self._last_success_time,
                "last_failure_time": self._last_failure_time,
                "stats": {
                    "total_requests": self.stats.total_requests,
                    "successful_requests": self.stats.successful_requests,
                    "failed_requests": self.stats.failed_requests,
                    "rejected_requests": self.stats.rejected_requests,
                    "state_changes": self.stats.state_changes,
                }
            }


class CircuitOpenError(Exception):
    """Exception raised when circuit breaker is open and request is rejected."""
    pass


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Provides a centralized way to create, access, and monitor
    circuit breakers for multiple devices.
    
    Example:
        >>> registry = CircuitBreakerRegistry()
        >>> cb1 = registry.get_or_create("sensor_1")
        >>> cb2 = registry.get_or_create("sensor_2")
        >>> 
        >>> # Get all open circuits
        >>> open_circuits = registry.get_open_circuits()
    """

    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize the registry.
        
        Args:
            default_config: Default configuration for new circuit breakers
        """
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = default_config or CircuitBreakerConfig()
        self._lock = threading.RLock()
        self._on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None

    def set_state_change_callback(
        self,
        callback: Callable[[str, CircuitState, CircuitState], None]
    ) -> None:
        """
        Set a global callback for all state changes.
        
        Args:
            callback: Function(device_id, old_state, new_state)
        """
        self._on_state_change = callback

    def get_or_create(
        self,
        device_id: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get existing or create new circuit breaker for a device.
        
        Args:
            device_id: Unique device identifier
            config: Optional specific configuration
            
        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if device_id not in self._breakers:
                self._breakers[device_id] = CircuitBreaker(
                    device_id=device_id,
                    config=config or self._default_config,
                    on_state_change=self._on_state_change
                )
            return self._breakers[device_id]

    def get(self, device_id: str) -> Optional[CircuitBreaker]:
        """
        Get circuit breaker for a device if it exists.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            CircuitBreaker or None if not found
        """
        with self._lock:
            return self._breakers.get(device_id)

    def remove(self, device_id: str) -> bool:
        """
        Remove a circuit breaker from the registry.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if device_id in self._breakers:
                del self._breakers[device_id]
                return True
            return False

    def get_all(self) -> Dict[str, CircuitBreaker]:
        """
        Get all registered circuit breakers.
        
        Returns:
            Dictionary of device_id -> CircuitBreaker
        """
        with self._lock:
            return dict(self._breakers)

    def get_open_circuits(self) -> Dict[str, CircuitBreaker]:
        """
        Get all circuit breakers in OPEN state.
        
        Returns:
            Dictionary of device_id -> CircuitBreaker for open circuits
        """
        with self._lock:
            return {
                device_id: cb
                for device_id, cb in self._breakers.items()
                if cb.is_open
            }

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get summary status of all circuit breakers.
        
        Returns:
            Dictionary with counts by state and details
        """
        with self._lock:
            states = {
                CircuitState.CLOSED: 0,
                CircuitState.OPEN: 0,
                CircuitState.HALF_OPEN: 0
            }
            
            for cb in self._breakers.values():
                states[cb.state] += 1

            return {
                "total_devices": len(self._breakers),
                "closed": states[CircuitState.CLOSED],
                "open": states[CircuitState.OPEN],
                "half_open": states[CircuitState.HALF_OPEN],
                "devices": {
                    device_id: cb.get_status_dict()
                    for device_id, cb in self._breakers.items()
                }
            }

    def reset_all(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        with self._lock:
            for cb in self._breakers.values():
                cb.reset()
