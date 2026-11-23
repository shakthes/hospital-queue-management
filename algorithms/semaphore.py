"""
Semaphore Module — OS Concept Implementation
Demonstrates: Counting Semaphore & Mutual Exclusion (Mutex)
"""

import threading
import time
from typing import Optional


class CountingSemaphore:
    """
    Counting Semaphore — OS synchronization primitive.
    
    Used to control access to a finite pool of resources (doctors).
    
    Key Operations:
    - wait()   / P() / down() → Decrements the count. Blocks if count == 0.
    - signal() / V() / up()   → Increments the count. Wakes one blocked thread.
    
    Real-world analogy:
    - Semaphore count = number of available doctors (CPUs)
    - Each P() call → one doctor becomes busy
    - Each V() call → one doctor becomes free
    
    OS textbook: Dijkstra's Semaphore (1965)
    """

    def __init__(self, initial_count: int, max_count: Optional[int] = None):
        if initial_count < 0:
            raise ValueError("Semaphore count cannot be negative")
        self._count     = initial_count
        self._max_count = max_count or initial_count
        self._mutex     = threading.Lock()
        self._condition = threading.Condition(self._mutex)
        self._waiters   = 0
        self._history   : list = []   # Audit log for education

    def wait(self, timeout: float = None) -> bool:
        """
        P() operation — acquire one resource unit.
        
        Args:
            timeout: Max seconds to block. None = block indefinitely.
                     0 = non-blocking (return False immediately if unavailable).
        
        Returns:
            True  → resource acquired
            False → timed out or non-blocking and unavailable
        """
        with self._condition:
            if self._count <= 0:
                if timeout == 0:
                    return False
                self._waiters += 1
                result = self._condition.wait(timeout=timeout)
                self._waiters -= 1
                if not result or self._count <= 0:
                    return False
            self._count -= 1
            self._log("P(wait)", self._count)
            return True

    def signal(self):
        """
        V() operation — release one resource unit.
        Wakes one waiting thread if any are blocked.
        """
        with self._condition:
            if self._max_count and self._count >= self._max_count:
                raise ValueError("Semaphore released more times than acquired")
            self._count += 1
            self._log("V(signal)", self._count)
            self._condition.notify()

    def _log(self, operation: str, count_after: int):
        self._history.append({
            "operation":   operation,
            "count_after": count_after,
            "timestamp":   time.strftime("%H:%M:%S"),
            "thread":      threading.current_thread().name,
        })
        if len(self._history) > 200:
            self._history = self._history[-200:]

    @property
    def count(self) -> int:
        return self._count

    @property
    def waiting_threads(self) -> int:
        return self._waiters

    def get_history(self) -> list:
        return self._history[-50:]

    def __repr__(self):
        return f"Semaphore(count={self._count}, waiters={self._waiters})"


class MutexLock:
    """
    Binary Semaphore / Mutex — OS synchronization primitive.
    
    Ensures mutual exclusion: only one thread can access
    the critical section at a time.
    
    Usage: Prevents two patients from being assigned
    to the same doctor simultaneously.
    """

    def __init__(self, name: str = "mutex"):
        self._name     = name
        self._sem      = CountingSemaphore(1, max_count=1)
        self._owner    : Optional[str] = None

    def acquire(self, owner: str = "unknown", timeout: float = None) -> bool:
        """Lock the mutex. Returns False if already locked."""
        result = self._sem.wait(timeout=timeout or 0)
        if result:
            self._owner = owner
        return result

    def release(self):
        """Unlock the mutex."""
        self._owner = None
        self._sem.signal()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()

    @property
    def is_locked(self) -> bool:
        return self._sem.count == 0

    @property
    def owner(self) -> Optional[str]:
        return self._owner

    def __repr__(self):
        status = f"LOCKED by {self._owner}" if self.is_locked else "UNLOCKED"
        return f"Mutex({self._name}, {status})"
