#!/usr/bin/env python3
"""
Regression check: replay Domain-Connect/Templates PR editor-test tokens
through this library's apply_template() and flag discrepancies against the
result recorded at PR test time.

For each merged PR in Domain-Connect/Templates:
  1. Extract "Online Editor test results" editor links from the PR body,
     using the same token format as check_pr_description.py in that repo.
  2. Decode each token (signature verification is not attempted here - we
     trust the GitHub PR body as the source of truth, and the HMAC key is
     a private secret of the Templates repo's CI).
  3. Re-run apply_template() using the token's own embedded template dict
     (not the repo's current file) plus its zone_records/domain/host/params/
     group_ids/ignore_signature/multi_aware, so results reflect purely
     "did this library's behavior change" rather than template edits.
  4. Compare (new_records, deleted_records, final_records) against the
     token's stored dc_apply_result, ignoring the entire "_dc" key (its
     "id" sub-field is a fresh random UUID per multi_aware run and other
     _dc content may evolve independently of apply_template correctness).

PRs without any decodable editor-test token are skipped (not flagged) but
still cached, so a re-run doesn't re-fetch them from GitHub.

Usage:
    .venv/bin/python tools/pr_regression_check/check_pr_regressions.py [--limit N] [--refresh] [--pr NUMBER]
"""
import argparse
import base64
import gzip
import json
import os
import re
import subprocess
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from domainconnectzone.DomainConnectImpl import DomainConnect  # noqa: E402

REPO = "Domain-Connect/Templates"
CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache')
PR_CACHE_FILE = os.path.join(CACHE_DIR, 'prs.jsonl')
DEFAULT_OVERRIDES_FILE = os.path.join(os.path.dirname(__file__), 'overrides.json')

EDITOR_URL_PATTERN = re.compile(
    r"https://domainconnect\.paulonet\.eu/dc/free/templateedit\?token=([A-Za-z0-9+/=%]+)"
)

VOLATILE_KEYS = {"_dc"}

# REDIR301/REDIR302 records require the caller to supply "redirect_records" -
# placeholder DNS records representing the provider's own redirect infrastructure.
# The editor token does not carry these (they're not part of the template test
# state), but the online editor at domainconnect.paulonet.eu always uses this
# fixed loopback pair as its redirect-infrastructure fixture, confirmed by
# reproducing PR #1842's stored dc_apply_result byte-for-byte with it.
DEFAULT_REDIRECT_RECORDS = [
    {"type": "A", "pointsTo": "127.0.0.1", "ttl": 600},
    {"type": "AAAA", "pointsTo": "::1", "ttl": 600},
]


def load_cache():
    prs = {}
    if os.path.exists(PR_CACHE_FILE):
        with open(PR_CACHE_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                pr = json.loads(line)
                prs[pr['number']] = pr
    return prs


def append_cache(pr):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(PR_CACHE_FILE, 'a') as f:
        f.write(json.dumps(pr) + "\n")


def rewrite_cache(prs):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(PR_CACHE_FILE, 'w') as f:
        for pr in prs.values():
            f.write(json.dumps(pr) + "\n")


GRAPHQL_QUERY = """
query($cursor: String) {
  repository(owner: "Domain-Connect", name: "Templates") {
    pullRequests(states: MERGED, first: 50, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        body
        mergedAt
        files(first: 100) {
          pageInfo { hasNextPage }
          nodes { path }
        }
      }
    }
  }
}
"""


def fetch_merged_prs(known_numbers, limit=None, stop_at_pr=None):
    """Yield PR dicts from GitHub via gh api graphql, skipping ones already cached.

    PRs are fetched newest-first. If stop_at_pr is given, fetching stops right
    after that PR is yielded (or once the given PR number is passed, in case
    it does not exist), regardless of limit.
    """
    cursor = None
    fetched = 0
    while True:
        args = [
            "gh", "api", "graphql",
            "-f", f"query={GRAPHQL_QUERY}",
        ]
        if cursor:
            args += ["-f", f"cursor={cursor}"]
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        pr_conn = data["data"]["repository"]["pullRequests"]
        for node in pr_conn["nodes"]:
            if stop_at_pr is not None and node["number"] < stop_at_pr:
                return
            if node["number"] in known_numbers:
                continue
            if node["files"]["pageInfo"]["hasNextPage"]:
                print(f"  WARNING: PR #{node['number']} has >100 changed files; "
                      f"file list truncated", file=sys.stderr)
            pr = {
                "number": node["number"],
                "title": node["title"],
                "body": node["body"] or "",
                "merged_at": node["mergedAt"],
                "files": [n["path"] for n in node["files"]["nodes"]],
            }
            yield pr
            fetched += 1
            if stop_at_pr is not None and node["number"] == stop_at_pr:
                return
            if limit and fetched >= limit:
                return
        if not pr_conn["pageInfo"]["hasNextPage"]:
            return
        cursor = pr_conn["pageInfo"]["endCursor"]


def load_overrides(path):
    """
    Load the overrides file. Format:

    {
      "<pr_number>": {
        "<saved_at>": {
          "action": "ignore",
          "reason": "..."
        }
      },
      "<pr_number2>": {
        "<saved_at>": {
          "action": "override_expected",
          "reason": "...",
          "dc_apply_result": [[...new...], [...deleted...], [...final...]]
        }
      }
    }

    Each link within a PR is keyed by its "saved_at" timestamp, which is
    unique per editor-test link. Returns {} if the file does not exist.
    """
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        raw = json.load(f)

    overrides = {}
    for pr_number_str, links in raw.items():
        pr_number = int(pr_number_str)
        for saved_at, entry in links.items():
            action = entry.get("action")
            if action not in ("ignore", "override_expected"):
                raise ValueError(
                    f"overrides file: PR #{pr_number} saved_at={saved_at!r} "
                    f"has unknown action {action!r} (expected 'ignore' or 'override_expected')"
                )
            if action == "override_expected" and "dc_apply_result" not in entry:
                raise ValueError(
                    f"overrides file: PR #{pr_number} saved_at={saved_at!r} "
                    f"has action 'override_expected' but no 'dc_apply_result'"
                )
            overrides[(pr_number, saved_at)] = entry
    return overrides


def add_override_entries(path, pr_number, action, reason, results):
    """
    Append override entries for every result in `results` whose status is
    'mismatch' or 'error', to the overrides file at `path`. Existing entries
    for the same PR are preserved (and overwritten if the same saved_at is
    added again). Returns the list of saved_at keys written.
    """
    raw = {}
    if os.path.exists(path):
        with open(path) as f:
            raw = json.load(f)

    pr_key = str(pr_number)
    pr_overrides = raw.setdefault(pr_key, {})

    written = []
    for res in results:
        if res["status"] not in ("mismatch", "error"):
            continue
        saved_at = res["saved_at"]
        entry = {"action": action, "reason": reason}
        if action == "override_expected":
            if res["status"] != "mismatch" or "actual_result" not in res:
                print(f"  WARNING: skipping saved_at={saved_at!r}: no actual result "
                      f"available to store (status={res['status']})", file=sys.stderr)
                continue
            entry["dc_apply_result"] = [strip_volatile(recs) for recs in res["actual_result"]]
        pr_overrides[saved_at] = entry
        written.append(saved_at)

    with open(path, 'w') as f:
        json.dump(raw, f, indent=2)
        f.write("\n")

    return written


def decode_token(token):
    """Decode an editor-link token without verifying its signature."""
    compressed = base64.b64decode(unquote(token))
    raw = gzip.decompress(compressed)
    payload = json.loads(raw.decode('utf-8'))
    payload.pop("_signature", None)
    return payload


def get_editor_payloads(body):
    payloads = []
    for token in EDITOR_URL_PATTERN.findall(body):
        try:
            payloads.append(decode_token(token))
        except Exception as e:
            print(f"  WARNING: could not decode token: {e}", file=sys.stderr)
    return payloads


def strip_volatile(records):
    """Deep-copy records dropping any '_dc' key, for comparison purposes."""
    cleaned = []
    for rec in records:
        cleaned.append({k: v for k, v in rec.items() if k not in VOLATILE_KEYS})
    return cleaned


def sort_key(rec):
    return json.dumps(rec, sort_keys=True)


def records_equal(expected, actual):
    e = sorted((strip_volatile(expected)), key=sort_key)
    a = sorted((strip_volatile(actual)), key=sort_key)
    return e == a


def normalize_params(params):
    """
    The online editor stores params as {key: [value, ...]} (query-string-style,
    even for single-valued fields). apply_template()/resolve_variables() expect
    a plain {key: value} mapping, so collapse single-element lists.
    """
    normalized = {}
    for key, value in (params or {}).items():
        if isinstance(value, list):
            normalized[key] = value[0] if value else ""
        else:
            normalized[key] = value
    return normalized


def replay_payload(payload):
    """
    Re-run apply_template using the template/inputs embedded in the payload.
    Returns (actual_result_tuple, error) - error is an exception if raised.
    """
    template = payload.get("template")
    if not template:
        return None, ValueError("payload has no 'template'")

    has_redir = any(r.get("type") in ("REDIR301", "REDIR302")
                     for r in template.get("records", []))
    dc = DomainConnect(
        template=template,
        redir_template_records=DEFAULT_REDIRECT_RECORDS if has_redir else None,
    )
    try:
        actual = dc.apply_template(
            zone_records=json.loads(json.dumps(payload.get("zone_records", []))),
            domain=payload.get("domain", ""),
            host=payload.get("host", ""),
            params=normalize_params(payload.get("params", {})),
            group_ids=payload.get("group_ids") or None,
            ignore_signature=payload.get("ignore_signature", False),
            multi_aware=payload.get("multi_aware", False),
        )
        return actual, None
    except Exception as e:
        return None, e


def compare_payload(payload, override=None):
    """
    Returns a dict describing the comparison outcome for one editor-test payload:
      {"status": "match"|"mismatch"|"error"|"ignored", "detail": ...}

    override, if given, is the entry from the overrides file for this exact
    link (matched by PR number + saved_at). An "ignore" action short-circuits
    to status "ignored" without replaying the payload at all. An
    "override_expected" action substitutes its own dc_apply_result for the
    payload's before comparing.
    """
    if override is not None and override.get("action") == "ignore":
        return {"status": "ignored", "detail": override.get("reason")}

    expected = payload.get("dc_apply_result")
    if override is not None and override.get("action") == "override_expected":
        expected = override["dc_apply_result"]
    if not expected or len(expected) != 3:
        return {"status": "skipped", "detail": "no dc_apply_result in payload"}

    actual, error = replay_payload(payload)
    if error is not None:
        return {"status": "error", "detail": f"{type(error).__name__}: {error}"}

    expected_new, expected_deleted, expected_final = expected
    actual_new, actual_deleted, actual_final = actual

    mismatches = []
    for label, exp, act in (
        ("new_records", expected_new, actual_new),
        ("deleted_records", expected_deleted, actual_deleted),
        ("final_records", expected_final, actual_final),
    ):
        if not records_equal(exp, act):
            mismatches.append({
                "field": label,
                "expected": strip_volatile(exp),
                "actual": strip_volatile(act),
            })

    if mismatches:
        return {"status": "mismatch", "detail": mismatches, "actual_result": list(actual)}
    return {"status": "match", "detail": None}


def template_id(template):
    return f"{template.get('providerId', '?')}.{template.get('serviceId', '?')}"


def check_pr(pr, overrides=None):
    """Return a report dict for one cached PR, or None if it has no usable test links."""
    overrides = overrides or {}
    payloads = get_editor_payloads(pr["body"])
    if not payloads:
        return None

    results = []
    for payload in payloads:
        template = payload.get("template", {})
        saved_at = payload.get("saved_at")
        override = overrides.get((pr["number"], saved_at))
        outcome = compare_payload(payload, override=override)
        results.append({
            "template_id": template_id(template) if template else None,
            "domain": payload.get("domain"),
            "host": payload.get("host"),
            "saved_at": saved_at,
            "template": template,
            "zone_records": payload.get("zone_records", []),
            "params": payload.get("params", {}),
            "group_ids": payload.get("group_ids", []),
            "ignore_signature": payload.get("ignore_signature", False),
            "multi_aware": payload.get("multi_aware", False),
            **outcome,
        })

    if not any(r["status"] in ("mismatch", "error") for r in results):
        overall = "ok" if any(r["status"] == "match" for r in results) else "skipped"
    else:
        overall = "fail"

    return {
        "number": pr["number"],
        "title": pr["title"],
        "merged_at": pr["merged_at"],
        "overall": overall,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None,
                         help="Max number of NEW PRs to fetch from GitHub this run")
    parser.add_argument("--refresh", action="store_true",
                         help="Re-fetch all PRs from GitHub, ignoring the cache")
    parser.add_argument("--pr", type=int, default=None,
                         help="Only check a single PR number (must be cached or fetchable)")
    parser.add_argument("--report", default=os.path.join(CACHE_DIR, "report.json"),
                         help="Path to write the JSON report")
    parser.add_argument("--full-report", action="store_true",
                         help="Include PRs/results that matched in the JSON report "
                              "(default: only PRs with a mismatch or error are written)")
    parser.add_argument("--overrides", default=DEFAULT_OVERRIDES_FILE,
                         help="Path to the overrides file (default: overrides.json "
                              "next to this script)")
    parser.add_argument("--add-to-override-ignore", metavar="REASON", default=None,
                         help="For every currently-mismatching/erroring link in --pr, "
                              "add an 'ignore' entry to the overrides file with this reason. "
                              "Requires --pr.")
    parser.add_argument("--add-to-override-result", metavar="REASON", default=None,
                         help="For every currently-mismatching link in --pr, add an "
                              "'override_expected' entry to the overrides file with this "
                              "reason, storing the library's current actual output as the "
                              "new expected result. Requires --pr.")
    args = parser.parse_args()

    if (args.add_to_override_ignore or args.add_to_override_result) and args.pr is None:
        print("--add-to-override-ignore/--add-to-override-result require --pr", file=sys.stderr)
        return 1
    if args.add_to_override_ignore and args.add_to_override_result:
        print("--add-to-override-ignore and --add-to-override-result are mutually exclusive",
              file=sys.stderr)
        return 1

    overrides = load_overrides(args.overrides)

    known = {} if args.refresh else load_cache()
    if args.refresh:
        rewrite_cache({})

    if args.pr is not None and args.pr in known and not args.refresh:
        fetched_new = []
    else:
        print("Fetching merged PRs from GitHub" +
              (f" (limit {args.limit})" if args.limit else "") + "...")
        fetched_new = []
        for pr in fetch_merged_prs(known.keys(), limit=args.limit, stop_at_pr=args.pr):
            append_cache(pr)
            known[pr["number"]] = pr
            fetched_new.append(pr["number"])
        print(f"  fetched {len(fetched_new)} new PR(s); cache now has {len(known)} PR(s)")

    if args.pr is not None:
        if args.pr not in known:
            print(f"PR #{args.pr} not found (not merged, or beyond fetch limit)", file=sys.stderr)
            return 1
        prs_to_check = [known[args.pr]]
    else:
        prs_to_check = list(known.values())

    reports = []
    for pr in prs_to_check:
        report = check_pr(pr, overrides=overrides)
        if report is not None:
            reports.append(report)

    if args.add_to_override_ignore or args.add_to_override_result:
        action = "ignore" if args.add_to_override_ignore else "override_expected"
        reason = args.add_to_override_ignore or args.add_to_override_result
        pr_report = next((r for r in reports if r["number"] == args.pr), None)
        if pr_report is None or not any(res["status"] in ("mismatch", "error")
                                         for res in pr_report["results"]):
            print(f"\nNo mismatching/erroring links found for PR #{args.pr}; "
                  f"nothing added to overrides.")
        else:
            written = add_override_entries(args.overrides, args.pr, action, reason,
                                            pr_report["results"])
            print(f"\nAdded {len(written)} '{action}' override entry/entries for PR #{args.pr} "
                  f"to {args.overrides}: {', '.join(written)}")
            overrides = load_overrides(args.overrides)
            reports = [check_pr(pr, overrides=overrides) for pr in prs_to_check]
            reports = [r for r in reports if r is not None]

    ok = [r for r in reports if r["overall"] == "ok"]
    failed = [r for r in reports if r["overall"] == "fail"]

    print(f"\nChecked {len(reports)} PR(s) with test links "
          f"({len(known) - len(reports)} skipped, no test links found)")
    print(f"  OK:     {len(ok)}")
    print(f"  FAILED: {len(failed)}")

    for r in failed:
        print(f"\nFAIL PR #{r['number']}: {r['title']} ({r['merged_at']})")
        print(f"  https://github.com/{REPO}/pull/{r['number']}")
        for res in r["results"]:
            if res["status"] not in ("mismatch", "error"):
                continue
            print(f"  [{res['status']}] template={res['template_id']} "
                  f"domain={res['domain']} host={res['host']!r}")
            if res["status"] == "error":
                print(f"    {res['detail']}")
            else:
                for m in res["detail"]:
                    print(f"    field={m['field']}")
                    print(f"      expected: {json.dumps(m['expected'])}")
                    print(f"      actual:   {json.dumps(m['actual'])}")

    report_reports = reports if args.full_report else failed
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, 'w') as f:
        json.dump({
            "checked": len(reports),
            "ok": len(ok),
            "failed": len(failed),
            "reports": report_reports,
        }, f, indent=2)
    print(f"\nReport written to {args.report}"
          + ("" if args.full_report else " (failures only; pass --full-report for everything)"))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
