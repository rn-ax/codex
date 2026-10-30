#!/usr/bin/env python3
"""Show agrel links for the thread currently selected in Codex."""

import asyncio
import html
import json
import os
import shutil
import urllib.parse

import iterm2


AGREL = os.environ.get("AGREL_PATH") or shutil.which("agrel") or os.path.expanduser(
    "~/.local/bin/agrel"
)


async def relationships_for(thread_id):
    if not thread_id:
        return []

    try:
        process = await asyncio.create_subprocess_exec(
            AGREL,
            "get",
            "--entity",
            "codex-session",
            thread_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError:
        return None
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=3)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return None

    if process.returncode != 0:
        return None

    try:
        result = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(result, dict) or not isinstance(result.get("relationships"), list):
        return None

    links = {}
    for relationship in result.get("relationships", []):
        entity_a = relationship.get("entityA", {})
        entity_b = relationship.get("entityB", {})
        if entity_a == {"key": "codex-session", "value": thread_id}:
            related = entity_b
        elif entity_b == {"key": "codex-session", "value": thread_id}:
            related = entity_a
        else:
            continue

        key = related.get("key")
        value = related.get("value")
        parsed = urllib.parse.urlparse(value or "")
        if (
            key not in {"github-pr", "github-issue"}
            or parsed.scheme != "https"
            or parsed.hostname != "github.com"
        ):
            continue
        links.setdefault(value, (key, value, relationship.get("touchedAt", "")))

    return list(links.values())


def link_label(key, url):
    path = urllib.parse.urlparse(url).path.strip("/").split("/")
    if len(path) >= 4:
        kind = "PR" if key == "github-pr" else "Issue"
        return f"{kind} {path[0]}/{path[1]}#{path[3]}"
    return "PR" if key == "github-pr" else "Issue"


def render_links(links, thread_id):
    if not thread_id:
        return "<p>Codex has not published a selected thread ID.</p>"
    if links is None:
        return (
            "<p>Could not read agrel relationships. Check AGREL_PATH and the "
            "iTerm2 Script Console.</p>"
        )
    if not links:
        return "<p>No linked GitHub issues or pull requests.</p>"

    rows = []
    for key, url, touched_at in links:
        label = html.escape(link_label(key, url))
        href = html.escape(url, quote=True)
        timestamp = html.escape(str(touched_at or ""))
        rows.append(
            f'<li><a href="{href}" target="_blank" rel="noreferrer">{label}</a>'
            + (f'<small> · {timestamp}</small>' if timestamp else "")
            + "</li>"
        )
    return "<ul>" + "".join(rows) + "</ul>"


async def main(connection):
    app = await iterm2.async_get_app(connection)
    component = iterm2.StatusBarComponent(
        short_description="Codex relationships",
        detailed_description=(
            "Show linked GitHub issues and pull requests for the selected Codex thread."
        ),
        knobs=[],
        exemplar="PRs 1 · Issues 2",
        update_cadence=5,
        identifier="com.rnax.codex-agrel-status",
    )

    @iterm2.StatusBarRPC
    async def status(
        knobs,
        thread_id=iterm2.Reference("user.codex_thread_id"),
    ):
        links = await relationships_for(thread_id)
        if links is None:
            return "Codex links · unavailable"
        counts = {"github-pr": 0, "github-issue": 0}
        for key, _, _ in links:
            counts[key] += 1
        if not thread_id:
            return "Codex links · no thread"
        if not links:
            return "Codex links · none"
        return f"PRs {counts['github-pr']} · Issues {counts['github-issue']}"

    @iterm2.RPC
    async def show_links(session_id):
        session = app.get_session_by_id(session_id)
        if session is None:
            return
        thread_id = await session.async_get_variable("user.codex_thread_id")
        links = await relationships_for(thread_id)
        body = render_links(links, thread_id)
        await component.async_open_popover(
            session_id,
            "<!doctype html><meta charset='utf-8'>"
            "<style>body{font:14px -apple-system,sans-serif;padding:12px}"
            "ul{padding-left:20px}li{margin:8px 0}small{color:#777}</style>"
            "<h3>Codex relationships</h3>"
            + body,
            iterm2.Size(440, 360),
        )

    await component.async_register(connection, status, onclick=show_links)


iterm2.run_forever(main)
