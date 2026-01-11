
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.app_shell.rate_limit import RateLimiter
from src.rules.models import RateLimitRules, RateLimitWindow


@pytest.fixture
def rules():
    return RateLimitRules(
        login=RateLimitWindow(window_seconds=60, max_attempts=3),
        upload=RateLimitWindow(window_seconds=60, max_requests=2)
    )

@pytest.fixture
def limiter(rules):
    return RateLimiter(rules)

def test_allow_request_basic(limiter):
    key = "test_key"
    window = 60
    limit = 2
    
    assert limiter.allow_request(key, window, limit) is True
    assert limiter.allow_request(key, window, limit) is True
    assert limiter.allow_request(key, window, limit) is False  # Limit reached

def test_cleanup_window(limiter):
    key = "test_window"
    window = 1 # 1 second window
    limit = 1
    
    assert limiter.allow_request(key, window, limit) is True
    assert limiter.allow_request(key, window, limit) is False
    
    # Simulate time passing
    # We can patch datetime in the module, but simpler to rely on small window sleep
    # Or just mock datetime.
    # But sleeping 1.1s is safe for unit test provided it's fast enough.
    # Let's mock instead for robustness.
    
    with patch("src.app_shell.rate_limit.datetime") as mock_dt:
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_dt.now.return_value = start_time
        
        # Reset limiter wrapper logic to use mocked time?
        # The limiter imports datetime. 
        # So key is already in history from line above? No, starting fresh check.
        
        # New key for mocked test
        key2 = "mocked"
        
        assert limiter.allow_request(key2, 60, 1) is True
        assert limiter.allow_request(key2, 60, 1) is False
        
        # Move forward 61 seconds
        mock_dt.now.return_value = start_time + timedelta(seconds=61)
        
        # Should be allowed again
        assert limiter.allow_request(key2, 60, 1) is True

def test_check_login(limiter):
    # Configured max=3
    ip = "127.0.0.1"
    assert limiter.check_login(ip) is True
    assert limiter.check_login(ip) is True
    assert limiter.check_login(ip) is True
    assert limiter.check_login(ip) is False

def test_check_upload(limiter):
    # Configured max=2
    uid = "user1"
    assert limiter.check_upload(uid) is True
    assert limiter.check_upload(uid) is True
    assert limiter.check_upload(uid) is False
