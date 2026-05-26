# Flask + GitHub OAuth POC

A minimal Flask application that demonstrates the **OAuth 2.0 Authorization Code flow** end-to-end against GitHub. The home page shows a single "Login with GitHub" button; after authorization, the same page shows the user's avatar, name, GitHub `@login`, numeric `id`, a Logout button, and a live list of the user's **5 most recently updated repositories** fetched from the GitHub API on every render using the stored access token.

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

> **New to OAuth?** Read [`docs/OAUTH_EXPLAINED.md`](docs/OAUTH_EXPLAINED.md) first. It's a standalone learning companion that explains *why* the protocol is shaped the way it is — the problem OAuth solves, the difference between front and back channels, what `state` and `redirect_uri` actually defend against, and where this POC cuts corners compared to production. The walk-through below assumes you already know the concepts and just want to see how they map onto `app.py`.

The app implements the standard Authorization Code flow. Reading `app.py` top-to-bottom:

1. **`oauth.register("github", ...)`** — tells Authlib which provider URLs to use and which scopes to request (`read:user`). Client ID/Secret identify *this app* to GitHub.
2. **`GET /`** (`index`) — renders `templates/index.html`. The template branches on `session['user']`:
   - **Logged out**: shows the Login button.
   - **Logged in**: the view first calls `GET https://api.github.com/user/repos?sort=updated&per_page=5` using the access token stored in `session['token']`, then renders the profile block (avatar, name, `@login`, `id`), the Logout button, and the live repo list. The repo call happens on **every** render — nothing is cached — so it's a real demonstration of a token-gated feature. If the call fails (e.g. the token was revoked on GitHub), the session is cleared and the user is bounced back to the login state.
3. **`GET /login`** — `oauth.github.authorize_redirect(redirect_uri)` builds the GitHub authorize URL (with `client_id`, `redirect_uri`, `scope`, and a CSRF `state` token stored in the session) and 302-redirects the browser to GitHub.
4. **User authorizes on GitHub** — GitHub redirects back to `/auth/callback?code=...&state=...`.
5. **`GET /auth/callback`** —
   - `oauth.github.authorize_access_token()` validates `state`, then makes a server-to-server `POST` to GitHub's token endpoint with the `code` + `client_secret`, returning the token dict (`access_token`, `token_type`, `scope`).
   - `oauth.github.get("user", token=token)` calls `https://api.github.com/user` with the bearer token to fetch the authenticated user's profile.
   - We persist `{id, login, name, avatar_url}` in `session['user']` and the full token dict in `session['token']`. `id` is GitHub's immutable numeric user identifier and is what should be used as a primary key for any login-required logic; `login` and `name` can change and are display-only.
   - Redirect back to `/`, which now renders the logged-in state.
6. **`GET /logout`** — clears both `session['user']` and `session['token']`, then redirects to `/`.

### Identifying the logged-in user

The "is this user logged in?" check in any login-required route is simply `session.get("user")` — the signed Flask cookie is the source of truth. To call GitHub on the user's behalf inside such a route, pass `token=session["token"]` to `oauth.github.get(...)`. For this POC the token lives in the signed-cookie session; for anything beyond a demo, store tokens server-side keyed by `user["id"]`.

## Project layout

```
flask-oauth/
├── app.py
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── README.md
├── docs/
│   └── OAUTH_EXPLAINED.md
└── templates/
    └── index.html
```
