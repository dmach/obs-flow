from core.fingerprint import BasePayload


class PRRevisionPayload(BasePayload):
    base_sha: str
    head_sha: str
    target_branch: str
