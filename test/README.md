# Domain Connect Apply-Zone — Test Suite

This directory contains the test suite for the `domainconnectzone` library.

## Files

| File | Purpose |
|------|---------|
| `test_definitions/process_records_tests.yaml` | Language-agnostic compliance suite for `process_records` (88 cases) |
| `test_definitions/apply_template_tests.yaml` | Language-agnostic compliance suite for `apply_template` (12 cases) |
| `test_process_records.py` | Python harness that loads and runs all `process_records` YAML suites |
| `test_apply_template.py` | Python harness that loads and runs all `apply_template` YAML suites |
| `harness_utils.py` | Shared helpers for the two YAML harnesses |
| `test_DomainConnect.py` | Python-specific API tests (constructor, signatures, …) |
| `test_DomainConnectTemplates.py` | Tests for template enumeration / validation |
| `test_sigutil.py` | Tests for the signature utility module |
| `test_qsutils.py` | Tests for the query-string utility module |
| `test_definitions/templates/` | Template JSON files used by `apply_template` test cases |

---

## Compliance test suites

### What they are

`test_definitions/process_records_tests.yaml` and `test_definitions/apply_template_tests.yaml` are
self-contained, language-agnostic test specifications.  Any implementation of
the Domain Connect zone-apply logic — regardless of programming language — can
load these files and verify correctness against them.

The tests cover the full record-processing rule set defined in the
[Domain Connect Specification](https://github.com/Domain-Connect/DomainConnectSpecification):
conflict-deletion rules per record type, variable substitution, group
filtering, multi-aware / multi-instance semantics, redirect records, and
input validation.

### Suite type

Each YAML file declares its type at the top level:

```yaml
suite_type: process_records   # or apply_template
```

Test harnesses scan the directory for `*.yaml` files and process only files
whose `suite_type` matches the harness.  This means you can add extra suite
files (e.g. `my_custom_records_tests.yaml` with `suite_type: process_records`)
and they will be picked up automatically.

### Test types

| Suite type | Description |
|------------|-------------|
| `process_records` | Calls the low-level record processor with inline `template_records`. No template file required. |
| `apply_template` | Loads a real template file by `provider_id` / `service_id` from `test/templates/` and applies it via the high-level API. |

### Structure of a test case

```yaml
- id: cname_delete                    # unique snake_case identifier
  description: "..."                  # human-readable description

  input:
    zone_records: [...]               # current zone state (list of records)
    template_records: [...]           # records to apply (process_records only)
    domain: foo.com                   # domain being managed
    host: bar                         # sub-domain ("" = apex)
    params: {VAR: value}              # variable substitution map

    # optional (process_records)
    group_ids: ["1"]                  # filter to these group IDs
    multi_aware: false
    multi_instance: false
    provider_id: null
    service_id: null
    unique_id: null
    redirect_records: null            # backing A/AAAA for REDIR types

    # optional (apply_template)
    provider_id: exampleservice.domainconnect.org
    service_id: template1
    ignore_signature: false
    qs: null                          # query string for sig verification
    sig: null                         # base64 signature
    key: null                         # DNS key sub-domain
    multi_aware: false
    unique_id: null

  expect:
    new_count: 1                      # number of records added
    delete_count: 0                   # number of records deleted
    records: [...]                    # expected final zone state (sorted)

    # OR, for error cases:
    exception: InvalidData            # expected exception name
```

### Record sorting

When comparing `expect.records` against the actual result, records are sorted
by `(type, name, ttl, data)`.  Test harnesses must apply the same sort before
asserting equality.

### Random `_dc.id` values

When `multi_aware: true` and no `unique_id` is given, the implementation
assigns a random string to `_dc.id`.  Test harnesses **must** normalise these
random values to the sentinel string `"<test only: random>"` before comparing
against `expect.records`.

### Exception names

| Name | Meaning |
|------|---------|
| `InvalidData` | Bad record content or format (IP address, DNS name, …) |
| `InvalidTemplate` | Malformed, missing, or inapplicable template |
| `MissingParameter` | A required `%VARIABLE%` was not supplied |
| `HostRequired` | Template requires a host label but none was provided |
| `TypeError` | Unrecognised record type string |

### Zone record fields

| Field | Type | Notes |
|-------|------|-------|
| `type` | string | `A`, `AAAA`, `CNAME`, `MX`, `NS`, `TXT`, `SRV`, `REDIR301`, `REDIR302`, or a custom type (e.g. `CAA`, `TYPE256`) |
| `name` | string | Relative owner name; `"@"` = apex |
| `data` | string | Record data / rdata |
| `ttl` | integer | Time-to-live in seconds |
| `priority` | integer | MX preference / SRV priority |
| `protocol` | string | SRV: `"UDP"`, `"TCP"`, `"TLS"` |
| `service` | string | SRV: service host |
| `weight` | integer | SRV weight |
| `port` | integer | SRV port |
| `_dc` | mapping | Multi-aware provenance: `id`, `providerId`, `serviceId`, `host`, `essential` (`"Always"` or `"OnApply"`) |

### Template record fields

Template records use `host` (or `name` for SRV) rather than the resolved
`name`.  Values may contain `%VARIABLE%` tokens and the special token `"@"`.

| Type | Key fields |
|------|-----------|
| A / AAAA / CNAME / NS | `host`, `pointsTo`, `ttl` |
| MX | `host`, `pointsTo`, `ttl`, `priority` |
| TXT | `host`, `data`, `ttl`, `txtConflictMatchingMode`, `txtConflictMatchingPrefix` |
| SRV | `name`, `target`, `protocol`, `service`, `priority`, `weight`, `port`, `ttl` |
| SPFM | `host`, `spfRules` |
| REDIR301 / REDIR302 | `host`, `target` |
| Custom (CAA, TYPE\<N\>, …) | `host`, `data`, `ttl` |

---

## Running the tests

The virtualenv `.venv/` in the repository root has all dependencies installed.

```bash
# Run all tests
.venv/bin/python -m pytest test/

# Run process_records compliance tests (verbose)
.venv/bin/python -m pytest test/test_process_records.py -v

# Run apply_template compliance tests (verbose)
.venv/bin/python -m pytest test/test_apply_template.py -v

# Run a single compliance test by ID
.venv/bin/python -m pytest test/test_process_records.py::ProcessRecordsTests::test_cname_delete -v
.venv/bin/python -m pytest test/test_apply_template.py::ApplyTemplateTests::test_template_apply_basic -v

# Run Python-API tests only
.venv/bin/python -m pytest test/test_DomainConnect.py -v

# Run with coverage
.venv/bin/python -m coverage run -m unittest discover ./test
.venv/bin/python -m coverage report -m
```

---

## Porting the compliance suite to another language

1. Copy `test_definitions/process_records_tests.yaml`,
   `test_definitions/apply_template_tests.yaml`, and the `test_definitions/templates/` directory.
2. Parse the YAML in your test framework of choice.
3. Scan for `*.yaml` files; check the top-level `suite_type` field to
   determine which harness should handle each file.
4. For each test case:
   - If `suite_type` is `process_records`: call your record-processor with
     the `input` fields; check `expect.new_count`, `expect.delete_count`, and
     sorted `expect.records` (or catch `expect.exception`).
   - If `suite_type` is `apply_template`: load the template identified by
     `provider_id` / `service_id` from `templates/`, apply it, and assert the
     same outputs.  Inject backing redirect records
     `[{A: 127.0.0.1, ttl: 600}, {AAAA: ::1, ttl: 600}]` on your instance.
5. For `multi_aware: true` cases without a `unique_id`, replace any random
   `_dc.id` value with `"<test only: random>"` before comparing.
6. Map the exception names in `expect.exception` to your language's equivalent
   error types.

The full field reference is in the header comment block of each YAML file.
