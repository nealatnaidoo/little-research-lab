## COMPONENT_ID
C-collab

## PURPOSE
Manage collaboration grants for content items.

## INPUTS
- `GrantAccessInput`: Grant access to a user
- `RevokeAccessInput`: Revoke access from a user
- `ListCollaboratorsInput`: List collaborators for content
- `CheckAccessInput`: Check if user has access

## OUTPUTS
- `CollabOutput`: Grant data
- `CollabListOutput`: List of collaborators
- `AccessCheckOutput`: Boolean result

## DEPENDENCIES (PORTS)
- `CollabRepoPort`: Persist grants
- `ContentRepoPort`: Verify content existence/ownership
- `UserRepoPort`: Verify target users
- `PolicyEngine`: Authorization checks

## SIDE EFFECTS
- Creates/deletes CollaborationGrant records

## INVARIANTS
- I1: Owner cannot be added as collaborator (already has full access)
- I2: Duplicate grants update existing scope
