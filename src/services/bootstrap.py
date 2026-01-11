
import os
import sys
from datetime import datetime
from uuid import uuid4

from src.domain.entities import User
from src.ui.context import ServiceContext


def bootstrap_system(ctx: ServiceContext) -> None:
    """
    Check if system needs bootstrapping (Day 0) and create owner account if configured.
    """
    rules = ctx.rules
    
    # 1. Check if bootstrap is enabled
    if not rules.ops.bootstrap_admin.enabled_if_no_users:
        return

    # 2. Check if users exist
    # Using list_all is expensive if many users, but fine for bootstrap check (expecting 0)
    users = ctx.auth_service.user_repo.list_all()
    if len(users) > 0:
        return

    # 3. Attempt Bootstrap
    email = os.environ.get("LRL_BOOTSTRAP_EMAIL")
    password = os.environ.get("LRL_BOOTSTRAP_PASSWORD")
    
    
    if not email or not password:
        print(
            "BOOTSTRAP INFO: System is empty but LRL_BOOTSTRAP_EMAIL/PASSWORD not set. "
            "Skipping owner creation."
        )
        return
        
    print(f"BOOTSTRAP: Creating owner account for {email}...")
    
    try:
        # We need to bypass AuthService.create_user permissions check (requires actor).
        # Inspect AuthService to see if we can use an internal method or if we must use 
        # repo directly + hashing. Ideall, use Service logic to ensure hashing etc.
        
        password_hash = ctx.auth_service.auth_adapter.hash_password(password)
        
        owner = User(
            id=uuid4(),
            email=email,
            display_name="Owner (Bootstrap)",
            password_hash=password_hash,
            roles=["owner"],
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        
        ctx.auth_service.user_repo.save(owner)
        print("BOOTSTRAP: Owner account created successfully.")
        
    except Exception as e:
        print(f"BOOTSTRAP ERROR: Failed to create owner. {e}", file=sys.stderr)
