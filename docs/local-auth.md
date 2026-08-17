# Local Authentication

HackerGPT Local uses a local-first single-user auth layer.

Defaults:

- username: `admin`
- password: `admin987`

The bootstrap account is seeded by the backend if it does not already exist. The password is stored as a PBKDF2-HMAC hash with a per-user salt; plaintext credentials are not stored in the database and are not checked in frontend code.

Session behavior:

- `POST /api/v1/auth/login` verifies credentials and sets a signed httpOnly cookie.
- `POST /api/v1/auth/change-password` verifies the current password, hashes the new password, bumps
  a password revision, and issues a fresh signed cookie.
- `GET /api/v1/auth/me` restores the current session.
- `POST /api/v1/auth/logout` clears the cookie.
- protected `/api/v1/*` APIs require the session cookie when auth is enabled.

Signed session tokens include a password revision. After a password change, older cookies with the
previous revision no longer authenticate.

Configuration:

- `BOOTSTRAP_ADMIN_USERNAME`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `HACKERGPT_BOOTSTRAP_ADMIN_USERNAME`
- `HACKERGPT_BOOTSTRAP_ADMIN_PASSWORD`
- `HACKERGPT_AUTH_SESSION_SECRET`

The generated session secret is stored under the local data directory when no secret is configured. This auth layer does not replace ToolRegistry, PermissionService, confirmations, active scopes, path controls, network controls, or audit logs.
