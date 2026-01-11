from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectRules(BaseModel):
    slug: str
    rules_version: str
    required_sections: list[str]

class CsrfRules(BaseModel):
    enabled: bool
    mode: str

class SecurityRules(BaseModel):
    fail_fast_on_invalid_rules: bool
    allowed_link_protocols: list[str]
    disallowed_markdown_features: list[str]
    csrf: CsrfRules

class PasswordHashingRules(BaseModel):
    algorithm: str
    min_length: int

class SessionCookieRules(BaseModel):
    secure: bool
    http_only: bool
    same_site: str

class SessionsRules(BaseModel):
    ttl_minutes: int
    rotate_on_login: bool
    store_tokens_hashed: bool
    cookie: SessionCookieRules

class AuthRules(BaseModel):
    password_hashing: PasswordHashingRules
    sessions: SessionsRules

class RbacRules(BaseModel):
    roles: dict[str, list[str]]
    public_permissions: list[str]

class AbacRule(BaseModel):
    if_condition: dict[str, Any] = Field(alias="if")
    allow: list[str]

    model_config = ConfigDict(populate_by_name=True)

class AbacRules(BaseModel):
    content_edit_rules: list[AbacRule]
    asset_read_rules: list[AbacRule]

class RangeRule(BaseModel):
    min: int
    max: int

class RegexRule(RangeRule):
    pattern: str

class ContentRules(BaseModel):
    slug: RegexRule
    title: RangeRule
    summary: dict[str, int] # max: 280
    visibility_values: list[str]
    status_values: list[str]

class BlockProperty(BaseModel):
    type: str | None = None
    min: int | None = None
    max: int | None = None
    max_bytes: int | None = None

class BlockSchema(BaseModel):
    required: list[str]
    properties: dict[str, BlockProperty]

class BlocksRules(BaseModel):
    allowed_types: list[str]
    max_blocks_per_item: int
    schemas: dict[str, BlockSchema]

class UploadsRules(BaseModel):
    max_upload_bytes: int
    allowlist_mime_types: list[str]
    allowlist_extensions: list[str]
    quarantine: dict[str, bool]

class EmbedProvider(BaseModel):
    provider: str
    match: str

class EmbedsRules(BaseModel):
    allowlist: list[EmbedProvider]
    deny_if_not_allowlisted: bool

class SchedulingRules(BaseModel):
    publish_check_mode: list[str]
    max_scheduled_days_ahead: int
    allow_backdate_publish_at: bool

class RateLimitWindow(BaseModel):
    window_seconds: int
    max_attempts: int | None = None
    max_requests: int | None = None

class RateLimitRules(BaseModel):
    login: RateLimitWindow
    upload: RateLimitWindow

class BackupsRules(BaseModel):
    include: list[str]
    backup_dir_name: str
    retention_count: int

class AdminBootstrapRules(BaseModel):
    enabled_if_no_users: bool
    required_env_when_enabled: list[str]

class OpsRules(BaseModel):
    data_dir_required: bool
    required_env: list[str]
    bootstrap_admin: AdminBootstrapRules
    backups: BackupsRules

class Rules(BaseModel):
    project: ProjectRules
    security: SecurityRules
    auth: AuthRules
    rbac: RbacRules
    abac: AbacRules
    content: ContentRules
    blocks: BlocksRules
    uploads: UploadsRules
    embeds: EmbedsRules
    scheduling: SchedulingRules
    rate_limits: RateLimitRules
    ops: OpsRules
