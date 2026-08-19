"""
Facebook Page API service — posting, comment deletion, comment replies.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


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
        with httpx.Client(timeout=10.0) as client:
            resp = client.delete(
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

    def get_comment(self, comment_id: str) -> dict:
        """Fetch comment details (message, from, etc.)."""
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
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
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(f"{GRAPH_BASE}{path}", data=data)
            if not resp.is_success:
                logger.error(
                    "Graph API POST %s failed: %s %s", path, resp.status_code, resp.text
                )
                resp.raise_for_status()
            return resp.json()
