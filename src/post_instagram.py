#!/usr/bin/env python3
"""Publish one approved four-image carousel through the official Instagram API.

The command is a dry run unless --publish is supplied. Tokens are read only from
environment variables or a local .env file and are never printed.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


CSV_PATH = Path("data/posts.csv")
GENERATED_DIR = Path("generated")
PUBLISHED_PATH = Path("data/published.json")
IMAGE_NAMES = ("01.jpg", "02.jpg", "03.jpg", "04.jpg")


@dataclass(frozen=True)
class Post:
    post_id: str
    publish_date: str
    caption: str
    image_paths: tuple[Path, ...]


def load_env(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE entries without overriding existing environment variables."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def read_posts(csv_path: Path = CSV_PATH) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = [dict(row) for row in reader]
    malformed = [row.get("id", "?") for row in rows if row.get(None)]
    if malformed:
        raise ValueError(
            "CSV has extra columns in posts: "
            + ", ".join(malformed)
            + ". Put fields containing commas inside double quotes."
        )
    return rows


def select_post(
    rows: list[dict[str, str]],
    target_date: str,
    post_id: str | None,
    generated_dir: Path = GENERATED_DIR,
) -> Post:
    candidates = [row for row in rows if row.get("status", "").strip().lower() == "approved"]
    if post_id:
        candidates = [row for row in candidates if row.get("id") == post_id]
    else:
        candidates = [row for row in candidates if row.get("publish_date") == target_date]

    if len(candidates) != 1:
        target = f"post ID {post_id}" if post_id else f"date {target_date}"
        raise ValueError(f"Expected exactly one approved post for {target}; found {len(candidates)}")

    row = candidates[0]
    paths = tuple(generated_dir / row["id"] / name for name in IMAGE_NAMES)
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing generated images: " + ", ".join(missing))

    caption = row.get("caption", "").strip()
    if not caption:
        raise ValueError(f"Post {row['id']} has no caption")
    return Post(row["id"], row["publish_date"], caption, paths)


def public_image_urls(post: Post, base_url: str) -> tuple[str, ...]:
    base_url = base_url.rstrip("/")
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("PUBLIC_MEDIA_BASE_URL must be a public HTTPS URL")
    return tuple(f"{base_url}/generated/{post.post_id}/{path.name}" for path in post.image_paths)


def read_published(path: Path = PUBLISHED_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_published(post: Post, media_id: str, path: Path = PUBLISHED_PATH) -> None:
    data = read_published(path)
    data[post.post_id] = {
        "media_id": media_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "scheduled_date": post.publish_date,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class InstagramClient:
    def __init__(self, access_token: str, user_id: str, api_version: str, graph_base_url: str):
        self.access_token = access_token
        self.user_id = user_id
        self.api_version = api_version.strip("/")
        self.graph_base_url = graph_base_url.rstrip("/")

    def _url(self, object_id: str, edge: str = "") -> str:
        suffix = f"/{edge}" if edge else ""
        return f"{self.graph_base_url}/{self.api_version}/{object_id}{suffix}"

    def _request(self, method: str, url: str, parameters: dict[str, str]) -> dict[str, Any]:
        body = urllib.parse.urlencode(parameters).encode("utf-8") if method == "POST" else None
        if method == "GET" and parameters:
            url = f"{url}?{urllib.parse.urlencode(parameters)}"
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "English1000Knock/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Instagram API returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Instagram API connection failed: {error.reason}") from error
        if "error" in payload:
            raise RuntimeError(f"Instagram API error: {payload['error']}")
        return payload

    def create_image_container(self, image_url: str) -> str:
        payload = self._request(
            "POST",
            self._url(self.user_id, "media"),
            {"image_url": image_url, "is_carousel_item": "true"},
        )
        return str(payload["id"])

    def create_carousel_container(self, children: list[str], caption: str) -> str:
        payload = self._request(
            "POST",
            self._url(self.user_id, "media"),
            {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption},
        )
        return str(payload["id"])

    def wait_until_ready(self, container_id: str, timeout_seconds: int = 180) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            payload = self._request(
                "GET", self._url(container_id), {"fields": "status_code,status"}
            )
            status = str(payload.get("status_code", "")).upper()
            if status == "FINISHED":
                return
            if status in {"ERROR", "EXPIRED"}:
                raise RuntimeError(f"Instagram container failed: {payload.get('status', status)}")
            time.sleep(5)
        raise TimeoutError(f"Instagram container {container_id} was not ready after {timeout_seconds}s")

    def publish(self, creation_id: str) -> str:
        payload = self._request(
            "POST",
            self._url(self.user_id, "media_publish"),
            {"creation_id": creation_id},
        )
        return str(payload["id"])


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable is missing: {name}")
    return value


def run_dry_run(post: Post, urls: tuple[str, ...]) -> None:
    print("DRY RUN — Instagramへは送信していません")
    print(f"post_id: {post.post_id}")
    print(f"publish_date: {post.publish_date}")
    print(f"caption: {post.caption}")
    for index, (path, url) in enumerate(zip(post.image_paths, urls, strict=True), start=1):
        print(f"image_{index}: {path} -> {url}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--post-id", help="Dateを無視して指定IDを選択")
    parser.add_argument("--publish", action="store_true", help="実際にInstagramへ投稿する")
    parser.add_argument("--allow-republish", action="store_true", help="投稿済みIDの再投稿を許可")
    parser.add_argument(
        "--skip-if-missing",
        action="store_true",
        help="当日分がない場合はエラーにせず終了する（定時実行用）",
    )
    args = parser.parse_args()

    load_env()
    try:
        post = select_post(read_posts(), args.date, args.post_id)
    except ValueError as error:
        if args.skip_if_missing and not args.post_id and "found 0" in str(error):
            print(f"SKIP — {args.date} に承認済み投稿はありません")
            return
        raise
    published = read_published()
    if post.post_id in published and not args.allow_republish:
        raise RuntimeError(
            f"Post {post.post_id} is already recorded as published. "
            "Use --allow-republish only when intentional."
        )

    base_url = required_env("PUBLIC_MEDIA_BASE_URL")
    urls = public_image_urls(post, base_url)
    if not args.publish:
        run_dry_run(post, urls)
        return

    client = InstagramClient(
        required_env("INSTAGRAM_ACCESS_TOKEN"),
        required_env("INSTAGRAM_USER_ID"),
        os.getenv("INSTAGRAM_API_VERSION", "v23.0"),
        os.getenv("INSTAGRAM_GRAPH_BASE_URL", "https://graph.instagram.com"),
    )
    print(f"Creating four image containers for post {post.post_id}...")
    children = [client.create_image_container(url) for url in urls]
    print("Creating carousel container...")
    carousel_id = client.create_carousel_container(children, post.caption)
    client.wait_until_ready(carousel_id)
    print("Publishing carousel...")
    media_id = client.publish(carousel_id)
    write_published(post, media_id)
    print(f"Published post {post.post_id}. Instagram media ID: {media_id}")


if __name__ == "__main__":
    main()
