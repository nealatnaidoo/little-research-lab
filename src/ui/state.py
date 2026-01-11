from dataclasses import dataclass

from src.domain.entities import Session, User


@dataclass
class AppState:
    current_user: User | None = None
    current_session: Session | None = None
    
    def logout(self) -> None:
        self.current_user = None
        self.current_session = None

