# Scientific pre-review, 15 September 2026

An independent scientific pre-review of all 650 v0.1 profiles, produced with AI assistance
(Claude Opus 5) at the repository owner's request. **It is not the named, domain-qualified
scientific sign-off that `PROFILE_REVIEW.md` requires, and must not be recorded as one.** No
evidence file was written to `source/reviews/`.

| File | What it is |
|---|---|
| `BMCS-v0.1-Referee-Report.pdf` | 106-page report: engine evidence, 14 systemic findings, per-profile findings, verdict register, decision rules, sources |
| `change-request.json` | The machine-readable change request (8.6 MB): every finding, contract-area and item decision, fixture audit, and 5,829 answers to the packets' reviewer questions |
| `bmcs-referee-report.html` | The same report as a browsable page |
| `build_change_request.py`, `emit_review.py` | Rebuild `change-request.json` from the packets, profiles and fixtures |
| `make_pdf.py`, `report-template.html` | Render the PDF and the HTML page |

```bash
python3 docs/scientific-remediation/pre-review-2026-09-15/emit_review.py   # rebuild the change request
python3 docs/scientific-remediation/pre-review-2026-09-15/make_pdf.py      # rebuild the PDF (needs reportlab; uses macOS system fonts)
```

## Read it with these corrections

The report stands as a fault report. These parts do not, and
[../REMEDIATION_PLAN.md](../REMEDIATION_PLAN.md) section 2 carries the full list:

- The `136 BLOCK / 514 CHANGES_REQUIRED` split is **withdrawn**. Nearly every defect comes from
  shared generator and comparison code, so the conclusion is simply that all 650 profiles are
  unsuitable for GA review until those foundations are fixed. The per-profile table remains useful
  only as an index of which profiles show which symptom.
- The blanket candidate-item decisions are **withdrawn** (over-broad: censoring, ontology terms,
  artifact checksums). Item levels are decided per profile.
- Four conclusions were stated too absolutely: dense-to-sparse losslessness, Celsius to kelvin,
  identifier mapping loss, and the meaning of "any species". Each is now a named design decision.
- S12 miscounted the security profiles: 25 clinical and 25 epidemiology, not 50 clinical.
- Sources are now pinned in [../sources/sources.lock.json](../sources/sources.lock.json), but most
  entries pin a Crossref citation record rather than the article itself. Paywalled papers and
  licensed standards still need a reviewer to pin their own copy.
- The HTML page and the PDF now open with a Corrections section carrying this list, and the verdict
  split is labelled as withdrawn wherever it appears.

The findings that survived replay are now reproducible tests in
[`scientific-checks/v0.1/cases.json`](../../../scientific-checks/v0.1/cases.json). Prefer those
tests over the report's prose when the two disagree: the tests are executable and the prose is not.
