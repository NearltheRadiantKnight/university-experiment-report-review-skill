# Domain Profiles

## Routing contract

`inspect_report.py` writes `domain_routing` into the manifest. Routing is based on extracted report text, not the filename. Each profile is local JSON under `assets/domain-profiles/`.

- `high`: load the selected profile and apply its evidence, screenshot, workflow, and review checks.
- `medium`: compare the first two candidates; apply only rules clearly supported by the document.
- `low`: use the general review methodology and state that the domain is unconfirmed.

The plan records `domain_profile`, `domain_confidence`, and `domain_profile_basis`. A profile augments teacher requirements; it never overrides them.

## Profiles

- `software-testing`: TestLink, QTP/UFT, Selenium, equivalence classes, boundary values, test cases, and defect evidence.
- `networking`: topology, addressing, routing/switching, terminal verification, Wireshark, and protocol fields.
- `database`: DBMS/version, schema, SQL, rows/columns, transactions, execution plans, and privacy.
- `os-programming`: source code, compiler/runtime, input/output, boundary cases, algorithms, processes, threads, and system behavior.
- `physical-science`: instruments, range, units, raw data, plots, fitting, simulation, and error analysis.

Never invent parameters that a profile says are important. Instead add them to the missing-information checklist.