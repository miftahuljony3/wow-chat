"""
Facebook token resolution helpers.

A common setup mistake is pasting a *User* access token (or a token for the
wrong page) when connecting a Messenger/Instagram integration. Posting to a
page requires that page's own *Page* access token. This module resolves the
correct Page token from whatever token the user provided, so the integration
just works — and returns a human-readable note (incl. a warning + the list of
pages the token actually manages when it can't find a match).
"""

import logging

from core.net_retry import request_with_retries

logger = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v19.0"


def _get(path: str, token: str, *, attempts: int = 4, **params):
    params["access_token"] = token
    resp = request_with_retries("GET", f"{GRAPH}/{path}", params=params, attempts=attempts)
    try:
        data = resp.json()
    except Exception:
        data = {}
    return resp.status_code, data


def resolve_page_access_token(token: str, page_id: str) -> tuple[str, dict]:
    """
    Return (page_access_token, info) for `page_id`.

    Strategy:
      1. GET /{page_id}?fields=access_token — if the token manages the page,
         Facebook hands back a Page-scoped token. Use it.
      2. Fallback: GET /me/accounts and match the entry whose id == page_id.
      3. Otherwise return the original token unchanged + a warning note, so the
         eventual post fails with a clear, actionable message.

    Never raises — resolution is best-effort.
    """
    info = {
        "resolved": False,
        "source": "unchanged",
        "page_name": "",
        "note": "",
        "managed_pages": [],
    }
    if not token or not page_id:
        return token, info

    # 1. Direct page endpoint — cleanest path.
    try:
        status, data = _get(page_id, token, fields="access_token,name")
        if status == 200 and data.get("access_token"):
            info.update(
                resolved=True,
                source="page_endpoint",
                page_name=data.get("name", ""),
                note=f"✓ Using the Page access token for “{data.get('name', page_id)}”.",
            )
            return data["access_token"], info
    except Exception as exc:
        logger.warning("Page-endpoint token resolution failed: %s", exc)

    # 2. /me/accounts fallback.
    try:
        status, data = _get("me/accounts", token, fields="name,id,access_token,tasks", limit=200)

        # Expired / invalid token (code 190) — report it precisely.
        err = data.get("error") if isinstance(data, dict) else None
        if err and err.get("code") == 190:
            info["note"] = (
                f"⚠ This access token is expired or invalid ({err.get('message', '')}). "
                f"Generate a fresh long-lived Page access token (with pages_manage_posts "
                f"+ pages_read_engagement) and paste it here."
            )
            return token, info

        pages = data.get("data", []) if status == 200 else []
        info["managed_pages"] = [{"id": p.get("id"), "name": p.get("name")} for p in pages]

        match = next((p for p in pages if str(p.get("id")) == str(page_id)), None)
        if match and match.get("access_token"):
            info.update(
                resolved=True,
                source="me_accounts",
                page_name=match.get("name", ""),
                note=f"✓ Using the Page access token for “{match.get('name', page_id)}”.",
            )
            return match["access_token"], info

        # No match — craft an actionable warning.
        if pages:
            listed = ", ".join(f"{p.get('name')} ({p.get('id')})" for p in pages)
            info["note"] = (
                f"⚠ This token doesn’t manage page {page_id}. It manages: {listed}. "
                f"Use one of those Page IDs, or a token for page {page_id}."
            )
        else:
            _, me = _get("me", token, fields="id,name")
            me_err = me.get("error") if isinstance(me, dict) else None
            if me_err and me_err.get("code") == 190:
                info["note"] = (
                    f"⚠ This access token is expired or invalid ({me_err.get('message', '')}). "
                    f"Paste a fresh long-lived Page access token."
                )
            else:
                info["note"] = (
                    f"⚠ Couldn’t find a Page token for {page_id}. This looks like a "
                    f"{me.get('name', 'User')} ({me.get('id', '?')}) token with no managed "
                    f"pages — generate a Page token with pages_manage_posts + "
                    f"pages_read_engagement."
                )
    except Exception as exc:
        logger.warning("/me/accounts token resolution failed: %s", exc)
        info["note"] = f"⚠ Couldn’t verify this token with Facebook right now ({exc})."

    return token, info
