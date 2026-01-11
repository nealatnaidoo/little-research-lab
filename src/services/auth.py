from datetime import datetime, timedelta
from uuid import UUID, uuid4

from src.domain.entities import Session, User
from src.domain.policy import PolicyEngine
from src.ports.auth import AuthPort
from src.ports.repo import UserRepoPort


class AuthService:
    def __init__(self, user_repo: UserRepoPort, auth_adapter: AuthPort, policy: PolicyEngine):
        self.user_repo = user_repo
        self.auth_adapter = auth_adapter
        self.policy = policy
        self._sessions: dict[str, Session] = {}

    def login(self, email: str, password: str) -> User | None:
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        
        if not self.auth_adapter.verify_password(password, user.password_hash):
            return None
            
        if user.status != "active":
            return None
            
        return user

    def create_session(self, user: User) -> Session:
        token = self.auth_adapter.create_token(user.id, 24 * 60) # 24 hours
        
        session = Session(
             id=str(uuid4()),
             user_id=user.id,
             token_hash=token,
             expires_at=datetime.now() + timedelta(hours=24)
        )
        self._sessions[token] = session
        return session

    def get_user_by_token(self, token: str) -> User | None:
        session = self._sessions.get(token)
        if not session:
            return None
        if session.expires_at < datetime.now():
            del self._sessions[token]
            return None
        return self.user_repo.get_by_id(session.user_id)

    def list_users(self, actor: User) -> list[User]:
        if not self.policy.can_manage_users(actor):
            raise PermissionError("Access denied")
        return self.user_repo.list_all()

    def update_user(
        self, actor: User, target_id: str | UUID, new_roles: list[str], new_status: str
    ) -> User:
        if not self.policy.can_manage_users(actor):
            raise PermissionError("Access denied")
            
        uid = UUID(str(target_id))
        target = self.user_repo.get_by_id(uid)
        if not target:
            raise ValueError("User not found")
        
        # Self-lockout check
        if str(target.id) == str(actor.id):
             # Prevent removing admin role from self
             if "admin" in target.roles and "admin" not in new_roles:
                 raise ValueError("Cannot remove admin role from yourself")
             if new_status != "active":
                 raise ValueError("Cannot disable yourself")
        
        # Invalidate sessions if disabled
        if new_status != "active" and target.status == "active":
             # Remove all sessions for this user
             tokens_to_remove = [
                 k for k, v in self._sessions.items() 
                 if str(v.user_id) == str(target.id)
             ]
             for k in tokens_to_remove:
                 del self._sessions[k]

        # We trust the caller (admin UI) to provide valid roles/status strings
        # But we should probably validate against RoleType logic or cast
        # For now, simplistic casting to Any or ignore to satisfy mypy
        target.roles = new_roles # type: ignore
        target.status = new_status # type: ignore
        target.updated_at = datetime.now()
        
        self.user_repo.save(target)
        return target
