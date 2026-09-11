import json
import os
from pathlib import Path

import requests

API_URL = "https://rubinum.io/api/forum/posts/latest?limit=20"
STATE_FILE = Path("state.json")

# Only posts from this section are sent to Discord.
TARGET_SECTION = "Events"

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


def load_state():
    if not STATE_FILE.exists():
        return None
    try:
        return int(json.loads(STATE_FILE.read_text())["last_id"])
    except Exception:
        return None


def save_state(last_id):
    STATE_FILE.write_text(json.dumps({"last_id": last_id}, indent=2) + "\n")


def get_posts():
    r = requests.get(API_URL, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"Rubinum API returned an unsuccessful response: {data}")
    return data["posts"]


def send_discord(post):
    post_id = post["id"]
    title = post["title"]
    author = post.get("author_username", "Unknown")
    section = post.get("section_name", "Unknown")
    created = post.get("created_at", "")
    url = f"https://rubinum.io/forum/post/{post_id}"

    payload = {
        "username": "Rubinum News",
        "embeds": [{
            "title": title[:256],
            "url": url,
            "description": f"**Section:** {section}\n**Author:** {author}",
            "timestamp": created,
            "footer": {"text": f"Rubinum post #{post_id}"}
        }]
    }

    r = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    r.raise_for_status()


def main():
    posts = get_posts()
    if not posts:
        print("No posts returned.")
        return

    posts = sorted(posts, key=lambda p: int(p["id"]))
    last_id = load_state()

    # First run: establish a baseline and do NOT spam the Discord channel
    # with the existing backlog.
    if last_id is None or last_id <= 0:
        save_state(int(posts[-1]["id"]))
        print(f"Initial baseline set to post #{posts[-1]['id']}.")
        return

    new_posts = [
        p for p in posts
        if int(p["id"]) > last_id
        and p.get("section_name") == TARGET_SECTION
    ]

    for post in new_posts:
        send_discord(post)
        print(f"Sent #{post['id']}: {post['title']}")

    # Always advance the state to the newest API post, including ignored ones.
    # This prevents an ignored post from being considered new forever.
    newest_id = int(posts[-1]["id"])
    if newest_id > last_id:
        save_state(newest_id)
    else:
        print("No new posts.")


if __name__ == "__main__":
    main()
