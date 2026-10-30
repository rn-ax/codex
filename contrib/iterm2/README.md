# iTerm2 Codex relationships

This optional iTerm2 status-bar component shows distinct GitHub issues and pull requests linked to the thread selected in Codex. Clicking it opens a popover with links.

The Codex TUI publishes its current thread as the iTerm2 session variable `user.codex_thread_id`. The component reads that variable and runs `agrel get --entity codex-session <thread-id>` to load the links.

## Install

1. Build and run this Codex fork in iTerm2.
2. Enable iTerm2's Python API and install its Python runtime if prompted.
3. Copy `codex_agrel_status.py` into `~/Library/Application Support/iTerm2/Scripts/AutoLaunch/`, creating the `AutoLaunch` directory if needed.
4. If `agrel` is not on iTerm2's `PATH`, set `AGREL_PATH` to its executable path in the environment that launches iTerm2.
5. In iTerm2, open **Settings > Profiles > Session > Configure Status Bar** and add **Codex relationships**.

The component updates every five seconds and refreshes immediately when the Codex thread ID changes. It only displays canonical `https://github.com/` PR and issue URLs.
