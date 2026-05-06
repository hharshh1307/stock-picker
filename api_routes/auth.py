"""Auth API routes — login, register, user management."""

import uuid
from datetime import datetime
from typing import Any

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()

def _get_store():
    from api_server import get_store
    return get_store()

ADMIN_EMAIL = "harshh1307@gmail.com"


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None
    invite_token: str | None = None  # Optional invite-only gating


# Hardcoded invite token — change this or move to DB
INVITE_TOKEN = "niftysage-invite-2025"


def _get_user_by_email(store, email: str) -> dict | None:
    row = store.conn.execute(
        "SELECT * FROM users WHERE email = ? AND is_active = 1", (email.lower(),)
    ).fetchone()
    return dict(row) if row else None


@router.post("/login")
async def login(body: LoginRequest) -> dict[str, Any]:
    """Verify credentials against DB. Called by NextAuth credentials provider."""
    store = _get_store()
    email = body.email.lower().strip()

    user = _get_user_by_email(store, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check password with bcrypt
    try:
        if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last login timestamp
    store.conn.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.now().isoformat(), user["id"]),
    )
    store.conn.commit()

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }


@router.post("/register")
async def register(body: RegisterRequest) -> dict[str, Any]:
    """Register a new user. Requires invite token or admin."""
    store = _get_store()
    email = body.email.lower().strip()

    # Invite token gate (skip for admin email)
    if email != ADMIN_EMAIL.lower() and body.invite_token != INVITE_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="Registration requires a valid invite token. Contact harshh1307@gmail.com for access."
        )

    # Check if already exists
    existing = _get_user_by_email(store, email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    # Hash password
    password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    # Determine role
    role = "admin" if email == ADMIN_EMAIL.lower() else "user"
    name = body.name or email.split("@")[0]
    user_id = str(uuid.uuid4())

    store.conn.execute(
        "INSERT INTO users (id, email, password_hash, name, role, created_at) VALUES (?,?,?,?,?,?)",
        (user_id, email, password_hash, name, role, datetime.now().isoformat()),
    )
    store.conn.commit()

    return {"id": user_id, "email": email, "name": name, "role": role}


class OAuthRequest(BaseModel):
    email: str
    name: str | None = None
    provider_id: str | None = None

@router.post("/oauth")
async def oauth_login(body: OAuthRequest) -> dict[str, Any]:
    """Sync an OAuth user to the database, creating them if they don't exist."""
    store = _get_store()
    email = body.email.lower().strip()

    user = _get_user_by_email(store, email)
    
    if not user:
        # Create user
        user_id = str(uuid.uuid4())
        role = "admin" if email == ADMIN_EMAIL.lower() else "user"
        name = body.name or email.split("@")[0]
        
        # We store empty password hash for OAuth-only users
        store.conn.execute(
            "INSERT INTO users (id, email, password_hash, name, role, created_at, last_login) VALUES (?,?,?,?,?,?,?)",
            (user_id, email, "", name, role, datetime.now().isoformat(), datetime.now().isoformat()),
        )
        store.conn.commit()
        return {"id": user_id, "email": email, "name": name, "role": role}
    else:
        # Update last login
        store.conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(), user["id"]),
        )
        store.conn.commit()
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        }


@router.get("/users")
async def list_users(x_admin_token: str | None = None) -> list[dict]:
    """List all users (admin only)."""
    from fastapi import Header
    from api_routes.admin import _require_admin
    _require_admin(x_admin_token)

    store = _get_store()
    rows = store.conn.execute(
        "SELECT id, email, name, role, created_at, last_login, is_active FROM users ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(user_id: str, x_admin_token: str | None = None) -> dict:
    """Deactivate a user account (admin only)."""
    from api_routes.admin import _require_admin
    _require_admin(x_admin_token)

    store = _get_store()
    store.conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    store.conn.commit()
    return {"status": "deactivated", "user_id": user_id}


# ── Chat history persistence ──────────────────────────────────────────────────

class ChatHistoryItem(BaseModel):
    user_id: str
    session_id: str
    role: str  # 'user' | 'assistant'
    content: str
    tool_calls: str | None = None  # JSON string


@router.post("/chat-history")
async def save_chat_message(body: ChatHistoryItem) -> dict:
    """Save a chat message to history."""
    store = _get_store()
    store.conn.execute(
        """INSERT INTO user_chat_history (user_id, session_id, role, content, tool_calls, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (body.user_id, body.session_id, body.role, body.content,
         body.tool_calls, datetime.now().isoformat()),
    )
    store.conn.commit()
    return {"status": "saved"}


@router.get("/chat-history/{user_id}/{session_id}")
async def get_chat_history(user_id: str, session_id: str, limit: int = 20) -> list[dict]:
    """Get recent chat history for a user session."""
    store = _get_store()
    rows = store.conn.execute(
        """SELECT role, content, tool_calls, created_at FROM user_chat_history
           WHERE user_id = ? AND session_id = ?
           ORDER BY created_at ASC
           LIMIT ?""",
        (user_id, session_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


@router.delete("/chat-history/{user_id}/{session_id}")
async def clear_chat_history(user_id: str, session_id: str) -> dict:
    """Clear chat history for a session."""
    store = _get_store()
    store.conn.execute(
        "DELETE FROM user_chat_history WHERE user_id = ? AND session_id = ?",
        (user_id, session_id),
    )
    store.conn.commit()
    return {"status": "cleared"}


# ── Watchlist ─────────────────────────────────────────────────────────────────

@router.get("/watchlist/{user_id}")
async def get_watchlist(user_id: str) -> list[dict]:
    store = _get_store()
    rows = store.conn.execute(
        """SELECT w.symbol, s.company_name, s.sector, w.added_at
           FROM user_watchlists w
           LEFT JOIN stocks s ON s.symbol = w.symbol
           WHERE w.user_id = ?
           ORDER BY w.added_at DESC""",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/watchlist/{user_id}/{symbol}")
async def add_to_watchlist(user_id: str, symbol: str) -> dict:
    store = _get_store()
    try:
        store.conn.execute(
            "INSERT OR IGNORE INTO user_watchlists (user_id, symbol, added_at) VALUES (?,?,?)",
            (user_id, symbol.upper(), datetime.now().isoformat()),
        )
        store.conn.commit()
        return {"status": "added", "symbol": symbol.upper()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/watchlist/{user_id}/{symbol}")
async def remove_from_watchlist(user_id: str, symbol: str) -> dict:
    store = _get_store()
    store.conn.execute(
        "DELETE FROM user_watchlists WHERE user_id = ? AND symbol = ?",
        (user_id, symbol.upper()),
    )
    store.conn.commit()
    return {"status": "removed", "symbol": symbol.upper()}
