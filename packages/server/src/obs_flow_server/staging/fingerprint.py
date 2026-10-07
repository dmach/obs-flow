from core.fingerprint import BasePayload


class StagingBatchPayload(BasePayload):
    pr_revisions: list[str] = []
