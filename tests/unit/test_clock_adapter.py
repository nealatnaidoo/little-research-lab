from datetime import datetime

from src.adapters.clock import SystemClock


def test_system_clock():
    clock = SystemClock()
    now = clock.now()
    assert isinstance(now, datetime)
    # Sanity check: is it close to real now?
    real_now = datetime.now()
    diff = abs((real_now - now).total_seconds())
    assert diff < 1.0 # Should be very fast
