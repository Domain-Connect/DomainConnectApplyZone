# coding=utf-8
"""
YAML-driven compliance test harness for process_records tests.

Scans the test directory for *.yaml files whose top-level `suite_type` is
"process_records", loads all matching files, and synthesises one
unittest.TestCase method per test case.

Usage
-----
    pytest test/test_process_records.py -v
    pytest test/test_process_records.py::ProcessRecordsTests::test_cname_delete -v
"""
import os
import unittest

from domainconnectzone import process_records

try:
    from .harness_utils import (
        DEFINITIONS_DIR, EXCEPTION_MAP, check_keys, inject_tests,
        load_suites, sorted_records, validate_common_case,
    )
except ImportError:
    from harness_utils import (  # type: ignore[no-redef]
        DEFINITIONS_DIR, EXCEPTION_MAP, check_keys, inject_tests,
        load_suites, sorted_records, validate_common_case,
    )

_DIR = os.path.dirname(os.path.realpath(__file__))

# ---------------------------------------------------------------------------
# process_records-specific allowed input keys and template record keys
# ---------------------------------------------------------------------------
_INPUT_KEYS = {
    "zone_records", "template_records", "domain", "host", "params",
    "group_ids", "multi_aware", "multi_instance",
    "provider_id", "service_id", "unique_id", "redirect_records",
}

_TEMPLATE_RECORD_KEYS = {
    "type", "host", "ttl", "groupId", "essential",
    # A/AAAA/CNAME/NS/MX
    "pointsTo", "priority",
    # TXT
    "data", "txtConflictMatchingMode", "txtConflictMatchingPrefix",
    # SRV
    "name", "target", "protocol", "service", "weight", "port",
    # SPFM
    "spfRules",
    # REDIR301/REDIR302
    "target",
}


# ---------------------------------------------------------------------------
# Suite validation
# ---------------------------------------------------------------------------
def _validate_suite(suite, path):
    for case in suite.get("tests", []):
        ctx = "test case {!r} in {!r}".format(case.get("id", "?"), path)
        inp = case.get("input", {})
        validate_common_case(case, inp, ctx, _INPUT_KEYS)
        for i, rec in enumerate(inp.get("template_records") or []):
            check_keys(rec, _TEMPLATE_RECORD_KEYS,
                       "template_records[{}] of {}".format(i, ctx))
        for i, rec in enumerate(inp.get("redirect_records") or []):
            check_keys(rec, _TEMPLATE_RECORD_KEYS,
                       "redirect_records[{}] of {}".format(i, ctx))


# ---------------------------------------------------------------------------
# Test factory
# ---------------------------------------------------------------------------
def _make_test(case):
    """Return a test method that exercises process_records."""
    inp = case["input"]
    exp = case["expect"]
    title = case.get("description", case["id"])

    expected_exception = EXCEPTION_MAP.get(exp.get("exception"))
    expected_records = exp.get("records")
    new_count = exp.get("new_count")
    delete_count = exp.get("delete_count")

    def test_fn(self):
        kwargs = {
            "multi_aware":      inp.get("multi_aware", False),
            "multi_instance":   inp.get("multi_instance", False),
            "provider_id":      inp.get("provider_id"),
            "service_id":       inp.get("service_id"),
            "unique_id":        inp.get("unique_id"),
            "redirect_records": inp.get("redirect_records"),
            "group_ids":        inp.get("group_ids") or (),
        }

        zone_records = list(inp.get("zone_records") or [])

        if expected_exception is not None:
            with self.assertRaises(expected_exception, msg=title):
                process_records(
                    inp["template_records"],
                    zone_records,
                    inp["domain"],
                    inp.get("host", ""),
                    inp.get("params") or {},
                    **kwargs,
                )
            return

        new_recs, del_recs, final_recs = process_records(
            inp["template_records"],
            zone_records,
            inp["domain"],
            inp.get("host", ""),
            inp.get("params") or {},
            **kwargs,
        )

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
class ProcessRecordsTests(unittest.TestCase):
    """Compliance tests for process_records, loaded from *.yaml suite files."""


for _path, _suite in load_suites(DEFINITIONS_DIR, "process_records"):
    _validate_suite(_suite, _path)

inject_tests(ProcessRecordsTests, "process_records", DEFINITIONS_DIR, _make_test)


if __name__ == "__main__":
    unittest.main()
