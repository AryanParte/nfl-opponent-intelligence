# Development and review

Start with the README and current roadmap. Python 3.11+ is required. Use
`PYTHONPATH=src python3 -m unittest discover -s tests -v` for the offline suite.
The README includes the command-line demo. Tests use only temporary directories
and synthetic fixtures; they must never depend on current upstream data.

Keep a change tied to one observable behavior. Define the football cohort and
denominator before adding a metric. Add regression tests that fail for the actual
bug or assumption, not tests that only restate the implementation.

Before a commit, inspect the complete diff and run the relevant verification.
Update the roadmap, status, and learning log. Preserve raw input provenance, do
not commit downloaded season files or secrets, and label all synthetic examples.

The canonical repository is https://github.com/AryanParte/nfl-opponent-intelligence.
Fetch origin and reconcile the existing branch before selecting work. Work on a
`codex/` branch, push verified commits, and create/update its PR against main.
No direct main/master commits, automatic merges, or force pushes. The one-time
migration seeded main with the preserved foundation snapshot; later work requires
review. See [daily workflow](docs/DAILY_WORKFLOW.md) for identity and recovery rules.
