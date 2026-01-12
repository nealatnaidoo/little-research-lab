## COMPONENT_ID
C-auth

## PURPOSE
Manage user authentication, sessions, and user administration (RBAC).

## INPUTS
- `LoginInput`: Email/Password to authenticate
- `CreateSessionInput`: Create session for authenticated user
- `VerifySessionInput`: Validate token and retrieve user
- `CreateUserInput`: (Admin) Create new user
- `UpdateUserInput`: (Admin) Update user roles/status
- `ListUsersInput`: (Admin) List all users

## OUTPUTS
- `AuthOutput`: User and Session data
- `UserOutput`: Single user data
- `UserListOutput`: List of users

## DEPENDENCIES (PORTS)
- `UserRepoPort`: Persist users
- `AuthPort`: Password hashing and token generation
- `PolicyEngine`: Authorization checks (managed internally or via port)

## SIDE EFFECTS
- Creates/updates User records in DB
- Manages in-memory session store (Note: Should be persistent in production, but following legacy implementation for now)

## INVARIANTS
- I1: Email must be unique
- I2: Admin cannot disable themselves or remove their own admin role
- I3: Passwords are always hashed
