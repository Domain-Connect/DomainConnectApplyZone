# coding=utf-8
"""
Shared utilities for the YAML-driven compliance test harnesses.

Used by test_process_records.py and test_apply_template.py.
"""
import glob
import os

import yaml

# Root directory for compliance test assets (YAML suites and template files).
DEFINITIONS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_definitions")
TEMPLATE_DIR    = os.path.join(DEFINITIONS_DIR, "templates")

from domainconnectzone import (
    HostRequired,
    InvalidData,
    InvalidSignature,
    InvalidTemplate,
    MissingParameter,
)

# ---------------------------------------------------------------------------
# Exception name → class mapping
# ---------------------------------------------------------------------------
EXCEPTION_MAP = {
    "HostRequired":     HostRequired,
    "InvalidData":      InvalidData,
    "InvalidSignature": InvalidSignature,
    "InvalidTemplate":  InvalidTemplate,
    "MissingParameter": MissingParameter,
    "TypeError":        TypeError,
}

# ---------------------------------------------------------------------------
# Allowed YAML keys shared by both harnesses
# ---------------------------------------------------------------------------
_SUITE_KEYS  = {"version", "suite_type", "description", "tests"}
_CASE_KEYS   = {"id", "description", "input", "expect"}
_EXPECT_KEYS = {"new_count", "delete_count", "records", "exception"}

_ZONE_RECORD_KEYS = {
    "type", "name", "data", "ttl",
    "priority", "protocol", "service", "weight", "port",
    "_dc",
}

# ---------------------------------------------------------------------------
# Key-validation helpers
# ---------------------------------------------------------------------------
def check_keys(mapping, allowed, context):
    """Raise ValueError if *mapping* contains any key not in *allowed*."""
    unknown = set(mapping) - allowed
    if unknown:
        raise ValueError(
            "Unknown key(s) {} in {}".format(sorted(unknown), context)
        )


def validate_zone_record(record, context):
    """Validate a single zone record (input or expected output)."""
    check_keys(record, _ZONE_RECORD_KEYS, context)
    if "_dc" in record and not isinstance(record["_dc"], object):
        raise ValueError("_dc not an object: {}".format(record["_dc"]))


def validate_common_case(case, inp, ctx, input_keys):
    """
    Validate fields that are common to every test case regardless of suite type:
    case-level keys, input-level keys, expect-level keys, and all zone records
    (both in input.zone_records and expect.records).

    *input_keys* is the suite-specific set of allowed input keys.
    """
    check_keys(case, _CASE_KEYS, ctx)
    check_keys(inp, input_keys, "input of {}".format(ctx))
    check_keys(case.get("expect", {}), _EXPECT_KEYS, "expect of {}".format(ctx))
    for i, rec in enumerate(inp.get("zone_records") or []):
        validate_zone_record(rec, "zone_records[{}] of {}".format(i, ctx))
    for i, rec in enumerate((case.get("expect") or {}).get("records") or []):
        validate_zone_record(rec, "expect.records[{}] of {}".format(i, ctx))


# ---------------------------------------------------------------------------
# Record sort helpers (used when comparing expected vs actual zone state)
# ---------------------------------------------------------------------------
def _sort_key(record):
    return (
        record.get("type", ""),
        record.get("name", ""),
        record.get("ttl", 0),
        record.get("data", ""),
    )


def sorted_records(records):
    """Return *records* sorted by (type, name, ttl, data), or None."""
    if records is None:
        return None
    return sorted(records, key=_sort_key)


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------
def load_suites(directory, suite_type):
    """
    Yield (path, suite) for every *.yaml file in *directory* whose top-level
    ``suite_type`` field equals *suite_type*.

    Also validates the top-level suite keys before yielding.
    """
    for path in sorted(glob.glob(os.path.join(directory, "*.yaml"))):
        with open(path) as f:
            suite = yaml.safe_load(f)
        if suite.get("suite_type") != suite_type:
            continue
        check_keys(suite, _SUITE_KEYS, "suite file {!r}".format(path))
        yield path, suite


# ---------------------------------------------------------------------------
# Test-injection helper
# ---------------------------------------------------------------------------
def inject_tests(test_class, suite_type, directory, make_test_fn):
    """
    Scan *directory* for YAML suites matching *suite_type*, call
    *make_test_fn(case)* for each test case, and attach the returned method
    to *test_class*.  Raises ValueError on duplicate test IDs.
    """
    for path, suite in load_suites(directory, suite_type):
        for case in suite["tests"]:
            test_name = "test_" + case["id"]
            if hasattr(test_class, test_name):
                raise ValueError(
                    "Duplicate test id {!r} found in {!r}".format(
                        case["id"], path
                    )
                )
            setattr(test_class, test_name, make_test_fn(case))
