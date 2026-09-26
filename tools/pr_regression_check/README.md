# PR regression check

Replays the "Online Editor test results" links recorded in merged
[Domain-Connect/Templates](https://github.com/Domain-Connect/Templates) pull
requests through this repo's `apply_template()`, and flags any pull request
whose recorded result no longer matches what the library produces today.

## Usage

```bash
# Check everything cached so far (first run fetches from GitHub)
.venv/bin/python tools/pr_regression_check/check_pr_regressions.py

# Fetch up to N additional not-yet-cached merged PRs, then check everything cached
.venv/bin/python tools/pr_regression_check/check_pr_regressions.py --limit 500

# Check one specific PR (fetches it if not already cached)
.venv/bin/python tools/pr_regression_check/check_pr_regressions.py --pr 1842

# Ignore the cache and re-fetch everything from GitHub
.venv/bin/python tools/pr_regression_check/check_pr_regressions.py --refresh

# Include PRs/results that matched in the JSON report too (default: errors only)
.venv/bin/python tools/pr_regression_check/check_pr_regressions.py --full-report
```

Requires the `gh` CLI, authenticated with access to
`Domain-Connect/Templates` (public repo, so any authenticated token works).

PRs are fetched newest-first and cached in `.cache/prs.jsonl` (gitignored),
one JSON object per line, so repeated runs only fetch PRs not already seen.
A JSON report is written to `.cache/report.json`. By default it only
includes PRs that mismatched or errored; pass `--full-report` to include
every checked PR, matches included. Each result includes the full
`apply_template()` inputs (`template`, `zone_records`, `params`,
`group_ids`, `ignore_signature`, `multi_aware`) so a failure can be
reproduced directly without going back to the PR body.

## How it works

Each editor-test link encodes a gzip+base64 token (same format the
Templates repo's own `check_pr_description.py` decodes) containing:

- `template` — the exact template dict that was tested
- `zone_records`, `domain`, `host`, `group_ids`, `params` — the
  `apply_template()` inputs used
- `ignore_signature`, `multi_aware` — `apply_template()` flags
- `dc_apply_result` — the `(new_records, deleted_records, final_records)`
  tuple `apply_template()` returned at test time

The tool decodes the token (without attempting signature verification —
the HMAC key is a private secret of the Templates repo's CI, and we trust
the GitHub PR body as the source of truth here), re-runs `apply_template()`
with the token's own embedded template and inputs, and diffs the result
against the stored `dc_apply_result`. Using the token's embedded template
(rather than the template file as it stands in the Templates repo today)
isolates "did this library's behavior change" from "did the template change
after the test was recorded".

The comparison ignores each record's entire `_dc` key: `_dc.id` is a fresh
random UUID on every `multi_aware` run and will never match a stored result,
and the rest of `_dc`'s shape may legitimately evolve independently of
`apply_template()` correctness.

### REDIR301/REDIR302 caveat

Templates using `REDIR301`/`REDIR302` require the caller to supply
`redirect_records` — placeholder records standing in for the DNS
provider's own redirect infrastructure. The editor token doesn't carry
these (they aren't template test state), so the tool supplies a fixed
`127.0.0.1` / `::1` pair, confirmed against a real PR's recorded result to
match what the online editor itself uses as its default fixture.

## PRs without test links

A merged PR with no decodable "Online Editor test results" link is skipped
(not flagged as a failure) but is still cached, so it isn't re-fetched from
GitHub on the next run.
