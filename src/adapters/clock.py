from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now()

    def now_utc(self) -> datetime:
        return datetime.now(UTC)

    def is_past_or_now(self, utc_dt: datetime) -> bool:
        return utc_dt <= self.now_utc()

    def is_future(self, utc_dt: datetime, grace_seconds: int = 0) -> bool:
        from datetime import timedelta

        return utc_dt > (self.now_utc() - timedelta(seconds=grace_seconds))
