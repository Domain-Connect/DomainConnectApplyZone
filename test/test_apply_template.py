# coding=utf-8
"""
YAML-driven compliance test harness for apply_template tests.

Scans the test directory for *.yaml files whose top-level `suite_type` is
"apply_template", loads all matching files, and synthesises one
unittest.TestCase method per test case.

Usage
-----
    pytest test/test_apply_template.py -v
    pytest test/test_apply_template.py::ApplyTemplateTests::test_template_apply_basic -v
"""
import os
import unittest

from domainconnectzone import DomainConnect

try:
    from .harness_utils import (
        DEFINITIONS_DIR, EXCEPTION_MAP, inject_tests,
        load_suites, sorted_records, TEMPLATE_DIR, validate_common_case,
    )
except ImportError:
    from harness_utils import (  # type: ignore[no-redef]
        DEFINITIONS_DIR, EXCEPTION_MAP, inject_tests,
        load_suites, sorted_records, TEMPLATE_DIR, validate_common_case,
    )

_DIR = os.path.dirname(os.path.realpath(__file__))

# Redirect records injected for all apply_template tests.
_REDIR_TEMPLATE_RECORDS = [
    {"type": "A",    "pointsTo": "127.0.0.1", "ttl": 600},
    {"type": "AAAA", "pointsTo": "::1",        "ttl": 600},
]

# ---------------------------------------------------------------------------
# apply_template-specific allowed input keys
# ---------------------------------------------------------------------------
_INPUT_KEYS = {
    "provider_id", "service_id", "zone_records", "domain", "host", "params",
    "group_ids", "ignore_signature", "multi_aware", "unique_id",
    "qs", "sig", "key",
}


# ---------------------------------------------------------------------------
# Suite validation
# ---------------------------------------------------------------------------
def _validate_suite(suite, path):
    for case in suite.get("tests", []):
        ctx = "test case {!r} in {!r}".format(case.get("id", "?"), path)
        validate_common_case(case, case.get("input", {}), ctx, _INPUT_KEYS)


# ---------------------------------------------------------------------------
# Test factory
# ---------------------------------------------------------------------------
def _make_test(case):
    """Return a test method that exercises DomainConnect.apply_template."""
    inp = case["input"]
    exp = case["expect"]
    title = case.get("description", case["id"])

    expected_exception = EXCEPTION_MAP.get(exp.get("exception"))
    expected_records = exp.get("records")
    new_count = exp.get("new_count")
    delete_count = exp.get("delete_count")

    multi_aware = inp.get("multi_aware", False)
    unique_id   = inp.get("unique_id")

    def test_fn(self):
        dc = DomainConnect(
            inp["provider_id"],
            inp["service_id"],
            TEMPLATE_DIR,
            redir_template_records=_REDIR_TEMPLATE_RECORDS,
        )

        zone_records = list(inp.get("zone_records") or [])

        apply_kwargs = {
            "group_ids":        inp.get("group_ids"),
            "qs":               inp.get("qs"),
            "sig":              inp.get("sig"),
            "key":              inp.get("key"),
            "ignore_signature": inp.get("ignore_signature", False),
            "multi_aware":      multi_aware,
            "unique_id":        unique_id,
        }

        if expected_exception is not None:
            with self.assertRaises(expected_exception, msg=title):
                dc.apply_template(
                    zone_records,
                    inp["domain"],
                    inp.get("host") or "",
                    inp.get("params") or {},
                    **apply_kwargs,
                )
            return

        new_recs, del_recs, final_recs = dc.apply_template(
            zone_records,
            inp["domain"],
            inp.get("host") or "",
            inp.get("params") or {},
            **apply_kwargs,
        )

        # Normalise random _dc.id values when no unique_id was supplied.
        if multi_aware and unique_id is None and final_recs is not None:
            for r in final_recs:
                if "_dc" in r and "id" in r["_dc"]:
                    r["_dc"]["id"] = "<test only: random>"

        if new_count is not None:
            self.assertEqual(len(new_recs), new_count, title)
        if delete_count is not None:
            self.assertEqual(len(del_recs), delete_count, title)
        if expected_records is not None:
            self.assertEqual(
                sorted_records(final_recs),
                sorted_records(expected_records),
                title,
            )

    test_fn.__name__ = "test_" + case["id"]
    test_fn.__doc__ = title
    return test_fn


# ---------------------------------------------------------------------------
# Load suites, validate, and inject tests
# ---------------------------------------------------------------------------
class ApplyTemplateTests(unittest.TestCase):
    """Compliance tests for apply_template, loaded from *.yaml suite files."""


for _path, _suite in load_suites(DEFINITIONS_DIR, "apply_template"):
    _validate_suite(_suite, _path)

inject_tests(ApplyTemplateTests, "apply_template", DEFINITIONS_DIR, _make_test)


if __name__ == "__main__":
    unittest.main()
