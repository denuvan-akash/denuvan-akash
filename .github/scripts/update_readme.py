#!/usr/bin/env python3
"""Render README.md from README.template.md.

Runs automatically in GitHub Actions (see .github/workflows/update-readme.yml).
Fills in:
  {{USERNAME}}      GitHub username (auto-detected from the repository owner)
  {{TIKTOK_URL}}    https://www.tiktok.com/@<handle>
  {{WHATSAPP_URL}}  https://wa.me/<number>
  {{RECENT_REPOS}}  the most recently pushed public repositories
  {{DAILY_QUOTE}}   one line that changes every day
  {{UPDATED}}       timestamp of this run

Only the standard library is used. It never crashes the workflow when the
GitHub API is unreachable; it falls back to a friendly placeholder instead.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

QUOTES = [
    "කේතයෙන් හීන ගොඩනගමු. 🚀",
    "Small commits, big dreams. ✨",
    "අද ලියන පේළියක්, හෙට ලොකු වෙනසක්.",
    "Ship it. Learn. Repeat. 🔁",
    "හොඳ code එකක් කියන්නේ හොඳින් කියවෙන කතාවක්.",
    "Every bug is an idea that isn't finished yet. 🐞",
    "ගොඩනගන එක නවත්තන්න එපා, ඉගෙන ගන්න එකත් නවත්තන්න එපා.",
    "Design with soul, code with heart. 💜",
    "පොඩි පියවරවල් ගොඩක් එකතු වුණාම ලොකු ගමනක් වෙනවා.",
    "Make it work, make it right, make it beautiful. 🎨",
    "අලුත් අදහසක් කියන්නේ අලුත් app එකක පළවෙනි commit එක.",
    "Stay curious. Stay building. 🌌",
    "රාත්‍රියේ ලියන code එක උදේට magic වෙනවා.",
    "Dream in Sinhala, ship in every language. 🌍",
]


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def fetch_repos(username, token, limit):
    """Return (repos, ok). repos is a list of dicts from the GitHub API."""
    mock = os.environ.get("MOCK_REPOS_JSON")
    if mock:
        data = load_json(mock, [])
        return data, True
    url = (
        f"https://api.github.com/users/{username}/repos"
        "?sort=pushed&direction=desc&per_page=30&type=owner"
    )
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme-updater"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp), True
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"warning: could not fetch repositories: {exc}", file=sys.stderr)
        return [], False


def render_repos(repos, ok, username, limit):
    own = [
        r for r in repos
        if not r.get("fork") and not r.get("archived")
        and r.get("name", "").lower() != username.lower()
    ][:limit]
    if not own:
        if not ok:
            return "_Repository list will appear after the next automatic update._"
        return "_No public repositories yet. Your first project will show up here automatically._ ✨"
    lines = []
    for r in own:
        desc = (r.get("description") or "").strip()
        bits = []
        if r.get("language"):
            bits.append(f"`{r['language']}`")
        stars = r.get("stargazers_count", 0)
        if stars:
            bits.append(f"⭐ {stars}")
        meta = " · ".join(bits)
        line = f"- 📦 [**{r['name']}**]({r['html_url']})"
        if desc:
            line += f" — {desc}"
        if meta:
            line += f"  \n  <sub>{meta}</sub>"
        lines.append(line)
    return "\n".join(lines)


def main():
    cfg = load_json(os.path.join(ROOT, "profile.config.json"), {}) or {}
    username = (
        cfg.get("github_username")
        or os.environ.get("GITHUB_REPOSITORY_OWNER")
        or os.environ.get("PROFILE_USERNAME")
        or "YOUR_USERNAME"
    )
    token = os.environ.get("GITHUB_TOKEN", "")
    count = int(cfg.get("recent_repos_count", 5))
    tz = dt.timezone(dt.timedelta(hours=float(cfg.get("timezone_offset_hours", 0))))
    now = dt.datetime.now(tz)

    tiktok = str(cfg.get("tiktok_handle", "")).lstrip("@")
    wa = "".join(ch for ch in str(cfg.get("whatsapp_international", "")) if ch.isdigit())

    repos, ok = fetch_repos(username, token, count)
    values = {
        "{{USERNAME}}": username,
        "{{DISPLAY_NAME}}": cfg.get("display_name", "Denuwan Akash"),
        "{{JOB_TITLE}}": cfg.get("job_title", "Software Engineer"),
        "{{LOCATION}}": cfg.get("location", "Colombo, Sri Lanka"),
        "{{TIKTOK_URL}}": f"https://www.tiktok.com/@{tiktok}" if tiktok else "https://www.tiktok.com",
        "{{WHATSAPP_URL}}": f"https://wa.me/{wa}" if wa else "https://wa.me",
        "{{RECENT_REPOS}}": render_repos(repos, ok, username, count),
        "{{DAILY_QUOTE}}": QUOTES[now.timetuple().tm_yday % len(QUOTES)],
        "{{UPDATED}}": now.strftime("%Y-%m-%d %H:%M") + f" (UTC{now.strftime('%z')[:3]}:{now.strftime('%z')[3:]})",
    }

    with open(os.path.join(ROOT, "README.template.md"), encoding="utf-8") as fh:
        text = fh.read()
    for key, val in values.items():
        text = text.replace(key, val)

    out = os.path.join(ROOT, os.environ.get("README_OUT", "README.md"))
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"README written for @{username} ({len(text)} chars)")


if __name__ == "__main__":
    main()
