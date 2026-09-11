# Rubinum → Discord (free GitHub Actions bot)

This checks the public Rubinum forum API every 5 minutes and posts new forum posts to a Discord webhook.

## Setup

1. Create a GitHub repository. A private repository is fine.
2. Upload `scraper.py`, `state.json`, and `.github/workflows/rubinum.yml`.
3. In the repository go to:
   Settings → Secrets and variables → Actions → New repository secret
4. Name the secret:
   `DISCORD_WEBHOOK_URL`
5. Paste your NEW Discord webhook URL as the value.
6. Go to Actions → "Rubinum News → Discord" → Run workflow once.
7. The first run creates a baseline and does not post the existing backlog.
8. After that, the scheduled workflow checks every 5 minutes.

The workflow has `contents: write` because it saves the last Rubinum post ID into `state.json`.

Only posts in the "Events" section are sent to Discord. Edit `TARGET_SECTION` in `scraper.py` if you want a different section.

Important: never put the Discord webhook URL directly into the Python file or commit it to GitHub. Keep it in GitHub Secrets.
