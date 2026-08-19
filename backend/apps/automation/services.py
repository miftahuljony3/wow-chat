"""
Facebook Page API service — posting, comment deletion, comment replies.
"""

import logging
import httpx

from core.net_retry import request_with_retries

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


class GraphAPIError(Exception):
    """Raised on a Facebook Graph API error response, carrying Meta's own
    error message + code so it shows up legibly in DailyPostLog / the UI."""

    def __init__(self, message: str, code=None, subcode=None, status: int = 0):
        self.code = code
        self.subcode = subcode
        self.status = status
        super().__init__(message)

    @classmethod
    def from_response(cls, resp) -> "GraphAPIError":
        try:
            err = resp.json().get("error", {})
            msg = err.get("message") or resp.text
            hint = ""
            # Missing publish permission — Meta returns a misleading legacy string
            if err.get("code") == 200:
                hint = (
                    " — the Page access token is missing the 'pages_manage_posts' "
                    "permission, or it is a User token rather than a Page token."
                )
            return cls(
                f"Facebook: {msg}{hint}",
                code=err.get("code"),
                subcode=err.get("error_subcode"),
                status=resp.status_code,
            )
        except Exception:
            return cls(f"Facebook HTTP {resp.status_code}: {resp.text[:300]}",
                       status=resp.status_code)


class FacebookPageService:
    """
    Wraps the Meta Graph API for page-level actions:
      - Publish photo / feed posts
      - Delete comments (spam moderation)
      - Reply to comments (auto-reply)
    """

    def __init__(self, page_access_token: str, page_id: str):
        self.token = page_access_token
        self.page_id = page_id

    # ── Publishing ────────────────────────────────────────────────────────────

    def post_photo(self, image_url: str, caption: str) -> dict:
        """
        Publish an image to the page timeline.
        image_url must be a publicly accessible URL.
        Returns {"id": "<post-id>"} on success.
        """
        resp = self._post(
            f"/{self.page_id}/photos",
            data={"url": image_url, "caption": caption, "access_token": self.token},
        )
        logger.info("Posted photo to page %s: %s", self.page_id, resp.get("id"))
        return resp

    def post_feed(self, message: str, link: str = "") -> dict:
        """
        Publish a text (or link) post to the page feed.
        Returns {"id": "<post-id>"}.
        """
        data: dict = {"message": message, "access_token": self.token}
        if link:
            data["link"] = link
        resp = self._post(f"/{self.page_id}/feed", data=data)
        logger.info("Posted to feed on page %s: %s", self.page_id, resp.get("id"))
        return resp

    def post_video(self, video_url: str, description: str, title: str = "") -> dict:
        """
        Upload a video by URL to the page.
        Returns {"id": "<video-id>"}.
        """
        data = {
            "file_url": video_url,
            "description": description,
            "access_token": self.token,
        }
        if title:
            data["title"] = title
        resp = self._post(f"/{self.page_id}/videos", data=data)
        logger.info("Posted video to page %s: %s", self.page_id, resp.get("id"))
        return resp

    # ── Comment Moderation ────────────────────────────────────────────────────

    def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a comment from a page post.
        Returns True on success.
        """
        resp = request_with_retries(
            "DELETE",
            f"{GRAPH_BASE}/{comment_id}",
            params={"access_token": self.token},
        )
        if resp.status_code == 200:
            logger.info("Deleted comment %s", comment_id)
            return True
        logger.warning(
            "Failed to delete comment %s: %s %s",
            comment_id, resp.status_code, resp.text,
        )
        return False

    def reply_to_comment(self, comment_id: str, message: str) -> dict:
        """
        Post a reply to a comment.
        Returns {"id": "<reply-comment-id>"}.
        """
        resp = self._post(
            f"/{comment_id}/comments",
            data={"message": message, "access_token": self.token},
        )
        logger.info("Replied to comment %s", comment_id)
        return resp

    def like_comment(self, comment_id: str) -> bool:
        """Like a comment (engagement boost on valid comments). Best-effort."""
        try:
            resp = request_with_retries(
                "POST", f"{GRAPH_BASE}/{comment_id}/likes",
                data={"access_token": self.token},
            )
            return resp.is_success
        except Exception as exc:
            logger.warning("Failed to like comment %s: %s", comment_id, exc)
            return False

    def get_comment(self, comment_id: str) -> dict:
        """Fetch comment details (message, from, etc.)."""
        resp = request_with_retries(
            "GET",
            f"{GRAPH_BASE}/{comment_id}",
            params={
                "fields": "message,from,created_time,can_remove",
                "access_token": self.token,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _post(self, path: str, data: dict) -> dict:
        # Retries connection-level failures (this VPS has flaky routing to
        # Facebook); does not retry HTTP errors like bad token / permission.
        resp = request_with_retries("POST", f"{GRAPH_BASE}{path}", data=data)
        if not resp.is_success:
            logger.error(
                "Graph API POST %s failed: %s %s", path, resp.status_code, resp.text
            )
            raise GraphAPIError.from_response(resp)
        return resp.json()
