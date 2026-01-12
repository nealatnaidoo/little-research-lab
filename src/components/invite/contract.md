## COMPONENT_ID
C-invite

## PURPOSE
Manage invite tokens for user registration.

## INPUTS
- `CreateInviteInput`: Create a new invite token
- `RedeemInviteInput`: Redeem a token to create a user

## OUTPUTS
- `InviteOutput`: Token string
- `RedeemOutput`: Created user

## DEPENDENCIES (PORTS)
- `InviteRepoPort`: Store invites
- `UserRepoPort`: Store users
- `AuthPort`: Hash tokens and passwords

## PRE-CONDITIONS
- Only Admins can create invites
- Token must be valid and unexpired to redeem

## SIDE EFFECTS
- Creates Invite records
- Creates User records on redemption
