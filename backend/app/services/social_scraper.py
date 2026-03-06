

# import httpx
import logging
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
# from backend.app.core.config import settings
import instaloader
from instaloader.exceptions import TooManyRequestsException
from instaloader.instaloadercontext import RateController

logger = logging.getLogger(__name__)


def _normalize_instagram_username(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""

    # If a URL is provided, only accept instagram hosts.
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if host not in {"instagram.com", "m.instagram.com"}:
            return ""
        value = (parsed.path or "").strip("/")
        value = value.split("/")[0]
    else:
        # Support bare instagram.com/username inputs without scheme.
        lower = value.lower()
        if lower.startswith("www."):
            value = value[4:]
            lower = value.lower()
        if lower.startswith("instagram.com/"):
            value = value.split("/", 1)[1]
        elif "/" in value and not value.startswith("@"):
            # Looks like a non-instagram path URL/input.
            return ""

    value = value.strip("/")
    if value.startswith("@"):
        value = value[1:]

    # Drop query/fragment remnants
    value = value.split("?")[0].split("#")[0]

    # Keep only instagram username-safe chars
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in "._")
    return cleaned[:30]


class FastFailRateController(RateController):
    """Rate controller that fails fast on 429 instead of sleeping for minutes."""

    def handle_429(self, query_type: str) -> None:
        self._context.error(
            "Instagram 429 received. Fast-failing this scrape request to avoid long blocking retries.",
            repeat_at_end=False,
        )
        raise TooManyRequestsException("Instagram rate limit hit (429). Fast-failed request.")

class SocialScraperService:
    """
    Service to interact with social media scraping.
    Currently uses Instaloader (local) for free testing.
    Apify logic is commented out for future use.
    """
    
    # APIFY_API_URL = "https://api.apify.com/v2"
    
    def __init__(self):
        # self.token = settings.APIFY_API_TOKEN
        # if not self.token:
        #     logger.warning("APIFY_API_TOKEN not found in settings. Scraping will fail.")
        self.L = instaloader.Instaloader(
            sleep=False,
            max_connection_attempts=1,
            request_timeout=20.0,
            rate_controller=lambda context: FastFailRateController(context),
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=True,
            save_metadata=False,
            compress_json=False
        )
            
    # async def _run_actor(self, actor_id: str, run_input: Dict[str, Any], timeout_secs: int = 120) -> List[Dict[str, Any]]:
    #     """
    #     Runs an Apify actor and retrieves the dataset items.
    #     """
        # ... (Apify logic commented out) ...

    async def scrape_instagram_profile(self, username: str, max_posts: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape recent posts from an Instagram profile using Instaloader.
        """
        normalized_username = _normalize_instagram_username(username)
        if not normalized_username:
            logger.warning(f"Invalid Instagram username input: {username}")
            return []

        logger.info(f"Scraping profile {normalized_username} using Instaloader...")
        
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._scrape_instagram_profile_sync, normalized_username, max_posts),
                timeout=25.0,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Instaloader profile scrape timed out for {normalized_username}")
            return []
        except TooManyRequestsException as e:
            logger.warning(f"Instaloader rate-limited for profile {normalized_username}: {e}")
            return []
        except Exception as e:
            logger.error(f"Instaloader profile scrape error: {e}")
            return []

    def _scrape_instagram_profile_sync(self, normalized_username: str, max_posts: int) -> List[Dict[str, Any]]:
        profile = instaloader.Profile.from_username(self.L.context, normalized_username)

        posts = []
        count = 0
        for post in profile.get_posts():
            if count >= max_posts:
                break

            posts.append({
                "id": post.shortcode,  # utilizing shortcode as clearer ID
                "shortCode": post.shortcode,
                "caption": post.caption,
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "commentsCount": post.comments,
                "likesCount": post.likes,
                "timestamp": post.date_utc.isoformat(),
                "ownerUsername": post.owner_username,
                "type": "instagram",
                # Store post object for comment fetching if needed (but can't serialise)
                # We fetch comments immediately below or refactor to fetch later
                "_post_obj": post,
            })
            count += 1

        return posts

    async def scrape_instagram_comments(self, post_obj: Any, max_comments: int = 15) -> List[Dict[str, Any]]:
        """
        Scrape comments for a specific post using Instaloader.
        Takes post object directly to avoid re-fetching.
        """
        logger.info(f"Scraping comments for post {post_obj.shortcode}...")
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._scrape_instagram_comments_sync, post_obj, max_comments),
                timeout=20.0,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Instaloader comment scrape timed out for post {post_obj.shortcode}")
            return []
        except TooManyRequestsException as e:
            logger.warning(f"Instaloader rate-limited while fetching comments: {e}")
            return []
        except Exception as e:
            logger.error(f"Instaloader comment scrape error: {e}")
            return []

    def _scrape_instagram_comments_sync(self, post_obj: Any, max_comments: int) -> List[Dict[str, Any]]:
        comments = []
        count = 0
        for comment in post_obj.get_comments():
            if count >= max_comments:
                break

            comments.append({
                "text": comment.text,
                "ownerUsername": comment.owner.username,
                "timestamp": comment.created_at_utc.isoformat(),
                "likesCount": comment.likes_count,
            })
            count += 1

        return comments

    async def scrape_hashtag(self, hashtag: str, max_posts: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape top posts for a specific hashtag to find category trends.
        """
        logger.info(f"Scraping hashtag #{hashtag} using Instaloader...")
        
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._scrape_hashtag_sync, hashtag, max_posts),
                timeout=25.0,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Instaloader hashtag scrape timed out for #{hashtag}")
            return []
        except TooManyRequestsException as e:
            logger.warning(f"Instaloader rate-limited for hashtag #{hashtag}: {e}")
            return []
        except Exception as e:
            logger.error(f"Instaloader hashtag scrape error: {e}")
            return []

    def _scrape_hashtag_sync(self, hashtag: str, max_posts: int) -> List[Dict[str, Any]]:
        # Get hashtag object
        hashtag_obj = instaloader.Hashtag.from_name(self.L.context, hashtag)

        posts = []
        count = 0
        # Get top posts for the hashtag (most relevant)
        for post in hashtag_obj.get_top_posts():
            if count >= max_posts:
                break

            posts.append({
                "id": post.shortcode,
                "shortCode": post.shortcode,
                "caption": post.caption,
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "commentsCount": post.comments,
                "likesCount": post.likes,
                "timestamp": post.date_utc.isoformat(),
                "ownerUsername": post.owner_username,
                "type": "instagram",
                "_post_obj": post,
            })
            count += 1

        return posts

    async def get_competitor_intel(self, username: str) -> Dict[str, Any]:
        """
        Orchestrate full intel gathering: Profile -> Posts -> Comments
        """
        # Note: scrape_instagram_profile returns posts with _post_obj
        posts = await self.scrape_instagram_profile(username, max_posts=3)
        intel = {"profile": username, "posts": []}
        
        for post in posts:
            post_obj = post.pop("_post_obj", None)
            
            # Fetch comments using the object
            comments = []
            if post_obj and post.get("commentsCount", 0) > 0:
                comments = await self.scrape_instagram_comments(post_obj, max_comments=10)
            
            post["comments_data"] = comments
            intel["posts"].append(post)
            
        return intel
