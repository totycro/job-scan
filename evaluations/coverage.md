# Feature acceptance coverage and review matrix

The owner approved all shared source-content reviews and all focused fixture content/expectations on 2026-11-06. Existing shared criterion expectations remain approved. Live results and their manual semantic reviews are recorded separately in `.local/evaluations/`. A successful run
requires every entry in `manifest.json` plus manual semantic/evidence/usability review.

| Requirement/scenario | Cases or checks |
| --- | --- |
| FR-001 / scenario 6 / SC-003 input failures | tests/unit/test_cli.py; loading, ambiguous |
| FR-002 / scenario 5 / SC-002 | posting-03 related cards; structure-pair/allowed and expected |
| FR-003 / scenarios 1,4 | posting-02, posting-03; remote-restrictions |
| FR-004 / scenario 2 | hybrid-allowed, hybrid-expected, qualitative, posting-01 |
| FR-005 / SC-001 evidence | all cases; test_evidence.py; manual source relevance review |
| FR-006 / scenario 3 | missing, conflict, flexible, office-days |
| FR-007 / SC-004 usability | all successful reports; manual owner review |
| Unusable source / loading shell | loading |
| Office-day arithmetic | office-days |
| Untrusted page instructions | untrusted-instructions |

The structure pair retains identical text in identical order and changes only the HTML
associations (`aria-labelledby`). It must produce different target-role schedules.

Pending reviews do not prevent independent coding. They cannot establish acceptance.
Never approve source or criterion metadata automatically or copy inference into expectations.
