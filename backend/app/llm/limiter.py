"""Centralized global rate limiter for LLM requests."""
import time
import threading

class GlobalRateLimiter:
    """A thread-safe chronological wait-queue rate limiter."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.last_called = 0.0

    def wait_if_needed(self, max_rpm: int) -> float:
        """Wait until it is this thread's turn to execute.
        
        Returns:
            The amount of time (in seconds) the thread slept.
        """
        if max_rpm <= 0:
            return 0.0
            
        min_interval = 60.0 / max_rpm
        
        with self.lock:
            now = time.time()
            next_allowed = max(now, self.last_called + min_interval)
            self.last_called = next_allowed
            
        sleep_time = next_allowed - now
        if sleep_time > 0:
            time.sleep(sleep_time)
            
        return max(0.0, sleep_time)


# Global singletons
GLOBAL_LIMITER = GlobalRateLimiter()

GLOBAL_METRICS = {
    "gemini_requests": 0,
    "gemini_rate_limited": 0,
    "gemini_retries": 0,
    "gemini_wait_seconds": 0.0
}
