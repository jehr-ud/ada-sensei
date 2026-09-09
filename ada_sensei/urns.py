from __future__ import annotations

import hashlib
import uuid


class URN:
    @staticmethod
    def make(kind: str, uid: str | None = None) -> str:
        return f"{kind}://{uid or uuid.uuid4()}"

    @staticmethod
    def parse(uri: str) -> tuple[str, str]:
        kind, _, uid = uri.partition("://")
        if not uid:
            raise ValueError(f"invalid urn: {uri!r}")
        return kind, uid

    @staticmethod
    def project_id_from_path(path: str) -> str:
        digest = hashlib.sha256(path.encode("utf-8")).hexdigest()
        return f"project://{digest}"
