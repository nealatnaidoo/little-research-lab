from collections.abc import Sequence
from typing import Any

from src.domain.entities import User
from src.rules.models import Rules


class PolicyEngine:
    def __init__(self, rules: Rules):
        self.rules = rules

    def check_permission(
        self, 
        user: User | None, 
        user_roles: Sequence[str], 
        action: str, 
        resource: Any = None,
        context: dict[str, Any] | None = None
    ) -> bool:
        """
        Check if the user/role is allowed to perform the action on the resource.
        
        Order of precedence:
        1. Public Permissions (Global)
        2. Role-Based Access Control (RBAC)
        3. Attribute-Based Access Control (ABAC)
        """
        context = context or {}
        
        # 1. Public Permissions
        if action in self.rules.rbac.public_permissions:
            return True
            
        # If not public, we need a user
        if not user:
            return False
            
        # 2. RBAC
        # Check if any of the user's roles allow this action
        for role in user_roles:
            allowed_actions = self.rules.rbac.roles.get(role, [])
            if "*" in allowed_actions:
                return True
            if action in allowed_actions:
                return True
            
            # Check for scoped wildcards (e.g. "content:*" matches "content:edit")
            if ":" in action:
                scope = action.split(":")[0]
                if f"{scope}:*" in allowed_actions:
                    return True
                
        # 3. ABAC
        # Only relevant if we have a resource to check against
        if resource:
            # Check content edit rules
            for rule in self.rules.abac.content_edit_rules:
                if self._evaluate_rule(rule.if_condition, user, user_roles, resource, context):
                    if action in rule.allow:
                        return True

            # Check asset read rules
            for rule in self.rules.abac.asset_read_rules:
                if self._evaluate_rule(rule.if_condition, user, user_roles, resource, context):
                    if action in rule.allow:
                        return True
                        
        return False

    def _evaluate_rule(
        self, 
        condition: dict[str, Any], 
        user: User, 
        user_roles: Sequence[str],
        resource: Any,
        context: dict[str, Any]
    ) -> bool:
        """
        Evaluate condition predicates from rules.yaml.
        Supported predicates:
        - role_in: list[str]
        - owns_content: bool
        - collaborator_scope_in: list[str]
        """
        for predicate, args in condition.items():
            if predicate == "role_in":
                # Check if intersection of user_roles and allowed roles is not empty
                if not set(user_roles).intersection(set(args)):
                    return False
            
            elif predicate == "owns_content":
                must_own = args
                if must_own:
                    # Check ownership
                    if not hasattr(resource, "owner_user_id"):
                        return False
                    if str(resource.owner_user_id) != str(user.id):
                        return False
            
            elif predicate == "collaborator_scope_in":
                required_scopes = set(args)
                grants = context.get("grants", [])
                # Check if user has any grant with required scope
                # Grants passed in are 'CollaborationGrant' objects for THIS user and THIS resource
                # Caller (ContentService) must ensure 'grants' are filtered for the user.
                has_grant = any(g.scope in required_scopes for g in grants)
                if not has_grant:
                    return False
            
        return True

    def can_manage_users(self, user: User) -> bool:
        return self.check_permission(user, user.roles, "users:manage")

    def can_manage_collaborators(self, user: User, resource: Any) -> bool:
        # Implicit rule: Owner or Admin can manage collaborators
        if "admin" in user.roles or "owner" in user.roles:
            return True
        if hasattr(resource, "owner_user_id") and str(resource.owner_user_id) == str(user.id):
            return True
        return False
