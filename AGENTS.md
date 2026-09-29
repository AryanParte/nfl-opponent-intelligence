# Daily engineering instructions

Read README.md, ROADMAP.md, docs/STATUS.md, and the latest LEARNING_LOG.md entry
before changing code. Then inspect the actual branch, recent commits, working
tree, tests, and configured remote work. Documentation is durable context, not
proof that unverified work has passed.

## Scope and priorities

- Build interview-defensible sports software and data engineering evidence.
- Fix verified regressions or relevant review feedback first; otherwise continue
  the next unchecked roadmap item. Finish one coherent unit per daily run.
- Current focus: the NFL Opponent Intelligence Platform and professional project
  presentation. Later NFL tracking and NBA projects are documented but deferred.
- Preserve completed work, existing user changes, and historical learning logs.
- Make routine decisions autonomously and record their rationale. Escalate only
  consequential ambiguity or indispensable missing authority/access.

## Verification and review

- Use primary sources for sports fields, statistical claims, and changing APIs.
- Test meaningful contracts and independently calculated expectations, including
  missing data, denominators, excluded plays, empty cohorts, and temporal cutoffs.
- Before committing, review the complete diff critically for bugs, weak tests,
  unnecessary complexity, data leakage, sports mistakes, and misleading docs.
- Fix findings and rerun relevant checks. Report what ran and what did not.
- No fabricated benchmark, deployment, usage, predictive, or affiliation claims.
- Synthetic examples must stay explicitly labeled. Retrospective source data is
  not automatically a historically available feature set.

## Git discipline

- Verify the Git root is THIS repository before staging. The host has an unrelated
  ancestor repository; never stage files from that root.
- Continue an appropriate `codex/` feature branch. Never commit or merge directly
  to main/master, enable auto-merge, force-push, or discard user changes.
- Stage explicit reviewed paths and commit meaningful verified work. Do not make
  filler commits, empty progress commits, or repeatedly rewrite history.
- Inspect existing branches/PRs before creating another. Once a remote exists,
  use a PR for review; never fabricate a remote URL or claim a local commit is
  published. The initial repository has no remote or main branch.
- On this host `/Library/Developer/CommandLineTools/usr/bin/git` works if the
  `/usr/bin/git` Xcode shim fails. Do not change global developer settings.

## Required end-of-run records

Update ROADMAP.md and docs/STATUS.md with completed acceptance criteria, evidence,
limitations, and the exact next unit. Append a dated entry to LEARNING_LOG.md:

- what was built and why it matters;
- important files/code to review;
- sports analytics concepts;
- software/statistical concepts;
- what Aryan should learn;
- exactly three questions he should be able to answer;
- tests run and findings from the complete-diff review;
- remaining issues and recommended next task.

If blocked, record the specific cause and a useful next step. Continue independent
in-scope work if possible. Do not repeat identical logs or commits on unchanged
blocked checks; amend the existing dated blocker entry only when there is new
information. Meaningful completion is the measure of a run, not line count.
