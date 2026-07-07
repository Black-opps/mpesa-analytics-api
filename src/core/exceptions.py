# src/core/exceptions.py - NEW


class MpesaAnalyticsError(Exception):
    """Base exception"""

    pass


class DuplicateUploadError(MpesaAnalyticsError):
    """Upload already processed"""

    def __init__(self, upload_id: str):
        self.upload_id = upload_id
        super().__init__(f"Upload {upload_id} already processed")


class SnapshotCorruptionError(MpesaAnalyticsError):
    """Snapshot corrupted"""

    def __init__(self, tenant_id: str, reason: str):
        self.tenant_id = tenant_id
        self.reason = reason
        super().__init__(f"Snapshot corrupted: {reason}")


class AnalyticsRefreshError(MpesaAnalyticsError):
    """Refresh failed"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Analytics refresh failed: {reason}")


class LockAcquisitionError(MpesaAnalyticsError):
    """Could not acquire lock"""

    def __init__(self, lock_key: str):
        self.lock_key = lock_key
        super().__init__(f"Could not acquire lock: {lock_key}")
