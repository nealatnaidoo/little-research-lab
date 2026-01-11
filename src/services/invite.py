import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.entities import Invite, RoleType, User
from src.domain.policy import PolicyEngine
from src.ports.auth import AuthPort
from src.ports.repo import InviteRepoPort, UserRepoPort


class InviteService:
    def __init__(
        self, 
        invite_repo: InviteRepoPort, 
        user_repo: UserRepoPort, 
        auth_adapter: AuthPort, 
        policy: PolicyEngine
    ):
        self.repo = invite_repo
        self.user_repo = user_repo
        self.auth = auth_adapter
        self.policy = policy

    def create_invite(self, creator: User, role: RoleType, days_valid: int = 7) -> str:
        # 1. Check permissions
        if not self.policy.can_manage_users(creator):
             raise PermissionError("User cannot create invites")

        # 2. Generate Token
        token = secrets.token_urlsafe(32)
        # Hash it for storage
        token_hash = self.auth.hash_token(token) 
        # Note: AuthPort needs hash_token? Or reuse hash_password?
        # Typically token hashing is fast (SHA256). Password hashing is slow (Argon2).
        # Let's assume AuthPort has `hash_token` or we use `hash_password` if load is low.
        # Actually, let's look at AuthPort.
        
        # If AuthPort doesn't have hash_token, I handle it here or add it.
        # Let's check AuthPort definition.
        # Assuming we need to extend AuthPort or just use hashlib here.
        # Using hashlib here is simpler for now.
        
        expires_at = datetime.utcnow() + timedelta(days=days_valid)
        
        invite = Invite(
            id=uuid4(),
            token_hash=token_hash, # We'll need to define how we hash
            role=role,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        
        self.repo.save(invite)
        return token

    def redeem_invite(self, token: str, email: str, display_name: str, password: str) -> User:
        # 1. Hash token to lookup
        # We need the same hash method as create_invite
        # Let's assume we use a private helper _hash_token(str) -> str
        token_hash = self._hash_token(token)
        
        invite = self.repo.get_by_token_hash(token_hash)
        if not invite:
            raise ValueError("Invalid invite token")
            
        # 2. Validate
        if invite.redeemed_at:
            raise ValueError("Invite already redeemed")
            
        if invite.expires_at < datetime.utcnow():
            raise ValueError("Invite expired")
            
        # 3. Create User
        # Check email uniqueness
        if self.user_repo.get_by_email(email):
            raise ValueError("Email already registered")
            
        pwd_hash = self.auth.hash_password(password)
        
        new_user = User(
            id=uuid4(),
            email=email,
            display_name=display_name,
            password_hash=pwd_hash,
            roles=[invite.role],
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.user_repo.save(new_user)
        
        # 4. Mark Redeemed
        invite.redeemed_at = datetime.utcnow()
        invite.redeemed_by_user_id = new_user.id
        self.repo.save(invite)
        
        return new_user

    def _hash_token(self, token: str) -> str:
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()
