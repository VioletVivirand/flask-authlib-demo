# Flask + GitHub OAuth POC

A minimal Flask application that demonstrates the **OAuth 2.0 Authorization Code flow** end-to-end against GitHub. The home page shows a single "Login with GitHub" button; after authorization, the same page shows `Welcome, {name}!` and a Logout button.

## Prerequisites

- Python ≥ 3.14.4
- [uv](https://docs.astral.sh/uv/) for dependency management
- A GitHub account

## 1. Register a GitHub OAuth App

1. Go to GitHub → click your avatar → **Settings**
2. Sidebar → **Developer settings** → **OAuth Apps** → **New OAuth App**
3. Fill in:
   - **Application name**: anything, e.g. `flask-oauth-poc`
   - **Homepage URL**: `http://127.0.0.1:5000`
   - **Authorization callback URL**: `http://127.0.0.1:5000/auth/callback` (must match exactly)

   Note: use `127.0.0.1` rather than `localhost`. Flask's dev server binds to `127.0.0.1` by default, and OAuth providers match redirect URIs as literal strings (RFC 6749 §3.1.2), so the registered URL must match exactly what the browser sends. RFC 8252 §7.3 also recommends loopback IP literals over `localhost` to avoid DNS/`/etc/hosts` quirks.
4. Click **Register application**
5. Copy the **Client ID**
6. Click **Generate a new client secret** → copy it immediately (only shown once)

## 2. Configure environment variables

```bash
cp .env.example .env
```

Then fill in `.env`:

```
FLASK_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
GITHUB_CLIENT_ID=<from step 1>
GITHUB_CLIENT_SECRET=<from step 1>
```

`.env` is gitignored. `uv.lock` is committed.

## 3. Install and run

```bash
uv sync
uv run flask --app app run
```

Open http://127.0.0.1:5000.

## OAuth flow walk-through

The app implements the standard Authorization Code flow. Reading `app.py` top-to-bottom:

1. **`oauth.register("github", ...)`** — tells Authlib which provider URLs to use and which scopes to request (`read:user`). Client ID/Secret identify *this app* to GitHub.
2. **`GET /`** (`index`) — renders `templates/index.html`. The template branches on `session['user']`: shows Login button when absent, Welcome + Logout when present.
3. **`GET /login`** — `oauth.github.authorize_redirect(redirect_uri)` builds the GitHub authorize URL (with `client_id`, `redirect_uri`, `scope`, and a CSRF `state` token stored in the session) and 302-redirects the browser to GitHub.
4. **User authorizes on GitHub** — GitHub redirects back to `/auth/callback?code=...&state=...`.
5. **`GET /auth/callback`** —
   - `oauth.github.authorize_access_token()` validates `state`, then makes a server-to-server `POST` to GitHub's token endpoint with the `code` + `client_secret`, getting back an `access_token`.
   - `oauth.github.get("user")` calls `https://api.github.com/user` with the bearer token to fetch the authenticated user's profile.
   - We persist `{name, login}` in the Flask signed-cookie session.
   - Redirect back to `/`, which now renders the Welcome state.
6. **`GET /logout`** — clears `session['user']` and redirects to `/`.

## Project layout

```
flask-oauth/
├── app.py
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── README.md
└── templates/
    └── index.html
```
