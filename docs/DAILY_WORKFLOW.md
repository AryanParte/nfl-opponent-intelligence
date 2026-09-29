# Daily sync and continuation

GitHub is the persistent source of truth:
https://github.com/AryanParte/nfl-opponent-intelligence.

Canonical local clone: `/Users/aryanparte/Documents/nfl-opponent-intelligence`.
The daily task runs at 08:00 America/New_York, following Eastern daylight/standard
time. The task's starting directory may differ; explicitly use the stable clone
for every Git and development command. A new chat or workspace is not a new project.

## Start of a run

1. Verify the clone exists, its Git root equals the intended path, and its origin
   identifies `AryanParte/nfl-opponent-intelligence`. The host has an unrelated
   ancestor repository, so do not rely on Git's upward directory discovery.
2. Inspect `git status`, recent commits, local branches, and upstream tracking.
   Preserve all user changes and unpublished commits.
3. Fetch origin. Inspect open PRs, reviews, remote branches, and CI. If the working
   branch is behind its own upstream and the working tree is clean, fast-forward
   it. If it is ahead, retain that history. Resolve divergence carefully in the
   feature branch, without resets, forced updates, or guessing about user changes.
4. Continue the appropriate unmerged `codex/` branch. If the prior work was merged,
   begin the next branch from updated origin/main. Do not repeatedly branch from
   the old initial snapshot or redo already merged work.
5. Read AGENTS.md, README.md, ROADMAP.md, docs/STATUS.md, and LEARNING_LOG.md from
   this checkout. Choose one coherent unfinished unit, prioritizing regressions
   and relevant review feedback.

Use the installed `/Library/Developer/CommandLineTools/usr/bin/git` when the
system `/usr/bin/git` Xcode shim fails. Do not change global developer settings.
The origin is configured as HTTPS, although this host's existing Git URL rules
may route Git transport through SSH. Verify the owner/repository, not just the
transport spelling. Repository-local HTTPS credential helpers are configured to
use the existing store; no credentials are committed to this project.

## Finish a run

Implement, test, and review the full diff. Fix findings and rerun relevant checks.
Update roadmap/status and append the required learning report with exactly three
review questions. Before committing, inspect `git var GIT_AUTHOR_IDENT` and
`git var GIT_COMMITTER_IDENT`. For Aryan's authorized daily work use:

```sh
git config --local user.name 'Aryan Parte'
git config --local user.email '134340600+AryanParte@users.noreply.github.com'
```

This name matches the connected GitHub profile. The email uses the verified
account ID and GitHub's documented ID-based no-reply format. GitHub already linked
the foundation commit's author and committer to AryanParte; inspect attribution
after publication if anything changes. Do not change global settings or backdate
commits to manufacture activity.

Stage only reviewed files, commit a clear meaningful unit on the feature branch,
and push it. Verify the remote branch SHA equals the local SHA. Open or update the
appropriate PR against main, attach it to the task, and inspect CI. Never merge
or enable auto-merge. Main was seeded once with the existing foundation snapshot
during migration; that is not permission for future direct changes to main.

If a push fails, retain local commits, record the exact reason, and retry before
starting unrelated work. Do not report a local-only commit as published. Keep
private files, credentials, and large raw data out of Git.

## Recovery in a new session

If the canonical clone is absent, check that the remote exists and clone its full
history to the stable path. Inspect remote branches/PRs to select the continuation
branch; do not assume main contains unmerged work. If a different directory already
occupies the path, inspect it before taking action. Never initialize a new repo as
a substitute, recreate the GitHub repository, or delete/overwrite an existing clone.

Filesystem permissions can be session-specific. If access is denied, request only
the stable clone, its protected `.git` metadata, and necessary GitHub network
access. Preserve work and report a real access blocker instead of developing in
the dated task directory. Local scheduled work requires this computer and app to
be running; see [scheduled tasks documentation](https://learn.chatgpt.com/docs/automations?surface=app).

The original task checkout is retained solely as a recovery backup under that
task's `work/migration-backup/nfl-opponent-intelligence`. It is not a continuation
checkout. Recover from GitHub first, because the backup will become stale.
