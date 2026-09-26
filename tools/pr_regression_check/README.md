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

# Use a different overrides file (default: overrides.json next to this script)
.venv/bin/python tools/pr_regression_check/check_pr_regressions.py --overrides /path/to/overrides.json
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
  tuple `apply_template()` returned at test time (the tool converts this to
  a named `{new_records, deleted_records, final_records}` dict internally
  and whenever it writes one out, so nothing depends on tuple position)

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

## Overrides

Some flagged discrepancies are known and not worth re-litigating on every
run — e.g. a bug in the online editor's own test tool rather than a real
library regression, or an expected result you know is stale for reasons
unrelated to `apply_template()`. These go in `overrides.json`, sitting next
to the script and committed to git (pass `--overrides` to use a different
path).

The file is keyed `<pr_number> -> <providerId> -> <serviceId> -> <host> -> [entries]`.
PR number stays the top-level key because different PRs can carry different
versions of "the same" template (by providerId/serviceId) with legitimately
different expected outcomes; providerId/serviceId/host is how a human
identifies a link within a PR. A host can hold several entries when
multiple links in the same PR share a host but differ in params (e.g. a
different `domain`), so each entry also carries the `params` it applies to
— a link only matches an entry when PR number, providerId, serviceId, host,
*and* params all match.

```json
{
  "840": {
    "spinlab.studio": {
      "casino": {
        "sub": [
          {
            "params": {"domain": "example.com", "host": "sub"},
            "action": "ignore",
            "reason": "Why this is being ignored, ideally with a link to context."
          }
        ]
      }
    }
  },
  "1234": {
    "some.provider": {
      "some-service": {
        "@": [
          {
            "params": {"domain": "example.com", "host": ""},
            "action": "override_expected",
            "reason": "The recorded result predates fix #NN; this is the corrected expectation.",
            "dc_apply_result": {
              "new_records": [],
              "deleted_records": [],
              "final_records": []
            }
          }
        ]
      }
    }
  }
}
```

- `"ignore"` skips the link entirely (status `ignored` in the report); the
  payload is not even replayed.
- `"override_expected"` replaces the token's stored `dc_apply_result` with
  the one given here before comparing against the library's actual output
  — use this when you know what the correct expected result should be,
  rather than just wanting to silence the check.

Unknown `action` values, or an `override_expected` entry missing
`dc_apply_result`, fail loudly at startup rather than being silently
ignored.

### Adding overrides from the CLI

Rather than hand-editing `overrides.json`, you can add entries directly for
a specific PR's currently-failing link(s):

```bash
# Add an "ignore" entry (with reason) for every mismatching/erroring link in PR #840
.venv/bin/python tools/pr_regression_check/check_pr_regressions.py --pr 840 \
    --add-to-override-ignore "Editor tool bug, not a library regression: see PR discussion"

# Add an "override_expected" entry, accepting the library's current output
# as the new expected result, for every currently-mismatching link in PR #1234
.venv/bin/python tools/pr_regression_check/check_pr_regressions.py --pr 1234 \
    --add-to-override-result "Recorded result predates fix #NN; this is the corrected expectation"
```

Both flags require `--pr` and only ever touch links belonging to that PR.
Only links currently reporting `mismatch` (or, for `--add-to-override-ignore`,
also `error`) get an entry; links that already match are left untouched.
`--add-to-override-result` skips `error` links (there is no actual result to
store) with a warning. Existing entries elsewhere in the file are preserved;
re-running for the same providerId/serviceId/host/params overwrites just
that entry.
