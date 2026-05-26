"""Flask + GitHub OAuth POC.

Implements the OAuth 2.0 Authorization Code flow:

    /          -> renders index.html (Login button or Welcome + Logout)
    /login     -> 302 to GitHub authorize URL
    /auth/callback -> exchanges code for token, fetches user, sets session
    /logout    -> clears session
"""

import os

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, session, url_for

load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


app = Flask(__name__)
app.secret_key = _require_env("FLASK_SECRET_KEY")

oauth = OAuth(app)
oauth.register(
    name="github",
    client_id=_require_env("GITHUB_CLIENT_ID"),
    client_secret=_require_env("GITHUB_CLIENT_SECRET"),
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user"},
)
print("[startup] GitHub OAuth client registered")


@app.route("/")
def index():
    user = session.get("user")
    repos = []
    if user and session.get("token"):
        try:
            # Live call to GitHub on each render — requires the access token.
            resp = oauth.github.get(
                "user/repos",
                params={"sort": "updated", "per_page": 5},
                token=session["token"],
            )
            resp.raise_for_status()
            repos = [
                {
                    "name": r["full_name"],
                    "url": r["html_url"],
                    "description": r.get("description"),
                    "updated_at": r["updated_at"],
                }
                for r in resp.json()
            ]
        except Exception as exc:  # noqa: BLE001
            # Token may have been revoked or expired — force re-login.
            app.logger.warning("Failed to fetch repos: %s", exc)
            session.pop("user", None)
            session.pop("token", None)
            return redirect(url_for("index"))
    return render_template("index.html", user=user, repos=repos)


@app.route("/login")
def login():
    redirect_uri = url_for("callback", _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def callback():
    try:
        token = oauth.github.authorize_access_token()  # validates state
        resp = oauth.github.get("user", token=token)
        resp.raise_for_status()
        data = resp.json()
        session["user"] = {
            "id": data["id"],  # stable identifier
            "login": data["login"],
            "name": data.get("name") or data["login"],
            "avatar_url": data.get("avatar_url"),
        }
        # Persist the token so login-required routes can call GitHub later.
        # For a POC the signed-cookie session is fine; in production store
        # tokens server-side keyed by user id.
        session["token"] = token
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("OAuth callback failed: %s", exc)
        session.pop("user", None)
        session.pop("token", None)
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("token", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
