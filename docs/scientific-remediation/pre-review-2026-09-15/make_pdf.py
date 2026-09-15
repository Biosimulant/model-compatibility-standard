"""Render the BMCS v0.1 referee report as a print PDF from change-request.json."""
from __future__ import annotations

import collections
import json
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.flowables import HRFlowable
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CR = json.load(open(os.path.join(HERE, "change-request.json")))
OUT = os.path.join(HERE, "BMCS-v0.1-Referee-Report.pdf")

# ------------------------------------------------------------------ fonts ----
SUP = "/System/Library/Fonts/Supplemental/"
for name, file in [("Body", "Georgia.ttf"), ("Body-Bold", "Georgia Bold.ttf"), ("Body-Italic", "Georgia Italic.ttf"),
                   ("Body-BoldItalic", "Georgia Bold Italic.ttf"), ("Display", "Arial Narrow.ttf"),
                   ("Display-Bold", "Arial Narrow Bold.ttf"), ("Mono", "Courier New.ttf"), ("Mono-Bold", "Courier New Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, SUP + file))
addMapping("Body", 0, 0, "Body"); addMapping("Body", 1, 0, "Body-Bold")
addMapping("Body", 0, 1, "Body-Italic"); addMapping("Body", 1, 1, "Body-BoldItalic")
addMapping("Display", 0, 0, "Display"); addMapping("Display", 1, 0, "Display-Bold")
addMapping("Display", 0, 1, "Display"); addMapping("Display", 1, 1, "Display-Bold")
addMapping("Mono", 0, 0, "Mono"); addMapping("Mono", 1, 0, "Mono-Bold")
addMapping("Mono", 0, 1, "Mono"); addMapping("Mono", 1, 1, "Mono-Bold")

# ----------------------------------------------------------------- colour ----
HEX = dict(ink="#17201B", muted="#55615A", faint="#7C8781", rule="#D6DCD4", rule_strong="#AEB8AC",
           accent="#2946B8", accent_soft="#E2E7F7", block="#B42318", block_soft="#FBE6E3",
           change="#8A5000", change_soft="#F7ECD6", pass_="#1B6E42", pass_soft="#DFF0E5",
           neutral_soft="#E6EAE4", code="#EEF1EC", paper="#FBFCFA")
C = {k: colors.HexColor(v) for k, v in HEX.items()}

PAGE_W, PAGE_H = A4
LM = RM = 20 * mm
FRAME_W = PAGE_W - LM - RM

# ----------------------------------------------------------------- styles ----
def style(name, font="Body", size=9.6, leading=None, color="ink", **kw):
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading or size * 1.45,
                          textColor=C[color], **kw)

S = {
    "eyebrow": style("eyebrow", "Display-Bold", 8.2, 11, "muted", spaceAfter=3),
    "h1": style("h1", "Display-Bold", 33, 34, "ink", spaceAfter=10),
    "h2": style("h2", "Display-Bold", 21, 24, "ink", spaceAfter=8),
    "h2plain": style("h2plain", "Display-Bold", 21, 24, "ink", spaceAfter=8),
    "h3": style("h3", "Display-Bold", 12.8, 15.5, "ink", spaceAfter=2),
    "h3toc": style("h3toc", "Display-Bold", 12.8, 15.5, "ink", spaceAfter=2),
    "domain": style("domain", "Display-Bold", 15, 18, "ink", spaceBefore=4, spaceAfter=6),
    "lede": style("lede", "Body", 12.2, 17.6, "ink", spaceAfter=8),
    "body": style("body", "Body", 9.6, 14, "ink", spaceAfter=7),
    "muted": style("muted", "Body", 8.6, 12.2, "muted"),
    "small": style("small", "Body", 8.2, 11.4, "ink"),
    "cell": style("cell", "Body", 8.1, 11.2, "ink"),
    "cellmuted": style("cellmuted", "Body", 7.8, 10.8, "muted"),
    "cellmono": style("cellmono", "Mono", 7.3, 9.4, "ink"),
    "cellmonob": style("cellmonob", "Mono-Bold", 6.6, 8.8, "block"),
    "cellnarrow": style("cellnarrow", "Display", 8, 10, "ink"),
    "cellpass": style("cellpass", "Display-Bold", 8, 10.2, "pass_"),
    "dt": style("dt", "Display-Bold", 7.6, 10.6, "muted"),
    "th": style("th", "Display-Bold", 7.6, 9.6, "muted"),
    "bigdecision": style("bigdecision", "Display-Bold", 15.5, 19, "ink", spaceAfter=6),
    "num": style("num", "Display-Bold", 26, 27, "ink"),
    "numlabel": style("numlabel", "Display-Bold", 7.4, 9, "muted"),
    "iri": style("iri", "Mono", 7.6, 10, "ink"),
    "iriold": style("iriold", "Mono", 7.6, 10, "muted"),
    "toc0": style("toc0", "Display", 11, 17, "ink"),
}


def esc(text):
    return escape(str(text if text is not None else ""))


def chip(text, fg, bg, size=6.8):
    return f'<font name="Mono-Bold" size="{size}" color="{HEX[fg]}" backColor="{HEX[bg]}">&nbsp;{esc(text)}&nbsp;</font>'


VERDICT_CHIP = {"BLOCK": ("block", "block_soft"), "CHANGES_REQUIRED": ("change", "change_soft")}
DISP_CHIP = {"included": ("accent", "accent_soft"), "conditional": ("change", "change_soft"), "excluded": ("muted", "neutral_soft"),
             "required": ("block", "block_soft"), "recommended": ("pass_", "pass_soft"), "optional": ("muted", "neutral_soft")}
SEV_CHIP = {"blocking": ("block", "block_soft"), "non-blocking": ("change", "change_soft")}
AREA_ORDER = ["structure", "semantic", "representation", "dimensions", "identifiers", "measurement",
              "biological_context", "lifecycle", "origin", "uncertainty", "artifact", "constraints", "security"]
AREA_LABEL = {
    "structure": "Structure", "semantic": "Scientific meaning", "representation": "Representation",
    "dimensions": "Dimensions and feature order", "identifiers": "Identifiers and versions",
    "measurement": "Quantity, unit, scale, normalisation, endpoint", "biological_context": "Biological and experimental context",
    "lifecycle": "Time and lifecycle meaning", "origin": "Origin and provenance", "uncertainty": "Uncertainty and missingness",
    "artifact": "Artifact format", "constraints": "Cross-field constraints", "security": "Security, consent, licensing, data use",
}
FX_KEYS = [("positive_scientifically_valid", "Positive example is scientifically valid"),
           ("missing_evidence_returns_unknown", "Missing evidence returns UNKNOWN"),
           ("contradiction_returns_incompatible", "Known contradiction returns INCOMPATIBLE"),
           ("direct_hides_transformation", "Direct compatibility hides no transformation"),
           ("conversions_correct", "Unit and representation conversions are correct"),
           ("lossy_and_inference_identified", "Lossy conversion and inference are identified")]
FX_CODE = {"PASS": "P", "PARTIAL": "~", "WEAK": "W", "FAIL": "F", "N/A": "-"}


# ------------------------------------------------------------ doc template ----
class ReportDoc(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(filename, pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=22 * mm, bottomMargin=20 * mm,
                         title="BMCS v0.1 Referee Report",
                         author="Claude Opus 5 (AI-assisted pre-sign-off analysis)",
                         subject="Independent scientific review of the Biosimulant Model Compatibility Standard v0.1 profiles",
                         creator="Biosimulant model-compatibility-standard review")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="cover", frames=[frame], onPage=draw_cover),
                               PageTemplate(id="body", frames=[frame], onPage=draw_body)])
        self._seq = 0
        self._has_level0 = False

    def beforeDocument(self):
        # multiBuild lays the story out several times; keys must repeat exactly for the contents to resolve
        self._seq = 0
        self._has_level0 = False

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        name = flowable.style.name
        if name in ("h2", "h3toc", "domain"):
            self._seq += 1
            key = f"bm{self._seq}"
            text = flowable.getPlainText()
            self.canv.bookmarkPage(key)
            if name == "h2":
                self.canv.addOutlineEntry(text, key, level=0, closed=True)
                self._has_level0 = True
                self.notify("TOCEntry", (0, text, self.page, key))
            elif self._has_level0:
                self.canv.addOutlineEntry(text, key, level=1, closed=True)


def draw_footer(canvas, doc):
    canvas.setFont("Body-Italic", 7.4)
    canvas.setFillColor(C["muted"])
    canvas.drawString(LM, 11 * mm, "Pre-sign-off analysis and change request. Not a named domain-qualified reviewer's approval.")
    canvas.setFont("Display-Bold", 8)
    canvas.drawRightString(PAGE_W - RM, 11 * mm, str(doc.page))


def draw_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C["ink"])
    canvas.rect(0, PAGE_H - 7 * mm, PAGE_W, 7 * mm, stroke=0, fill=1)
    draw_footer(canvas, doc)
    canvas.restoreState()


def draw_body(canvas, doc):
    canvas.saveState()
    canvas.setFont("Display-Bold", 7.6)
    canvas.setFillColor(C["muted"])
    canvas.drawString(LM, PAGE_H - 12.5 * mm, "BMCS V0.1 REFEREE REPORT")
    canvas.drawRightString(PAGE_W - RM, PAGE_H - 12.5 * mm, "INDEPENDENT SCIENTIFIC REVIEW  ·  15 SEPTEMBER 2026")
    canvas.setStrokeColor(C["rule"])
    canvas.setLineWidth(0.5)
    canvas.line(LM, PAGE_H - 14.5 * mm, PAGE_W - RM, PAGE_H - 14.5 * mm)
    draw_footer(canvas, doc)
    canvas.restoreState()


# --------------------------------------------------------------- helpers ----
def section(story, eyebrow, title, intro=(), new_page=True):
    if new_page:
        story.append(PageBreak())
    else:
        story.append(CondPageBreak(70 * mm))
        story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(esc(eyebrow.upper()), S["eyebrow"]))
    story.append(Paragraph(esc(title), S["h2"]))
    for para in intro:
        story.append(Paragraph(para, S["body"]))


def dl(rows, label_w=23 * mm, width=FRAME_W, proposed_row=None):
    data = [[Paragraph(esc(k.upper()), S["dt"]), v] for k, v in rows]
    t = Table(data, colWidths=[label_w, width - label_w], splitByRow=1)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if proposed_row is not None:
        st += [("LINEBEFORE", (1, proposed_row), (1, proposed_row), 1.8, C["pass_"]),
               ("LEFTPADDING", (1, proposed_row), (1, proposed_row), 7)]
    t.setStyle(TableStyle(st))
    return t


def grid(data, widths, header_rows=1, zebra=False, extra=()):
    t = Table(data, colWidths=widths, repeatRows=header_rows, splitByRow=1)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LINEBELOW", (0, 0), (-1, header_rows - 1), 0.8, C["rule_strong"]),
          ("LINEBELOW", (0, header_rows), (-1, -1), 0.3, C["rule"])]
    st.extend(extra)
    t.setStyle(TableStyle(st))
    return t


def src_ids(ids):
    return "  ".join(f'<font name="Mono" size="7" color="{HEX["accent"]}">{esc(i)}</font>' for i in ids)


# ----------------------------------------------------------------- story ----
def build():
    profiles = CR["profiles"]
    counts = CR["verdict_summary"]
    total = len(profiles)
    story = []

    # cover
    story.append(Spacer(1, 16 * mm))
    story.append(Paragraph("BIOSIMULANT MODEL COMPATIBILITY STANDARD  ·  V0.1  ·  SCIENTIFIC REVIEW  ·  15 SEPTEMBER 2026", S["eyebrow"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("None of the 650 profiles can be approved as published", S["h1"]))
    story.append(Paragraph("The verdict split below is withdrawn as a verdict and kept only as an index of which profiles show "
                           "which symptom; see Corrections.", S["muted"]))
    story.append(Paragraph("Every profile passes its tests in both implementations, and every packet digest matches its profile. "
                           "The tests prove the rules run. They do not prove the rules are right, and running the engine on real "
                           "scientific cases shows several rules returning the wrong answer in both directions.", S["lede"]))
    story.append(Spacer(1, 5 * mm))

    b, ch = counts.get("BLOCK", 0), counts.get("CHANGES_REQUIRED", 0)
    bar = Table([["", ""]], colWidths=[FRAME_W * b / total, FRAME_W * ch / total], rowHeights=[5.5 * mm])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), C["block"]), ("BACKGROUND", (1, 0), (1, 0), C["change"]),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(bar)
    story.append(Spacer(1, 3 * mm))
    legend_cells = []
    for label, n, col in [("BLOCK", b, "block"), ("CHANGES_REQUIRED", ch, "change"),
                          ("APPROVE_WITH_NON_BLOCKING_COMMENTS", 0, "rule_strong"), ("APPROVE", 0, "rule_strong")]:
        legend_cells.append([Paragraph(str(n), S["num"]),
                             Paragraph(f'<font color="{HEX[col]}">■</font> {esc(label)}', S["numlabel"])])
    legend = Table([legend_cells], colWidths=[FRAME_W / 4] * 4)
    legend.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("LINEABOVE", (0, 0), (-1, 0), 0.5, C["rule"]), ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    story.append(legend)
    story.append(Spacer(1, 9 * mm))

    rs = CR["reviewer_status"]
    status_rows = [
        ("What this is", "An independent pre-sign-off analysis and change request, produced by an AI assistant (Claude Opus 5) at the repository "
                         "owner's request. It is <b>not</b> the named, domain-qualified scientific sign-off that PROFILE_REVIEW.md requires, and "
                         "must not be recorded as one. Git history attributes all profile source to one author, so the named scientific and "
                         "schema reviewers must both come from outside that authorship."),
        ("Scope", esc(CR["scope"])),
        ("Repository", esc(CR["repository"])),
        ("Evidence files", esc(rs["evidence_policy"]) + " " + esc(rs["repository_changes"])),
        ("Digests", f'{CR["digest_check"]["digest_matches"]} of {CR["digest_check"]["packets_checked"]} packet profile_sha256 values reproduce from the profile definitions.'),
        ("Source pinning", esc(rs["sha256_pinning"])),
    ]
    st_data = [[Paragraph("STATUS OF THIS REVIEW", S["eyebrow"]), ""]] + [[Paragraph(esc(k), S["h3"]), Paragraph(v, S["small"])] for k, v in status_rows]
    status = Table(st_data, colWidths=[30 * mm, FRAME_W - 30 * mm])
    status.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("BOX", (0, 0), (-1, -1), 0.8, C["rule_strong"]),
                                ("BACKGROUND", (0, 0), (-1, -1), C["paper"]), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 9)]))
    story.append(status)

    # contents
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())
    story.append(Paragraph("CONTENTS", S["eyebrow"]))
    story.append(Paragraph("Contents", S["h2plain"]))
    toc = TableOfContents()
    toc.levelStyles = [S["toc0"]]
    toc.dotsMinLevel = 0
    story.append(toc)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("<b>Companion data.</b> The per-profile contract-area rationales, the full item-by-item decision lists and the answers to "
                           "every reviewer question in every packet are recorded in change-request.json, which accompanies this report. "
                           "This PDF carries every decision rule, every profile's verdict and audit results, and every profile-specific finding in full.", S["muted"]))

    # corrections
    section(story, "Read the report with these corrections", "Corrections",
            ["Raised in review of this report and accepted. The report stands as a fault report; these parts do not. "
             "Each correction opens a design decision, tracked in the remediation plan."])
    for item in CR.get("errata", []):
        story.append(KeepTogether([
            Spacer(1, 1.5 * mm),
            Paragraph(f'<font name="Mono-Bold" size="9.5" color="{HEX["change"]}">{esc(item["id"])}</font>&nbsp;&nbsp;&nbsp;{esc(item["title"])}', S["h3"]),
            Paragraph(esc(item["detail"]), S["body"]),
        ]))
    story.append(Spacer(1, 4 * mm))

    # engine evidence
    section(story, "What the passing tests leave out", "The engine, run on cases a scientist would try",
            ["Each row was executed against <font name=\"Mono\" size=\"8.4\">compare_contracts</font> or "
             "<font name=\"Mono\" size=\"8.4\">validate_contract</font> in the Python reference implementation. "
             "The engine result is what the standard returns today; the correct outcome is what the science requires."])
    rows = [[Paragraph(h, S["th"]) for h in ("PROFILE", "CASE", "ENGINE RETURNS", "CORRECT OUTCOME", "FINDING")]]
    for e in CR["engine_verification"]:
        rows.append([Paragraph(esc(e["profile"]).replace("/", "/<br/>", 1), S["cellnarrow"]), Paragraph(esc(e["case"]), S["cell"]),
                     Paragraph(esc(e["engine_result"]), S["cellmonob"]), Paragraph(esc(e["scientifically_correct"]).replace("LOSSLESS_CONVERSION_AVAILABLE", "LOSSLESS_CONVERSION_<br/>AVAILABLE"), S["cellpass"]),
                     Paragraph(esc(e["findings"]), S["cellmono"])])
    story.append(grid(rows, [33 * mm, 46 * mm, 43 * mm, 36 * mm, 12 * mm]))

    # concept decision
    section(story, "Decision requested on the provisional identifier", "What to do with the #concept identifier", new_page=False)
    cd = CR["concept_identifier_decision"]
    story.append(Paragraph(esc(cd["decision"]), S["bigdecision"]))
    iri = Table([[Paragraph("TODAY", S["dt"]), Paragraph("<strike>https://biosimulant.com/standards/model-compatibility/profiles/neuroscience/firing-rate/<b>v0.1#concept</b></strike>", S["iriold"])],
                 [Paragraph("PROPOSED", S["dt"]), Paragraph("https://biosimulant.com/standards/model-compatibility/<b>terms</b>/neuroscience/firing-rate", S["iri"])],
                 [Paragraph("MAPPING", S["dt"]), Paragraph("semantic.ontology_terms[]: { uri, ontology, version, relation: exact-match | broad-match | narrow-match }", S["iri"])]],
                colWidths=[23 * mm, FRAME_W - 23 * mm])
    iri.setStyle(TableStyle([("BACKGROUND", (1, 0), (1, -1), C["code"]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("LEFTPADDING", (0, 0), (0, -1), 0), ("LEFTPADDING", (1, 0), (1, -1), 7),
                             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                             ("LINEBELOW", (1, 0), (1, 1), 0.8, colors.white)]))
    story.append(iri)
    story.append(Spacer(1, 5 * mm))
    options = [
        (chip("REJECT", "block", "block_soft"), "<b>Keep as is.</b> The equal rule is tautological, since validation already forces both contracts to hold the same "
         "constant. And because the IRI embeds /v0.1, every v0.1 port would be INCOMPATIBLE with a v0.2 port whose meaning is unchanged."),
        (chip("REJECT", "block", "block_soft"), "<b>External identifier only.</b> No ontology defines a Biosimulant contract for a given quantity. Forcing one "
         "would overstate equivalence and lose the contract boundary the profile exists to draw."),
        (chip("ADOPT", "pass_", "pass_soft"), "<b>Controlled term plus mapping.</b> The Biosimulant term keeps profile identity stable across versions; required "
         "ontology_terms, compared by subsumption against a pinned snapshot, carry the scientific meaning. With no snapshot the comparison returns UNKNOWN."),
    ]
    opt = Table([[Paragraph(c_, S["small"]), Paragraph(t_, S["small"])] for c_, t_ in options], colWidths=[23 * mm, FRAME_W - 23 * mm])
    opt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                             ("LINEBELOW", (0, 0), (-1, -2), 0.3, C["rule"])]))
    story.append(opt)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Sources: " + src_ids(["obo-fp-003", "w3c-cooluris", "bioregistry-2022", "obi-2016"]), S["small"]))

    # systemic findings
    section(story, "Apply to the generator, so they apply to every profile it emits", "Systemic findings",
            ["Each finding gives the exact field, its current definition, the proposed definition, the reason, the supporting sources and "
             "the fixtures that must change. All changes belong in source/catalogue.review.json or scripts/build_standard.py, followed by "
             "regeneration; nothing under spec/v0.1/ should be edited by hand."])
    for s in CR["systemic_findings"]:
        fg, bg = SEV_CHIP[s["severity"]]
        head = [Spacer(1, 2 * mm),
                Paragraph(f'<font name="Mono-Bold" size="10" color="{HEX["accent"]}">{s["id"]}</font>&nbsp;&nbsp;&nbsp;{chip(s["severity"].upper(), fg, bg)}', S["small"]),
                Paragraph(f'{s["id"]}. {esc(s["title"])}', S["h3toc"]),
                Paragraph("Applies to " + esc(s["applies"]), S["muted"]), Spacer(1, 2 * mm)]
        body = dl([
            ("Field", Paragraph(esc(s["field"]), S["cellmono"])),
            ("Current", Paragraph(esc(s["current"]), S["cell"])),
            ("Proposed", Paragraph(esc(s["proposed"]), S["cell"])),
            ("Reason", Paragraph(esc(s["reason"]), S["cell"])),
            ("Fixtures", Paragraph(esc(s["fixtures"]), S["cell"])),
            ("Sources", Paragraph(src_ids(s["sources"]), S["cell"])),
        ], proposed_row=2)
        story.append(KeepTogether(head + [body]) if len(s["current"]) + len(s["proposed"]) + len(s["reason"]) < 1400 else KeepTogether(head))
        if len(s["current"]) + len(s["proposed"]) + len(s["reason"]) >= 1400:
            story.append(body)
        story.append(HRFlowable(width="100%", thickness=0.5, color=C["rule"], spaceBefore=5, spaceAfter=3))

    # profile-specific findings
    block_profiles = [p for p in profiles if p["profile_findings"]]
    fc = CR["profile_finding_counts"]
    section(story, "Findings that belong to individual profiles", "Profile-specific findings",
            [f"{len(block_profiles)} profiles carry at least one finding of their own, and every one of them is BLOCK: "
             f"P-MEAS (unit or scale, {fc.get('P-MEAS', 0)}), P-CONV (conversion fixture, {fc.get('P-CONV', 0)}), "
             f"P-KG (g vs kg fixture, {fc.get('P-KG', 0)}) and P-AXES (axes or representation, {fc.get('P-AXES', 0)}). "
             "A non-blocking P-MEAS means the declared unit and scale are acceptable but under-specified; the profile is still blocked by its conversion fixture. "
             "The remaining profiles have no finding of their own and are CHANGES_REQUIRED because of the systemic blockers.",
             "<b>P-CONV</b> is shown as current and proposed only, because its reason is the same everywhere: the fixture certifies a nanomolar-to-micromolar "
             "conversion regardless of the quantity the profile measures, and both implementations are tested to agree on it (S7). For the 14 molar-concentration "
             "profiles the conversion is dimensionally right, but the fixture pair inherits the wrong probability scale from the positive example. "
             "Fixture to change: comparison-lossless-unit-conversion. Sources: ucum-2.2, vim-jcgm-200-2012."])
    by_domain = collections.defaultdict(list)
    for p in block_profiles:
        by_domain[p["domain"]].append(p)
    for dom in sorted(by_domain):
        story.append(CondPageBreak(55 * mm))
        story.append(Paragraph(f'{esc(dom)} <font name="Display" size="10" color="{HEX["muted"]}">&nbsp;{len(by_domain[dom])} profiles</font>', S["domain"]))
        for p in by_domain[dom]:
            fg, bg = VERDICT_CHIP[p["verdict"]]
            header = Paragraph(f'<b>{esc(p["label"])}</b>&nbsp;&nbsp;<font name="Mono" size="7.6" color="{HEX["muted"]}">{esc(p["profile_id"])}</font>&nbsp;&nbsp;{chip(p["verdict"], fg, bg)}', style("ph", "Display-Bold", 10.6, 13.5))
            blocks = [Spacer(1, 1.5 * mm), header, Spacer(1, 1 * mm)]
            for i, f in enumerate(p["profile_findings"]):
                ffg, fbg = SEV_CHIP[f["severity"]]
                t = Paragraph(f'{chip(f["id"], ffg, fbg)}&nbsp;&nbsp;<b>{esc(f["title"])}</b>', S["small"])
                frows = [
                    ("Field", Paragraph(esc(f["field"]), S["cellmono"])),
                    ("Current", Paragraph(esc(f["current"]), S["cellmono"])),
                    ("Proposed", Paragraph(esc(f["proposed"]), S["cellmono"])),
                    ("Reason", Paragraph(esc(f["reason"]), S["cell"])),
                    ("Fixtures", Paragraph(esc(", ".join(f["fixtures"])), S["cellmono"])),
                    ("Sources", Paragraph(src_ids(f["sources"]), S["cell"])),
                ]
                if f["id"] == "P-CONV":
                    frows = [frows[1], frows[2]]
                d = dl(frows, label_w=21 * mm, width=FRAME_W - 5 * mm, proposed_row=1 if f["id"] == "P-CONV" else 2)
                wrapper = Table([[t], [d]], colWidths=[FRAME_W])
                wrapper.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                             ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                                             ("LINEBEFORE", (0, 0), (0, -1), 2, C["block"] if f["severity"] == "blocking" else C["change"])]))
                if i == 0:
                    story.append(KeepTogether(blocks + [wrapper]))
                else:
                    story.append(KeepTogether([Spacer(1, 1.5 * mm), wrapper]))
            story.append(HRFlowable(width="100%", thickness=0.3, color=C["rule"], spaceBefore=4, spaceAfter=1))

    # register
    section(story, "Every profile's verdict, audit and item decisions at a glance", "Verdict register: all 650 profiles",
            ["<b>Contract areas</b> read left to right in this order: " + "; ".join(f"{i + 1} {AREA_LABEL[a].lower()}" for i, a in enumerate(AREA_ORDER)) +
             ". Each letter is one area in that order: I = included, C = conditional, X = excluded.",
             "<b>Fixture audit</b> reads left to right: " + "; ".join(f"{i + 1} {label.lower()}" for i, (_, label) in enumerate(FX_KEYS)) +
             ". Each character is one check in that order: P = pass, ~ = partial, W = schema-valid but scientifically weak, F = fail, - = not applicable.",
             "<b>Items</b> counts the candidate items listed in the packet, as required / conditional / recommended / optional."])
    head = [Paragraph(h, S["th"]) for h in ("PROFILE", "VERDICT", "OWN FINDINGS", "CONTRACT AREAS", "FIXTURE AUDIT", "ITEMS R/C/Rec/O")]
    data = [head]
    extra = []
    by_dom_all = collections.defaultdict(list)
    for p in profiles:
        by_dom_all[p["domain"]].append(p)
    for dom in sorted(by_dom_all):
        extra += [("SPAN", (0, len(data)), (-1, len(data))), ("BACKGROUND", (0, len(data)), (-1, len(data)), C["neutral_soft"]),
                  ("LEFTPADDING", (0, len(data)), (0, len(data)), 4)]
        data.append([Paragraph(f'<b>{esc(dom)}</b>  <font color="{HEX["muted"]}">{len(by_dom_all[dom])} profiles</font>', style("dh", "Display-Bold", 8.8, 11)), "", "", "", "", ""])
        for p in by_dom_all[dom]:
            fg, bg = VERDICT_CHIP[p["verdict"]]
            areas = "".join({"included": "I", "conditional": "C", "excluded": "X"}[p["contract_area_decisions"][a]["disposition"]] for a in AREA_ORDER)
            fx = "".join(FX_CODE[p["fixture_review"][k]] for k, _ in FX_KEYS)
            ic = collections.Counter(p["candidate_item_decisions"].values())
            items = f'{ic.get("required", 0)}/{ic.get("conditional", 0)}/{ic.get("recommended", 0)}/{ic.get("optional", 0)}'
            own = " ".join(f["id"] for f in p["profile_findings"]) or "-"
            data.append([
                Paragraph(f'{esc(p["label"])}<br/><font name="Display" size="7.2" color="{HEX["muted"]}">{esc(p["profile_id"])}</font>', style("rp", "Body", 7.9, 10)),
                Paragraph(chip(p["verdict"].replace("CHANGES_REQUIRED", "CHANGES_REQD"), fg, bg, 6.2), S["cell"]),
                Paragraph(esc(own), S["cellmono"]),
                Paragraph(esc(areas), S["cellmono"]),
                Paragraph(esc(fx), S["cellmono"]),
                Paragraph(esc(items), S["cellmono"]),
            ])
    story.append(grid(data, [56 * mm, 25 * mm, 27 * mm, 24 * mm, 16 * mm, 22 * mm], extra=extra))

    # contract-area rules
    section(story, "How each contract area was decided, and for how many profiles", "Contract-area decisions",
            ["Every profile records one decision per contract area, with a reason. The decisions follow the rules below, so each rule is "
             "listed once with the number of profiles it applies to. An exclusion always carries its scientific reason."])
    for a in AREA_ORDER:
        tally = collections.Counter((p["contract_area_decisions"][a]["disposition"], p["contract_area_decisions"][a]["rationale"]) for p in profiles)
        rows = [[Paragraph(h, S["th"]) for h in ("DECISION", "PROFILES", "REASON")]]
        for (disp, why), n in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0][0])):
            fg, bg = DISP_CHIP[disp]
            rows.append([Paragraph(chip(disp.upper(), fg, bg), S["cell"]), Paragraph(str(n), style("n", "Display-Bold", 10, 12)), Paragraph(esc(why), S["cell"])])
        story.append(KeepTogether([Spacer(1, 2 * mm), Paragraph(esc(AREA_LABEL[a]), S["h3"]), Spacer(1, 1 * mm),
                                   grid(rows, [27 * mm, 17 * mm, FRAME_W - 44 * mm])]))

    # candidate item rules
    packet_counts = collections.Counter(path for p in profiles for path in p["candidate_item_decisions"])
    rules = CR["candidate_item_rules"]
    dist = collections.Counter(r["disposition"] for r in rules.values())
    section(story, "One decision per candidate item path, applied in every packet that lists it", "Candidate item decisions",
            [f"The packets list {len(rules)} distinct candidate items, 20 to 79 per profile. Decisions: "
             + ", ".join(f"{dist.get(k, 0)} {k}" for k in ("required", "conditional", "recommended", "optional", "excluded")) +
             ". Conditional names the condition under which an item becomes required. The Packets column counts how many of the 650 packets list the item."])
    families = collections.defaultdict(list)
    for path in sorted(rules):
        families[path.split(".")[0].split("[")[0]].append(path)
    for fam in sorted(families):
        rows = [[Paragraph(h, S["th"]) for h in ("ITEM", "DECISION", "PACKETS", "REASON")]]
        for path in families[fam]:
            r = rules[path]
            fg, bg = DISP_CHIP[r["disposition"]]
            rows.append([Paragraph(esc(path), S["cellmono"]), Paragraph(chip(r["disposition"].upper(), fg, bg), S["cell"]),
                         Paragraph(str(packet_counts[path]), S["cellmono"]), Paragraph(esc(r["rationale"]), S["cell"])])
        story.append(CondPageBreak(40 * mm))
        story.append(Paragraph(esc(fam), S["h3toc"]))
        story.append(Spacer(1, 1 * mm))
        story.append(grid(rows, [52 * mm, 26 * mm, 14 * mm, FRAME_W - 92 * mm]))
        story.append(Spacer(1, 4 * mm))

    # reviewer questions
    asked = collections.Counter()
    example = {}
    preferred = ["neuroscience/firing-rate@0.1", "imaging/ct-volume@0.1", "clinical/diagnosis-code@0.1",
                 "transcriptome/single-cell-expression-matrix@0.1", "neuroscience/spike-train@0.1"]
    ordered = sorted(profiles, key=lambda p: (preferred.index(p["profile_id"]) if p["profile_id"] in preferred else 99, p["profile_id"]))
    for p in ordered:
        for q, a in p["question_answers"].items():
            template = q.replace(p["label"], "{profile}")
            asked[template] += 1
            example.setdefault(template, (p["profile_id"], a))
    section(story, "Every question in questions_for_reviewers is answered for every packet that asks it", "Reviewer questions",
            ["The packets use 13 question templates. Each is shown with the number of packets that ask it and the answer recorded for one "
             "representative profile. The answer text for every packet is in change-request.json, where it is specialised to the profile's "
             "own fields, units, axes and findings."])
    for template, n in sorted(asked.items(), key=lambda kv: -kv[1]):
        pid, ans = example[template]
        story.append(KeepTogether([
            Spacer(1, 1.5 * mm),
            Paragraph(esc(template), S["h3"]),
            Paragraph(f"Asked in {n} packets. Example answer for <font name=\"Mono\" size=\"7.8\">{esc(pid)}</font>:", S["muted"]),
            Spacer(1, 1 * mm),
            Paragraph(esc(ans), S["body"]),
            HRFlowable(width="100%", thickness=0.3, color=C["rule"], spaceBefore=2, spaceAfter=2),
        ]))

    # sources
    section(story, "Formal standards, maintained ontologies, databases, guidance and primary publications", "Sources",
            ["Pinned by scripts/pin_sources.py and recorded in sources/sources.lock.json. Read the pinning column before relying on a digest: "
             "document pins the reviewed text, citation metadata pins only the Crossref record for the DOI, and licensed standards (ISO 80000-1, ISO 20776-1, SNOMED CT) cannot be pinned here at all. Where a decision rests on a paywalled or licensed text, the reviewer pins their own copy."])
    rows = [[Paragraph(h, S["th"]) for h in ("ID", "TITLE AND LOCATION", "VERSION", "SHA-256")]]
    for s in CR["sources"]:
        rows.append([Paragraph(esc(s["id"]), S["cellmono"]),
                     Paragraph(f'{esc(s["title"])}<br/><font name="Display-Bold" size="6.8" color="{HEX["muted"]}">{esc(s["kind"].replace("-", " ").upper())}</font>'
                               f'<br/><link href="{esc(s["url"])}"><font name="Mono" size="6.8" color="{HEX["accent"]}">{esc(s["url"])}</font></link>', S["cell"]),
                     Paragraph(esc(s["version"]), S["cellmuted"]),
                     Paragraph((esc(s["sha256"][:23]) + "&#8230;<br/>" + esc(str(s.get("pinned_as", "")).replace("-", " "))) if s.get("sha256") else "not pinned", style("np", "Mono", 6.4, 8.4, "muted" if s.get("sha256") else "change"))])
    story.append(grid(rows, [30 * mm, 84 * mm, 38 * mm, 18 * mm]))
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.8, color=C["rule_strong"], spaceAfter=6))
    story.append(Paragraph("Approval of a profile would mean only that it gives a defensible and precise compatibility contract for its stated "
                           "intended use. It would not mean that any model using it is scientifically valid, clinically safe or suitable for regulatory use.", S["muted"]))

    doc = ReportDoc(OUT)
    doc.multiBuild(story)
    print("wrote", OUT, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    build()
