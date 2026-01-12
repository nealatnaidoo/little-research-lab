import hashlib
import secrets
from datetime import timedelta
from uuid import uuid4

from src.domain.entities import Invite, User
from src.domain.policy import PolicyEngine
from src.ports.repo import (
    UserRepoPort,  # Reusing UserRepoPort definition from global/collab context if compatible
)

from .models import CreateInviteInput, InviteOutput, RedeemInviteInput, RedeemOutput
from .ports import AuthAdapterPort, InviteRepoPort, TimePort


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def run_create(
    inp: CreateInviteInput,
    invite_repo: InviteRepoPort,
    policy: PolicyEngine,
    time: TimePort,
) -> InviteOutput:
    if not policy.can_manage_users(inp.creator):
        return InviteOutput(success=False, error="User cannot create invites")

    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    now = time.now_utc()

    expires_at = now + timedelta(days=inp.days_valid)

    invite = Invite(
        id=uuid4(),
        token_hash=token_hash,
        role=inp.role,
        expires_at=expires_at,
        created_at=now,
    )

    invite_repo.save(invite)
    return InviteOutput(token=token, success=True)


def run_redeem(
    inp: RedeemInviteInput,
    invite_repo: InviteRepoPort,
    user_repo: UserRepoPort,
    auth_adapter: AuthAdapterPort,
    time: TimePort,
) -> RedeemOutput:
    token_hash = _hash_token(inp.token)
    invite = invite_repo.get_by_token_hash(token_hash)

    if not invite:
        return RedeemOutput(success=False, error="Invalid invite token")

    if invite.redeemed_at:
        return RedeemOutput(success=False, error="Invite already redeemed")

    now = time.now_utc()
    if invite.expires_at < now:
        return RedeemOutput(success=False, error="Invite expired")

    if user_repo.get_by_email(inp.email):
        return RedeemOutput(success=False, error="Email already registered")

    pwd_hash = auth_adapter.hash_password(inp.password)

    new_user = User(
        id=uuid4(),
        email=inp.email,
        display_name=inp.display_name,
        password_hash=pwd_hash,
        roles=[invite.role],
        status="active",
        created_at=now,
        updated_at=now,
    )

    user_repo.save(new_user)

    invite.redeemed_at = now
    invite.redeemed_by_user_id = new_user.id
    invite_repo.save(invite)

    return RedeemOutput(user=new_user, success=True)


def run(
    inp: CreateInviteInput | RedeemInviteInput,
    *,
    invite_repo: InviteRepoPort,
    user_repo: UserRepoPort | None = None,  # Only needed for redeem
    auth_adapter: AuthAdapterPort | None = None,  # Only needed for redeem
    policy: PolicyEngine | None = None,  # Only needed for create
    time: TimePort | None = None,
) -> InviteOutput | RedeemOutput:
    if isinstance(inp, CreateInviteInput):
        assert policy and time
        return run_create(inp, invite_repo, policy, time)

    elif isinstance(inp, RedeemInviteInput):
        assert user_repo and auth_adapter and time
        return run_redeem(inp, invite_repo, user_repo, auth_adapter, time)

    else:
        raise ValueError(f"Unknown input type: {type(inp)}")
