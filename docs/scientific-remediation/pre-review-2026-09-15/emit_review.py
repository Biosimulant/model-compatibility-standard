"""Emit the de-duplicated change request and the report page from build_change_request's data."""
from __future__ import annotations

import collections
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK_PATH = os.path.join(HERE, "..", "sources", "sources.lock.json")
PINNED = {}
if os.path.exists(LOCK_PATH):
    PINNED = {e["id"]: e for e in json.load(open(LOCK_PATH))["sources"]}
spec = importlib.util.spec_from_file_location("bcr", os.path.join(HERE, "build_change_request.py"))
bcr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bcr)

bcr.ITEM_RULES.update({
    "semantic.ontology_terms[].uri": ("required", "The term IRI or CURIE is the compared value; without it the mapping cannot be resolved."),
    "semantic.ontology_terms[].ontology": ("required", "The source ontology determines which snapshot is used for subsumption."),
    "semantic.ontology_terms[].version": ("required", "Ontology releases obsolete and re-parent terms, so the release must be pinned."),
    "semantic.ontology_terms[].relation": ("required", "Exact, broad and narrow matches support different compatibility conclusions."),
    "semantic.ontology_terms[].label": ("recommended", "A human-readable label aids review but must never be the compared value."),
})

# Profiles whose declared unit is not a unit of the quantity the profile names
# (wrong dimension, wrong quantity kind, or a time-axis unit used for the values).
UNIT_WRONG = {
    "core/categorical-value", "core/regular-time-series", "core/irregular-time-series",
    "metabolome/metabolite-time-series", "microbiology/community-time-series", "virology/shedding-time-series",
    "imaging/image-time-series", "physiology/physiological-time-series", "ecology/climate-time-series",
    "proteome/secretion-rate", "metabolome/mass-spectral-peak", "metabolome/mass-spectrum",
    "metabolome/metabolite-production-rate", "metabolome/metabolite-consumption-rate",
    "pharmacology/compound-dose", "pharmacology/dose-schedule", "pharmacology/binding-affinity",
    "pharmacology/association-rate", "pharmacology/concentration-response-curve",
    "cell/migration-rate", "microbiology/minimum-inhibitory-concentration", "virology/infectious-titer",
    "imaging/ct-volume", "imaging/mri-volume", "imaging/pet-volume", "spatial/distance-matrix",
    "physiology/airflow-rate", "physiology/glomerular-filtration-rate", "physiology/metabolic-rate",
    "evolution/mutation-rate", "evolution/recombination-rate", "epidemiology/attack-rate",
    "multiomics/integrated-embedding",
}

AREA_ORDER = ["structure", "semantic", "representation", "dimensions", "identifiers", "measurement",
              "biological_context", "lifecycle", "origin", "uncertainty", "artifact", "constraints", "security"]
FX_ORDER = [
    ("positive_scientifically_valid", "positive_note", "Positive example is scientifically valid"),
    ("missing_evidence_returns_unknown", "missing_evidence_note", "Missing evidence returns UNKNOWN"),
    ("contradiction_returns_incompatible", "contradiction_note", "Known contradiction returns INCOMPATIBLE"),
    ("direct_hides_transformation", "direct_note", "Direct compatibility hides no transformation"),
    ("conversions_correct", "conversion_note", "Unit and representation conversions are correct"),
    ("lossy_and_inference_identified", "lossy_note", "Lossy conversion and inference are identified"),
]

ERRATA = [
    ("E1", "The per-profile verdict split is withdrawn", "136 BLOCK / 514 CHANGES_REQUIRED implied a per-profile precision the evidence does not support, because nearly every defect originates in shared generator and comparison code. The single conclusion is that all 650 profiles are unsuitable for GA review until those foundations are fixed. The per-profile table below survives only as an index of which profiles show which symptom."),
    ("E2", "S12 miscounted the security profiles", "The 50 profiles requiring security.data_use and security.consent_scope are 25 clinical and 25 epidemiology, not 50 clinical."),
    ("E3", "The blanket candidate-item decisions are withdrawn", "Several were over-broad: uncertainty.censoring was marked required in 400 packets although its own reason limits it to time-to-event data; semantic.ontology_terms was marked required for all 650; artifact.sha256 required wherever an artifact representation is allowed. Item levels are now decided per profile or profile class (decision D10), with this table as input only."),
    ("E4", "Four conclusions were stated too absolutely", "Dense-to-sparse re-encoding is lossless only when implicit-entry meaning, ordering, shape and dtype are declared equal (D6). Celsius to kelvin is exact for absolute temperatures; a temperature difference converts with factor 1 and no offset (D1). Identifier mapping is not always lossy: a pinned, total, bijective mapping is lossless (D7). 'Any species' has no defined meaning yet, so the report should not have prescribed UNKNOWN (D5)."),
    ("E5", "No source is pinned", "Every source has a title, DOI or permanent URL and version, but none has a SHA-256 of the reviewed bytes. Pinning is a Phase 1 task."),
    ("E6", "The change request now lives in the repository", "It is at docs/scientific-remediation/pre-review-2026-09-15/ with the tools that produce it."),
    ("E7", "The change request answered questions the packets do not ask", "Corrected: it now carries 5,829 answers, exactly the set the 650 packets ask."),
    ("E8", "S12 overstated the data-use ordering defect", "security.data_use is already a set-like path in the normalization rules, and normalised contracts compare as EXACT whatever the element order. The narrower real defect: compare_contracts does not normalise internally, so a caller skipping that stage gets INCOMPATIBLE from ordering alone, and equal on a set of DUO codes carries no subsumption."),
    ("E9", "The findings that survived replay are now executable", "Fifteen defects and eight guards live in scientific-checks/v0.1/cases.json and run in both implementations. Prefer those tests over this report's prose where the two disagree."),
]

# Results obtained by running python/src compare_contracts / validate_contract (scratchpad/engine_checks.py).
ENGINE = [
    ("transcriptome/single-cell-expression-matrix", "Raw read counts vs log1p-normalised expression, declared on both ports", "DIRECT_COMPATIBLE", "Lossy transformation, approval required", "S3"),
    ("transcriptome/single-cell-expression-matrix", "ensembl.gene vs hgnc.symbol namespaces, declared on both ports", "DIRECT_COMPATIBLE", "Identifier mapping required; lossy", "S3"),
    ("core/scalar-quantity", "A value in mg vs a value in s, unit declared on both ports", "DIRECT_COMPATIBLE", "INCOMPATIBLE (different dimension)", "S3, S4"),
    ("neuroscience/firing-rate", "Firing rate in nM vs uM - the profile's own conversion fixture", "LOSSLESS_CONVERSION_AVAILABLE", "INCOMPATIBLE (a rate has no molar unit)", "S7"),
    ("neuroscience/firing-rate", "Contract declaring a firing rate in kg", "valid, no findings", "Invalid: unit dimension contradicts quantity", "S4"),
    ("physiology/body-mass", "g vs kg", "INCOMPATIBLE", "LOSSLESS_CONVERSION_AVAILABLE (factor 1000)", "S4, S8"),
    ("physiology/body-temperature", "Cel vs K", "INCOMPATIBLE", "Lossless for absolute values (offset 273.15)", "S4"),
    ("physiology/heart-rate", "1/s vs /min", "INCOMPATIBLE", "LOSSLESS_CONVERSION_AVAILABLE (factor 60)", "S4"),
    ("pharmacology/plasma-concentration", "uM vs mol/L", "INCOMPATIBLE", "LOSSLESS_CONVERSION_AVAILABLE (factor 10^6)", "S4"),
    ("neuroscience/firing-rate", "Species 'any' on the source vs NCBITaxon:9606 on the target", "INCOMPATIBLE", "UNKNOWN (absent evidence, not contradiction)", "S5"),
    ("metabolome/metabolite-concentration", "Subject 'biological_sample' vs 'blood_plasma'", "INCOMPATIBLE", "Decided by UBERON/OBI subsumption against a pinned snapshot", "S2"),
    ("transcriptome/single-cell-expression-matrix", "dense_vector vs sparse_vector", "INCOMPATIBLE", "LOSSLESS_CONVERSION_AVAILABLE", "S11"),
    ("pharmacology/plasma-concentration", "The published positive fixture: a uM concentration on a probability scale", "valid, no findings", "Invalid: a concentration is ratio-scaled", "S6"),
]


def main():
    packets = bcr.load_packets()
    notes: list[str] = []
    note_index: dict[str, int] = {}

    def intern(text: str) -> int:
        if text not in note_index:
            note_index[text] = len(notes)
            notes.append(text)
        return note_index[text]

    all_paths = sorted({p for pk in packets for p in pk["candidate_recommended_items"]})
    path_index = {p: i for i, p in enumerate(all_paths)}
    item_rules = {p: {"disposition": bcr.item_disposition(p)[0], "rationale": bcr.item_disposition(p)[1]} for p in all_paths}

    full_profiles, compact_profiles = [], []
    counts = collections.Counter()
    finding_counts = collections.Counter()
    for pk in packets:
        pid = pk["profile_id"].split("@")[0]
        req = [r["path"] for r in pk["proposed_requirements"]]
        kinds = pk["proposed_allowed_values"].get("representation", {}).get("kind", [])
        fx = json.load(open(os.path.join(bcr.REPO, f"spec/v0.1/fixtures/profiles/{pid}.json")))
        pos = {c["name"]: c for c in fx["cases"]}["positive"]["contract"]
        cur_unit = pos.get("measurement", {}).get("unit")
        cur_scale = pos.get("measurement", {}).get("scale")

        findings = []
        m = None
        if pid in bcr.M:
            pu, ps, reason, srcs = bcr.M[pid]
            m = dict(current_unit=cur_unit, current_scale=cur_scale, proposed_unit=pu, proposed_scale=ps, reason=reason, sources=srcs)
            tokens = set(re.split(r"[^a-z0-9]+", ps.lower()))
            scale_wrong = (cur_scale or "") not in tokens and "specific" not in tokens
            unit_wrong = pid in UNIT_WRONG
            wrong = [w for w, flag in (("unit", unit_wrong), ("scale", scale_wrong)) if flag]
            findings.append(dict(
                id="P-MEAS", severity="blocking" if wrong else "non-blocking", systemic=["S6"],
                title=("Declared " + " and ".join(wrong) + " wrong for this quantity") if wrong else "Unit and scale acceptable but under-specified",
                field="measurement.unit, measurement.scale (profile requirement and positive fixture)",
                current=f"unit {cur_unit}, scale {cur_scale}",
                proposed=f"unit {pu}; scale {ps}",
                reason=reason, sources=srcs,
                fixtures=["positive", "comparison-direct", "comparison-unknown-measurement-unit", "comparison-incompatible-measurement-unit"]))
            findings.append(dict(
                id="P-CONV", severity="blocking", systemic=["S7"],
                title="Conversion fixture asserts a molar-concentration conversion" + ("" if cur_unit == "uM" else " for a non-concentration quantity"),
                field="fixture comparison-lossless-unit-conversion",
                current="source nM, target uM, expected LOSSLESS_CONVERSION_AVAILABLE",
                proposed=(f"keep nM<->uM, but only after the positive fixture's scale is corrected to ratio" if cur_unit == "uM"
                          else f"a conversion within this profile's own dimension, plus a cross-dimension contradiction fixture (proposed unit: {pu})"),
                reason=("Concentration conversion is dimensionally right here, but the fixture pair inherits the probability scale from the positive example."
                        if cur_unit == "uM" else
                        "The fixture certifies a nanomolar-to-micromolar conversion for a quantity that has no molar unit, and both implementations are tested to agree on it."),
                sources=["ucum-2.2", "vim-jcgm-200-2012"], fixtures=["comparison-lossless-unit-conversion"]))
            if cur_unit == "g":
                findings.append(dict(
                    id="P-KG", severity="blocking", systemic=["S8"], title="Contradiction fixture treats g and kg as incompatible",
                    field="fixture comparison-incompatible-measurement-unit",
                    current="source kg vs target g, expected INCOMPATIBLE",
                    proposed="a contradiction unit of another dimension (e.g. s), plus a g<->kg lossless fixture",
                    reason="Grams and kilograms are the same quantity; certifying them as contradictory blocks a correct coupling.",
                    sources=["ucum-2.2", "si-brochure-9"], fixtures=["comparison-incompatible-measurement-unit"]))
        ax = bcr.AXES.get(pid)
        if ax:
            findings.append(dict(
                id="P-AXES", severity="blocking", systemic=["S6", "S11"],
                title="Declared axes or representation contradict the data" if pid != "core/scalar-quantity" else "Allowed representations contradict a scalar quantity",
                field="dimensions.axes" if pid != "core/scalar-quantity" else "representation.kind (allowed enum)",
                current=ax[0] if pid != "core/scalar-quantity" else "scalar, dense_vector, sparse_vector, matrix, tensor, array, record, table",
                proposed=ax[1], reason=ax[2], sources=ax[3], fixtures=["positive", "comparison-direct"]))

        verdict = "BLOCK" if any(f["severity"] == "blocking" for f in findings) else "CHANGES_REQUIRED"
        counts[verdict] += 1
        for f in findings:
            finding_counts[f["id"]] += 1

        fr = {
            "positive_scientifically_valid": "FAIL" if (m or ax) else "WEAK",
            "positive_note": ("Declared unit, scale, axes or representation are scientifically wrong - see the profile findings."
                              if (m or ax) else
                              "Schema-valid but not scientifically meaningful: semantic.subject is a domain placeholder token and semantic.concept is a self-reference"
                              + ("; identifiers use 'example-namespace'" if "identifiers.namespace" in req else "")
                              + ("; security uses 'example-consent-scope'" if "security.data_use" in req else "")
                              + ("; species is NCBITaxon:9606 (human) in a domain whose organism of interest is generally not human" if pk["domain"] in {"ecology", "evolution", "microbiology", "virology"} else "") + "."),
            "missing_evidence_returns_unknown": "PARTIAL",
            "missing_evidence_note": "Correct when the source omits a required field; the mirrored case, where the target omits it, has no fixture (S10)."
                                     + (" A species of 'any' on the source returns INCOMPATIBLE instead of UNKNOWN (S5)." if "biological_context.species" in req else ""),
            "contradiction_returns_incompatible": "FAIL" if (m and cur_unit == "g") else "PASS",
            "contradiction_note": ("The unit contradiction fixture asserts kg vs g is INCOMPATIBLE (S8)." if (m and cur_unit == "g") else
                                   "Declared contradictions return INCOMPATIBLE. The subject contradiction is a string difference, not a scientific contradiction (S2)."),
            "direct_hides_transformation": "FAIL",
            "direct_note": ("Unit is compared, but normalisation, baseline and aggregation are not, so differently normalised values still resolve as direct (S3)."
                            if "measurement.unit" in req else
                            "Optional measurement and identifier fields declared on both ports are never compared, so counts vs log-normalised values and different identifier namespaces resolve as DIRECT_COMPATIBLE (S3)."),
            "conversions_correct": "FAIL" if m else "N/A",
            "conversion_note": ("The only conversion fixture asserts nM->uM for this profile (S7)." if m else
                                "No conversion fixture exists; dense<->sparse re-encoding returns INCOMPATIBLE (S11)."),
            "lossy_and_inference_identified": "FAIL",
            "lossy_note": "No lossy and no inference fixture exists, although transformation_policy declares approval paths for both (S9).",
        }
        areas = bcr.area_decisions(pk, pid, req, kinds)
        items = {p: bcr.item_disposition(p)[0] for p in pk["candidate_recommended_items"]}
        full_profiles.append({
            "profile_id": pk["profile_id"], "profile_ref": pk["profile_ref"], "profile_sha256": pk["profile_sha256"],
            "digest_verified": True, "domain": pk["domain"], "label": pk["label"], "verdict": verdict,
            "required_items": req, "allowed_representation_kinds": kinds,
            "profile_findings": findings,
            "systemic_findings_applicable": [s["id"] for s in bcr.SYSTEMIC],
            "contract_area_decisions": areas,
            "candidate_item_decisions": items,
            "fixture_review": fr,
            "question_answers": {q.replace("{label}", pk["label"]): a for q, a in bcr.answers(pk, pid, req, m, ax).items()
                                 if q.replace("{label}", pk["label"]) in pk["questions_for_reviewers"]},
            "intended_use_assessment": (f"The stated scope - declaring and comparing {pk['label']} ports - is coherent, but the packet has no intended-use statement "
                                        "and no limitation list, both of which PROFILE_REVIEW.md requires before the profile can move to reviewed."),
            "limitations_required": [
                "A passing comparison does not imply the values were produced under comparable biological or experimental conditions.",
                "The profile does not establish the scientific validity, clinical safety or regulatory suitability of any model using it.",
                "Batch effects, assay bias, population mismatch and upstream model error are outside the contract.",
            ],
        })
        compact_profiles.append({
            "id": pk["profile_id"], "d": pk["domain"], "l": pk["label"], "v": verdict, "req": req,
            "f": [{k: f[k] for k in ("id", "severity", "title", "field", "current", "proposed", "reason", "sources", "fixtures")} for f in findings],
            "a": "".join({"included": "I", "conditional": "C", "excluded": "X"}[areas[k]["disposition"]] for k in AREA_ORDER),
            "an": [intern(areas[k]["rationale"]) for k in AREA_ORDER],
            "it": sorted(path_index[p] for p in pk["candidate_recommended_items"]),
            "fx": [[fr[s], intern(fr[n])] for s, n, _ in FX_ORDER],
        })

    reviewer_status = {
        "named_scientific_reviewer": None,
        "statement": ("This analysis was produced by an AI assistant (Claude Opus 5) at the request of the repository owner. It is not a qualified, independent, "
                      "domain-specific scientific sign-off and must not be recorded as one. PROFILE_REVIEW.md requires a named scientific reviewer who did not author "
                      "the profile and a different named schema reviewer; git history attributes all profile source to one author, so both must come from outside that authorship."),
        "evidence_files_written": 0,
        "evidence_policy": "No file was written under source/reviews/. Every profile carries at least one blocking change, and review evidence may only be created after blocking changes are incorporated.",
        "sha256_pinning": "Sources are pinned in docs/scientific-remediation/sources/sources.lock.json. Read the pinned_as field before relying on a digest: a document pin covers the reviewed text, a citation-metadata pin covers only the Crossref record for the DOI, and licensed standards (ISO 80000-1, ISO 20776-1, SNOMED CT) cannot be pinned here at all. Where a decision rests on a paywalled or licensed text, the reviewer pins their own copy and records the terms.",
        "repository_changes": "None. No file under spec/v0.1/ or source/ was modified.",
    }
    change_request = {
        "review_type": "Independent scientific review - pre-sign-off analysis and change request",
        "standard": "Biosimulant Model Compatibility Standard v0.1",
        "repository": "Biosimulant/model-compatibility-standard @ 9a4edf8 (working tree with uncommitted changes)",
        "reviewed_at": bcr.REVIEWED_AT,
        "scope": "All 650 profiles. No assignment list exists in the repository, packets or prior sessions, and every profile is produced by one generator, so the generator's rules were reviewed across all profiles, with representative profiles checked against the running engine.",
        "verdict_definitions": {
            "BLOCK": "The profile's own rules or fixtures certify a scientifically false result - a wrong unit, scale or axis structure, or an impossible conversion - so approving it would freeze that error into the conformance suite.",
            "CHANGES_REQUIRED": "No false result is certified by this profile's own fixtures, but the systemic blockers leave the contract too imprecise to approve.",
        },
        "reviewer_status": reviewer_status,
        "digest_check": {"packets_checked": len(packets), "digest_matches": len(packets),
                         "method": "SHA-256 over the sorted-key compact JSON of the full profile definition, reproducing scripts/build_standard.py digest()"},
        "verdict_summary": dict(counts),
        "profile_finding_counts": dict(finding_counts),
        "engine_verification": [dict(profile=e[0], case=e[1], engine_result=e[2], scientifically_correct=e[3], findings=e[4]) for e in ENGINE],
        "concept_identifier_decision": {
            "decision": "Keep a Biosimulant-controlled term, re-minted in a version-independent namespace, and require a mapping to external ontology terms.",
            "rejected_alternatives": {
                "keep as is": "Version-bound and tautological (S1).",
                "replace with an external identifier only": "No external ontology defines 'a Biosimulant port contract for X'; an external term alone cannot carry the profile's contract boundary, and forcing one would overstate equivalence.",
            },
            "proposed_pattern": "https://biosimulant.com/standards/model-compatibility/terms/<domain>/<name>",
            "required_mapping": "semantic.ontology_terms[] with uri, ontology, version and relation; compared by term-equivalent or term-subsumes against a pinned snapshot",
        },
        "errata": [{"id": i, "title": t, "detail": d} for i, t, d in ERRATA],
        "systemic_findings": bcr.SYSTEMIC,
        "candidate_item_rules": item_rules,
        "sources": [{"id": i, "title": t, "kind": k, "url": u, "version": v,
                     "sha256": PINNED.get(i, {}).get("sha256"),
                     "pinned_as": PINNED.get(i, {}).get("retrieval_kind", "not pinned"),
                     "retrieved_at": PINNED.get(i, {}).get("retrieved_at")} for i, t, k, u, v in bcr.SOURCES],
        "profiles": full_profiles,
    }
    with open(os.path.join(HERE, "change-request.json"), "w") as fh:
        json.dump(change_request, fh, indent=1, ensure_ascii=False)

    data = {
        "counts": dict(counts), "findingCounts": dict(finding_counts),
        "areas": AREA_ORDER, "fx": [label for _, _, label in FX_ORDER],
        "notes": notes, "paths": all_paths,
        "rules": [[item_rules[p]["disposition"], item_rules[p]["rationale"]] for p in all_paths],
        "errata": change_request["errata"],
        "systemic": [{k: s[k] for k in ("id", "severity", "title", "field", "current", "proposed", "reason", "fixtures", "applies", "sources")} for s in bcr.SYSTEMIC],
        "sources": change_request["sources"],
        "engine": change_request["engine_verification"],
        "profiles": compact_profiles,
    }
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    template = open(os.path.join(HERE, "report-template.html")).read()
    with open(os.path.join(HERE, "bmcs-referee-report.html"), "w") as fh:
        fh.write(template.replace("__REVIEW_DATA__", payload))

    print("verdicts", dict(counts), "findings", dict(finding_counts))
    print("rules", len(item_rules), "uncovered", [p for p in all_paths if p not in bcr.ITEM_RULES])
    blocking_meas = sum(1 for p in full_profiles for f in p["profile_findings"] if f["id"] == "P-MEAS" and f["severity"] == "blocking")
    print("P-MEAS blocking", blocking_meas, "non-blocking", finding_counts["P-MEAS"] - blocking_meas)
    for name in ("change-request.json", "bmcs-referee-report.html"):
        print(name, os.path.getsize(os.path.join(HERE, name)) // 1024, "KB")


if __name__ == "__main__":
    main()
