# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

A `.venv` virtualenv already exists in the repo root with all dependencies installed. Use `.venv/bin/python` (or activate it) instead of the system Python.

### Run all tests
```bash
.venv/bin/python -m pytest test/
```

### Run a single test file
```bash
.venv/bin/python -m pytest test/test_DomainConnect.py
```

### Run a single test case
```bash
.venv/bin/python -m pytest test/test_DomainConnect.py::DomainConnectTests::test_method_name
```

### Run tests with coverage
```bash
./run_unittests_with_coverage.sh
# Equivalent to:
.venv/bin/python -m coverage run -m unittest discover ./test && .venv/bin/python -m coverage report -m
```

### Build documentation
```bash
./build_doc.sh
# Equivalent to: cd docs && make html
```

## Architecture

This is a Python library (`domainconnectzone`) implementing the [Domain Connect protocol](https://www.domainconnect.org/) for DNS providers. Its purpose is to apply/delete service templates against a DNS zone.

### Core concepts

- **Zone records**: Dicts with `type`, `name`, `data`, `ttl`, and optional `_dc` (template provenance metadata), `_delete`, `_replace` flags. Types: A, AAAA, CNAME, NS, TXT, MX, SRV.
- **Templates**: JSON files named `{providerId}.{serviceId}.json` stored in `domainconnectzone/templates/`. They contain record definitions with `%variable%` substitution syntax.
- **Host resolution**: Template record names are relative to the applied host/domain. `@` means the apex. Variables `%domain%`, `%host%`, `%fqdn%` are always available.

### Module structure

- **[DomainConnectImpl.py](domainconnectzone/DomainConnectImpl.py)** — Main logic. Key entry points:
  - `DomainConnect(provider_id, service_id, template_path)` — loads a template from a file
  - `DomainConnect(template=...)` — loads from a dict directly
  - `.apply_template(zone_records, domain, host, params, ...)` — applies template, mutates zone_records with `_delete` flags and returns new records
  - `.verify_sig(qs, sig, key)` — verifies PKCS1v15/SHA256 signature for async flow
  - `resolve_variables(input_, domain, host, params, recordKey)` — resolves `%var%` substitution
  - `process_records(template_records, zone_records, domain, host, params)` — standalone function used by `apply_template`
  - `get_records_variables(template_records, group)` — returns required variable metadata from a template

- **[DomainConnectTemplates.py](domainconnectzone/DomainConnectTemplates.py)** — `DomainConnectTemplates(template_path)` class for enumerating/validating all templates in a directory. Validates against `template.schema` if present.

- **[sigutil.py](domainconnectzone/sigutil.py)** — `verify_sig`, `generate_sig`, `get_publickey`. Public keys are fetched from DNS TXT records at `{key}.{syncPubKeyDomain}` in a segmented format.

- **[qsutil.py](domainconnectzone/qsutil.py)** — `qs2dict(qs)` and `qsfilter(qs, filter_items)` for parsing/filtering query strings (used in the async signature flow).

- **[validate.py](domainconnectzone/validate.py)** — Input validation helpers for IP addresses, hostnames, and DNS record fields.

### Exceptions (all in `domainconnectzone` namespace)

`InvalidTemplate`, `HostRequired`, `InvalidSignature`, `MissingParameter`, `InvalidData`

### Test layout

Tests live in `test/` and use `unittest`. Test templates are in `test/test_definitions/templates/`. Tests mock DNS lookups (sigutil) with `unittest.mock.patch`.

| File | Purpose |
|------|---------|
| `test_DomainConnect.py` | Python-specific API tests (constructor, signatures, prompt, validator helpers) |
| `test_DomainConnectTemplates.py` | Template enumeration / validation |
| `test_sigutil.py` | Signature utility module |
| `test_qsutils.py` | Query-string utility module |
| `test_process_records.py` | YAML-driven harness — scans for `suite_type: process_records` files |
| `test_apply_template.py` | YAML-driven harness — scans for `suite_type: apply_template` files |
| `test_definitions/process_records_tests.yaml` | 88 language-agnostic process_records compliance tests |
| `test_definitions/apply_template_tests.yaml` | 12 language-agnostic apply_template compliance tests |
| `harness_utils.py` | Shared helpers for the two YAML harnesses (not a test module) |

The two YAML harnesses scan the test directory for `*.yaml` files matching their `suite_type` and synthesise one `unittest.TestCase` method per case at import time. Adding a new `*.yaml` file with the right `suite_type` is picked up automatically. The harnesses validate all YAML keys at load time and raise `ValueError` on unknown fields.

`harness_utils.py` uses a `try/except ImportError` import idiom so it works both under pytest (package-relative import) and `unittest discover` (top-level import).

### Conflict resolution rules

When applying a template, existing zone records are marked `_delete=1` based on type-specific rules:
- **A/AAAA**: deletes same-host records of same type
- **CNAME**: deletes all non-NS records at that host
- **TXT**: deletes based on `txtConflictMatchingMode` (None/All/Prefix)
- **MX/SRV/NS**: deletes same-host records of same type
- **Custom/unknown types** (CAA, TYPE256, etc.): no conflict deletion — record is simply added; `data` supports `%variable%` substitution and `@`/empty resolves to fqdn
