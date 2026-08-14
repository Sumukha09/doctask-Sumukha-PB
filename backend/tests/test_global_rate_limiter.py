import time
import concurrent.futures
from app.llm.limiter import GlobalRateLimiter

def test_global_rate_limiter_spacing():
    """Verify that the rate limiter perfectly spaces out concurrent requests."""
    limiter = GlobalRateLimiter()
    max_rpm = 60  # 1 request per second (interval = 1.0s)
    num_requests = 5
    
    start_time = time.time()
    
    def worker():
        return limiter.wait_if_needed(max_rpm)
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all tasks simultaneously
        futures = [executor.submit(worker) for _ in range(num_requests)]
        results = [f.result() for f in futures]
        
    end_time = time.time()
    total_elapsed = end_time - start_time
    
    # 5 requests at 1 req/sec:
    # T1 waits 0s
    # T2 waits 1s
    # T3 waits 2s
    # T4 waits 3s
    # T5 waits 4s
    # Total wait time should be ~10s.
    
    assert sum(results) >= 9.5
    # The entire block should take at least 4.0 seconds (since the 5th thread sleeps 4s).
    assert total_elapsed >= 4.0
    
def test_global_rate_limiter_zero_rpm():
    """Verify that max_rpm=0 bypasses the limiter."""
    limiter = GlobalRateLimiter()
    wait = limiter.wait_if_needed(0)
    assert wait == 0.0
