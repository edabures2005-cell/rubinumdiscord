import json
import os
import re
from pathlib import Path

import requests

API_URL = "https://rubinum.io/api/forum/section/3/posts?page=1&limit=20"
STATE_FILE = Path("itemshop_state.json")
WEBHOOK_URL = os.environ["DISCORD_ITEMSHOP_WEBHOOK_URL"]


def load_state():
    if not STATE_FILE.exists():
        return 0
    try:
        return int(json.loads(STATE_FILE.read_text())["last_id"])
    except Exception:
        return 0


def save_state(last_id):
    STATE_FILE.write_text(json.dumps({"last_id": last_id}, indent=2) + "\n")


def get_posts():
    r = requests.get(API_URL, timeout=20)
    r.raise_for_status()

    data = r.json()

    if not data.get("success"):
        raise RuntimeError(f"Rubinum API error: {data}")

    return data["posts"]


def bbcode_to_discord(text):
    text = re.sub(
        r"\[url=(.*?)\](.*?)\[/url\]",
        r"[\2](\1)",
        text,
        flags=re.I | re.S
    )

    text = re.sub(
        r"\[img\].*?\[/img\]",
        "",
        text,
        flags=re.I | re.S
    )

    text = re.sub(r"\[center\](.*?)\[/center\]", r"\1", text, flags=re.I | re.S)
    text = re.sub(r"\[b\](.*?)\[/b\]", r"**\1**", text, flags=re.I | re.S)
    text = re.sub(r"\[i\](.*?)\[/i\]", r"*\1*", text, flags=re.I | re.S)
    text = re.sub(r"\[u\](.*?)\[/u\]", r"__\1__", text, flags=re.I | re.S)
    text = re.sub(r"\[s\](.*?)\[/s\]", r"~~\1~~", text, flags=re.I | re.S)

    text = re.sub(
        r"\[color=[^\]]+\](.*?)\[/color\]",
        r"\1",
        text,
        flags=re.I | re.S
    )

    text = re.sub(
        r"\[size=[^\]]+\](.*?)\[/size\]",
        r"\1",
        text,
        flags=re.I | re.S
    )

    text = re.sub(r"\[list\]", "", text, flags=re.I)
    text = re.sub(r"\[/list\]", "", text, flags=re.I)
    text = re.sub(r"\[\*\]\s*", "\n• ", text, flags=re.I)

    text = re.sub(r"\[[^\]]+\]", "", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_text(text, max_len=4000):
    chunks = []

    while len(text) > max_len:
        cut = text.rfind("\n", 0, max_len)

        if cut < max_len // 2:
            cut = text.rfind(" ", 0, max_len)

        if cut < max_len // 2:
            cut = max_len

        chunks.append(text[:cut].strip())
        text = text[cut:].strip()

    if text:
        chunks.append(text)

    return chunks


def send_post(post):
    post_id = post["id"]
    title = post["title"]
    content = bbcode_to_discord(post.get("content", ""))
    author = post.get("username") or post.get("author_username", "Unknown")
    created = post.get("created_at", "")

    url = f"https://rubinum.io/forum/post/{post_id}"

    chunks = split_text(content)

    if not chunks:
        chunks = ["No post text was returned by Rubinum."]

    for i, chunk in enumerate(chunks):

        payload = {
            "username": "Rubinum Item Shop",
            "embeds": [{
                "title": title[:256] if i == 0 else f"{title[:245]} (continued)",
                "url": url,
                "description": chunk,
                "footer": {
                    "text": f"Rubinum Item Shop #{post_id} • Posted by {author}"
                }
            }]
        }

        if i == 0 and created:
            payload["embeds"][0]["timestamp"] = created

        r = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=20
        )

        r.raise_for_status()


def main():
    posts = get_posts()

    if not posts:
        print("No posts returned.")
        return

    posts = sorted(posts, key=lambda p: int(p["id"]))
    last_id = load_state()

    # First run: establish baseline without sending old posts
    if last_id <= 0:
        save_state(int(posts[-1]["id"]))
        print(f"Initial Item Shop baseline set to post #{posts[-1]['id']}.")
        return

    new_posts = [
        p for p in posts
        if int(p["id"]) > last_id
    ]

    for post in new_posts:
        send_post(post)
        print(f"Sent Item Shop post #{post['id']}: {post['title']}")

    newest_id = int(posts[-1]["id"])

    if newest_id > last_id:
        save_state(newest_id)
    else:
        print("No new Item Shop posts.")


if __name__ == "__main__":
    main()
