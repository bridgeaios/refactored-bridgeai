"""
YouTube Skill Discovery — search YouTube for skills, extract metadata as markdown,
learn skill definitions from video descriptions.

Flow:
  query / skill_id → YouTube Search API → video metadata → markdown parse
  → skill definition → stored in memory → available to engine + SVG renderer

Requires: YOUTUBE_API_KEY in env (Google Cloud Console → YouTube Data API v3)
          No key → service returns {"ok": False, "reason": "no_api_key"}

API budget: search costs ~100 quota units/request; videos.list costs 1.
Daily free quota: 10,000 units → ~100 searches/day.
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import httpx

log = logging.getLogger(__name__)

YT_BASE = "https://www.googleapis.com/youtube/v3"
_TIMEOUT = float(os.environ.get("BRIDGE_YT_TIMEOUT", "12"))
_MAX_RESULTS_DEFAULT = int(os.environ.get("BRIDGE_YT_MAX_RESULTS", "8"))

# Skill tag inference: map YouTube category keywords → Bridge skill tags
_TAG_MAP: dict[str, list[str]] = {
    "python":       ["python", "engineering"],
    "javascript":   ["javascript", "engineering"],
    "fastapi":      ["fastapi", "backend", "engineering"],
    "blockchain":   ["blockchain", "defi", "crypto"],
    "defi":         ["defi", "blockchain", "economy"],
    "trading":      ["trade", "economy", "bossbots"],
    "ai":           ["ai", "cognitive", "decision"],
    "machine learning": ["ai", "ml", "learning"],
    "ubi":          ["ubi", "economy", "bridge"],
    "speech":       ["speech", "tts", "bridge"],
    "visualization":["visualization", "svg", "render"],
    "economics":    ["economy", "bridge"],
    "governance":   ["governance", "ethics", "bridge"],
    "swarm":        ["swarm", "infrastructure", "bridge"],
    "health":       ["health", "infrastructure"],
    "api":          ["api", "backend", "engineering"],
    "tutorial":     ["tutorial", "learning"],
    "automation":   ["automation", "infrastructure"],
    "docker":       ["docker", "infrastructure", "devops"],
    "kubernetes":   ["kubernetes", "infrastructure", "devops"],
}


class YouTubeSkillsService:
    """
    Search YouTube, extract skill definitions from video metadata.
    All calls are async HTTP via httpx.
    """

    def __init__(self) -> None:
        self._key = os.environ.get("YOUTUBE_API_KEY", "").strip()

    @property
    def available(self) -> bool:
        return bool(self._key)

    # ─── SEARCH ─────────────────────────────────────────────────────────────────

    async def search(self, query: str, max_results: int = _MAX_RESULTS_DEFAULT) -> dict[str, Any]:
        """
        Search YouTube for videos matching query.
        Returns list of skill-shaped results with YouTube metadata + inferred tags.
        """
        if not self.available:
            return {"ok": False, "reason": "no_api_key", "hint": "Set YOUTUBE_API_KEY in .env", "results": []}

        params = {
            "part":       "snippet",
            "q":          query,
            "type":       "video",
            "maxResults": min(max_results, 25),
            "key":        self._key,
            "relevanceLanguage": "en",
            "safeSearch": "moderate",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(f"{YT_BASE}/search", params=params)
                r.raise_for_status()
                data = r.json()
        except httpx.TimeoutException:
            return {"ok": False, "reason": "timeout", "results": []}
        except httpx.HTTPStatusError as e:
            return {"ok": False, "reason": f"http_{e.response.status_code}", "results": []}
        except Exception as e:
            log.warning("YouTube search error: %s", e)
            return {"ok": False, "reason": str(e), "results": []}

        items = data.get("items", [])
        results = [_item_to_skill_shape(item) for item in items]
        return {
            "ok":      True,
            "query":   query,
            "count":   len(results),
            "results": results,
        }

    # ─── LEARN FROM VIDEO ───────────────────────────────────────────────────────

    async def learn_from_video(self, video_id: str) -> dict[str, Any]:
        """
        Fetch full video metadata for video_id and extract a skill definition.
        Parses description as markdown: numbered lists → steps, paragraphs → description.
        Returns { ok, skill_definition, video_meta, markdown_source }
        """
        if not self.available:
            return {"ok": False, "reason": "no_api_key", "hint": "Set YOUTUBE_API_KEY in .env"}

        params = {
            "part": "snippet,contentDetails,statistics",
            "id":   video_id,
            "key":  self._key,
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(f"{YT_BASE}/videos", params=params)
                r.raise_for_status()
                data = r.json()
        except httpx.TimeoutException:
            return {"ok": False, "reason": "timeout"}
        except httpx.HTTPStatusError as e:
            return {"ok": False, "reason": f"http_{e.response.status_code}"}
        except Exception as e:
            log.warning("YouTube video fetch error: %s", e)
            return {"ok": False, "reason": str(e)}

        items = data.get("items", [])
        if not items:
            return {"ok": False, "reason": "video_not_found"}

        item    = items[0]
        snippet = item.get("snippet", {})
        stats   = item.get("statistics", {})

        title       = snippet.get("title", "")
        description = snippet.get("description", "")
        channel     = snippet.get("channelTitle", "")
        yt_tags     = snippet.get("tags", []) or []
        published   = snippet.get("publishedAt", "")
        video_url   = f"https://www.youtube.com/watch?v={video_id}"

        # Parse markdown from description
        md_skill = _description_to_skill(title, description, yt_tags, channel, video_id, video_url)

        # Build metadata record
        video_meta = {
            "video_id":    video_id,
            "url":         video_url,
            "title":       title,
            "channel":     channel,
            "published_at": published,
            "views":       int(stats.get("viewCount", 0) or 0),
            "likes":       int(stats.get("likeCount", 0) or 0),
            "description_length": len(description),
        }

        return {
            "ok":              True,
            "skill_definition": md_skill,
            "video_meta":      video_meta,
            "markdown_source": _description_to_markdown(title, description, channel, video_url),
        }

    # ─── RECOMMEND FOR SKILL ────────────────────────────────────────────────────

    async def recommend_for_skill(self, skill_id: str, skill_name: str = "", tags: list[str] | None = None) -> dict[str, Any]:
        """
        Auto-recommend YouTube videos for a given skill.
        Builds a search query from skill_id + name + tags.
        """
        parts = [skill_name or skill_id.replace(".", " ")]
        for t in (tags or [])[:3]:
            if t not in ("bridge",):
                parts.append(t)
        query = " ".join(parts) + " tutorial"
        result = await self.search(query, max_results=6)
        result["skill_id"] = skill_id
        return result


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _item_to_skill_shape(item: dict) -> dict[str, Any]:
    """Convert a YouTube search result item to a skill-shaped dict."""
    snippet  = item.get("snippet", {})
    vid_id   = (item.get("id") or {}).get("videoId", "")
    title    = snippet.get("title", "")
    desc     = snippet.get("description", "")
    channel  = snippet.get("channelTitle", "")
    thumb    = (snippet.get("thumbnails") or {}).get("medium", {}).get("url", "")
    pub      = snippet.get("publishedAt", "")

    inferred_tags = _infer_tags(title + " " + desc)

    return {
        "video_id":   vid_id,
        "url":        f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "",
        "title":      title,
        "channel":    channel,
        "description": desc[:300] + ("…" if len(desc) > 300 else ""),
        "thumbnail":  thumb,
        "published":  pub,
        "tags":       inferred_tags,
        # Skill-compatible shape for direct use in /skills
        "skill_id":   _title_to_id(title),
        "skill_name": title,
        "source":     "youtube",
    }


def _description_to_skill(
    title: str,
    description: str,
    yt_tags: list[str],
    channel: str,
    video_id: str,
    video_url: str,
) -> dict[str, Any]:
    """
    Extract a skill definition from video metadata.
    Parses description markdown: numbered lists → steps, first paragraph → description.
    """
    lines    = description.strip().splitlines()
    steps    = _extract_steps(lines)
    desc_txt = _extract_description(lines)
    tags     = _infer_tags(title + " " + description + " " + " ".join(yt_tags))

    return {
        "id":          f"youtube.{video_id}",
        "name":        title[:80],
        "description": desc_txt[:400],
        "tags":        tags,
        "version":     "1.0.0",
        "source":      "youtube",
        "source_url":  video_url,
        "channel":     channel,
        "steps":       steps,
        "learned_at":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        # No run() / visualize() — those are generated by the engine from this definition
    }


def _description_to_markdown(title: str, description: str, channel: str, url: str) -> str:
    """Return the video description as clean markdown for storage + learning."""
    return f"# {title}\n\n**Channel:** {channel}  \n**URL:** {url}\n\n{description}"


def _extract_steps(lines: list[str]) -> list[dict[str, str]]:
    """Extract numbered list items from description lines as skill steps."""
    steps = []
    for line in lines:
        line = line.strip()
        # Match: "1. Title" or "1) Title" or "Step 1: Title"
        m = re.match(r'^(?:step\s*)?(\d+)[.):\s]+(.+)$', line, re.IGNORECASE)
        if m:
            _num, text = m.group(1), m.group(2).strip()
            # Split on " - " or " – " for title/detail
            if " - " in text:
                title, _, detail = text.partition(" - ")
            elif " – " in text:
                title, _, detail = text.partition(" – ")
            else:
                title, detail = text, ""
            steps.append({"title": title[:80], "detail": detail[:200]})
        if len(steps) >= 10:
            break
    return steps


def _extract_description(lines: list[str]) -> str:
    """Extract the first meaningful paragraph from description lines."""
    paragraphs = []
    current = []
    for line in lines:
        line = line.strip()
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            # Skip lines that look like timestamps (00:00), URLs, or social links
            if re.match(r'^\d+:\d+', line) or line.startswith("http") or line.startswith("@"):
                continue
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs[0][:400] if paragraphs else ""


def _infer_tags(text: str) -> list[str]:
    """Infer Bridge skill tags from text using keyword map."""
    text_lower = text.lower()
    found: set[str] = set()
    for keyword, tags in _TAG_MAP.items():
        if keyword in text_lower:
            found.update(tags)
    # Always include youtube as source tag
    found.add("youtube")
    return sorted(found)[:8]


def _title_to_id(title: str) -> str:
    """Convert video title to a safe skill id: youtube.some-skill-name"""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return f"youtube.{slug}"
