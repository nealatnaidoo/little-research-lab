import hashlib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from src.domain.entities import Asset, ContentVisibility, User
from src.domain.policy import PolicyEngine
from src.ports.filestore import FileStorePort
from src.ports.repo import AssetRepoPort
from src.rules.models import UploadsRules


class AssetService:
    def __init__(
        self,
        repo: AssetRepoPort,
        filestore: FileStorePort,
        policy: PolicyEngine,
        rules: UploadsRules,
    ):
        self.repo = repo
        self.filestore = filestore
        self.policy = policy
        self.rules = rules

    def upload_asset(
        self,
        user: User,
        filename: str,
        mime_type: str,
        data: bytes,
        visibility: ContentVisibility = "private",
    ) -> Asset:
        """
        Uploads an asset, validates it, and saves it to storage and DB.
        """
        # 1. Permission Check
        if not self.policy.check_permission(user, user.roles, "asset:create"):
            raise PermissionError("User not allowed to upload assets.")

        # 2. Validation
        # Size
        if len(data) > self.rules.max_upload_bytes:
            raise ValueError(
                f"File size exceeds limit ({self.rules.max_upload_bytes} bytes)."
            )

        # Extension
        ext = Path(filename).suffix.lower()
        if ext not in self.rules.allowlist_extensions:
            raise ValueError(f"Extension '{ext}' is not allowed.")

        # MIME Type
        if mime_type not in self.rules.allowlist_mime_types:
            raise ValueError(f"MIME type '{mime_type}' is not allowed.")

        # 3. Processing
        sha256_hash = hashlib.sha256(data).hexdigest()

        # Deduplication check?
        # For now, unique ID storage to prevent overwrites, but we store hash for meta.
        # We use UUID to avoid collisions.
        
        asset_id = uuid4()
        storage_name = f"{asset_id}{ext}"

        # 4. Save to Store
        stored_path = self.filestore.save(storage_name, data)

        # 5. Create Entity
        asset = Asset(
            id=asset_id,
            filename_original=filename,
            mime_type=mime_type,
            size_bytes=len(data),
            sha256=sha256_hash,
            storage_path=stored_path,
            visibility=visibility,
            created_by_user_id=user.id,
            created_at=datetime.utcnow(),
        )

        # 6. Save to Repo
        self.repo.save(asset)

        return asset

    def get_asset_meta(self, user: User | None, asset_id: UUID) -> Asset:
        """
        Get asset metadata. Checks permissions.
        """
        asset = self.repo.get_by_id(asset_id)
        if not asset:
            raise ValueError("Asset not found.")

        # Logic for Permission:
        # If public, anyone can read.
        # For now, let's assume 'asset:read' check via policy.

        role: Sequence[str] = user.roles if user else []

        # Check permissions
        # Resource-based check (e.g. ownership) via ABAC
        if not self.policy.check_permission(user, role, "asset:read", resource=asset):
            raise PermissionError("User not allowed to view this asset.")

        return asset

    def get_asset_content(self, user: User | None, asset_id: UUID) -> bytes:
        """
        Get asset content (bytes).
        """
        asset = self.get_asset_meta(user, asset_id)
        return self.filestore.get(asset.storage_path)
