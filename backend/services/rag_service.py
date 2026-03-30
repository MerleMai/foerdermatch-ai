from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional
import re


# -----------------------------
# Models
# -----------------------------

@dataclass(frozen=True)
class SourceRef:
    doc_type: str
    filename: str
    page_ref: str
    document_id: int
    chunk_index: int
    distance: float


@dataclass(frozen=True)
class ChecklistItem:
    item: str
    criticality: str  # high | medium | low
    source_refs: list[SourceRef]


@dataclass(frozen=True)
class RiskItem:
    risk: str
    criticality: str  # high | medium | low
    source_refs: list[SourceRef]


@dataclass(frozen=True)
class GroundedDetail:
    program_id: str
    summary: str
    program_requirements: list[ChecklistItem]
    risks: list[RiskItem]
    sources: list[SourceRef]


# -----------------------------
# Helpers
# -----------------------------

_SENT_SPLIT = re.compile(r"(?<=[\.\!\?])\s+|[\n\r]+")
_BULLET_CHARS = ["•", "", "▪", "■", "◦", "‣", "·"]


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _clean_display_text(s: str) -> str:
    s = str(s or "")
    s = s.replace("\x00", " ")
    s = s.replace("\u00ad", "")
    s = s.replace("­", "")
    for ch in _BULLET_CHARS:
        s = s.replace(ch, " ")
    s = s.replace(" ,", ",").replace(" .", ".").replace(" ;", ";").replace(" :", ":")
    s = _norm_ws(s)
    s = s.strip(" -–—•▪■")
    return s


def _ensure_complete_sentence(s: str) -> str:
    s = _clean_display_text(s)
    if not s:
        return ""
    if s.endswith("…") or s.endswith("..."):
        return ""
    if s[-1] not in ".!?":
        s += "."
    return s


def _extract_source_ref(item: dict[str, Any]) -> Optional[SourceRef]:
    md = item.get("metadata") or {}
    try:
        return SourceRef(
            doc_type=str(md.get("doc_type") or ""),
            filename=str(md.get("filename") or ""),
            page_ref=str(md.get("page_ref") or ""),
            document_id=int(md.get("document_id") or 0),
            chunk_index=int(md.get("chunk_index") or 0),
            distance=float(item.get("distance") or 0.0),
        )
    except Exception:
        return None


def _dedupe_sources(sources: Iterable[SourceRef]) -> list[SourceRef]:
    seen: set[tuple] = set()
    out: list[SourceRef] = []
    for s in sources:
        key = (s.document_id, s.chunk_index, s.doc_type, s.page_ref, s.filename)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    out.sort(key=lambda x: x.distance)
    return out


def _sentences_from_chunk(text: str) -> list[str]:
    raw = _SENT_SPLIT.split(text or "")
    sents: list[str] = []
    for r in raw:
        r = _clean_display_text(r)
        if len(r) < 25:
            continue
        if len(r) > 260:
            continue
        if r.endswith("…") or r.endswith("..."):
            continue
        r = _ensure_complete_sentence(r)
        if not r:
            continue
        sents.append(r)
    return sents


def _pick_best_sentences(retrieved: list[dict[str, Any]], n: int = 3) -> list[tuple[str, SourceRef]]:
    pairs: list[tuple[str, SourceRef]] = []
    for hit in retrieved:
        sref = _extract_source_ref(hit)
        if not sref:
            continue
        txt = str(hit.get("text") or "")
        for s in _sentences_from_chunk(txt):
            pairs.append((s, sref))
    pairs.sort(key=lambda p: p[1].distance)

    seen_s: set[str] = set()
    out: list[tuple[str, SourceRef]] = []
    for s, ref in pairs:
        key = s.lower()
        if key in seen_s:
            continue
        seen_s.add(key)
        out.append((s, ref))
        if len(out) >= n:
            break
    return out


def _criticality_from_text(t: str) -> str:
    tl = (t or "").lower()
    if any(k in tl for k in ["muss", "verpflicht", "erforder", "ausgeschlossen", "vor beginn", "vorhabensbeginn", "nur wenn"]):
        return "high"
    if any(k in tl for k in ["soll", "empfehl", "bestätig", "nachweis", "prüfen", "beachten"]):
        return "medium"
    return "low"


def _summary_prefix_for_program(program_id: str) -> list[str]:
    pid = (program_id or "").upper()

    if pid.startswith("KFW-ERP-DIGI-"):
        return [
            "- Förderart: zinsgünstiger ERP-Kredit für Digitalisierungsvorhaben",
            "- Zielgruppe: kleine und mittlere Unternehmen in Deutschland",
            "- Antragstellung: über Hausbank oder Finanzierungspartner",
            "- Besonderheit: Beihilfe- und Programmgrenzen können relevant sein",
        ]

    if pid == "ZIM":
        return [
            "- Förderart: Zuschuss für technologieorientierte FuE-Projekte",
            "- Zielgruppe: innovationsorientierte kleine und mittlere Unternehmen",
            "- Antragstellung: über den zuständigen Projektträger vor Projektbeginn",
            "- Besonderheit: Innovationshöhe und technisches Risiko müssen nachvollziehbar sein",
        ]

    if pid == "KMU-INNOVATIV":
        return [
            "- Förderart: Zuschuss für risikoreiche FuE-Vorhaben",
            "- Zielgruppe: forschungsaktive kleine und mittlere Unternehmen",
            "- Antragstellung: im Rahmen der vorgesehenen Einreichungsstichtage",
            "- Besonderheit: Das Vorhaben muss klar als anspruchsvolles FuE-Projekt eingeordnet werden",
        ]

    if pid.startswith("EEW-BAFA-"):
        return [
            "- Förderart: Zuschuss für Energie- und Effizienzmaßnahmen",
            "- Zielgruppe: Unternehmen mit investiven Energieeffizienzmaßnahmen",
            "- Antragstellung: vor Beginn der Maßnahme",
            "- Besonderheit: Technische Anforderungen und Einsparwirkungen müssen nachweisbar sein",
        ]

    if pid == "GO-INNO":
        return [
            "- Förderart: Zuschuss für externe Innovationsberatung",
            "- Zielgruppe: kleine und mittlere Unternehmen mit Innovationsvorhaben",
            "- Antragstellung: vor Beginn der Beratung",
            "- Besonderheit: Die Beratung muss durch ein passendes autorisiertes Unternehmen erfolgen",
        ]

    if pid == "GRW-MV-GEWERBE":
        return [
            "- Förderart: Zuschuss für gewerbliche Investitionen",
            "- Zielgruppe: Unternehmen mit Investitionsvorhaben im Fördergebiet",
            "- Antragstellung: vor Beginn der Investition",
            "- Besonderheit: Fördergebiet, Primäreffekt und Investitionswirkung sind zentral",
        ]

    return []

def _classify_summary_bucket(sentence: str) -> Optional[str]:
    tl = sentence.lower()

    if any(k in tl for k in ["darlehen", "kredit", "zuschuss", "haftungsfreistellung"]):
        return "förderart"
    if any(k in tl for k in ["kmu", "unternehmen", "kleine und mittlere", "mittelständische unternehmen", "zielgruppe"]):
        return "zielgruppe"
    if any(k in tl for k in ["förderfähig", "förderfaehig", "investitionen", "betriebsmittel", "maßnahmen", "beratung", "forschungs", "entwicklung"]):
        return "förderfähig"
    if any(k in tl for k in ["antrag", "hausbank", "finanzierungspartner", "projektträger", "vorhabensbeginn", "vor beginn", "einreichungsstichtage"]):
        return "antragstellung"
    if any(k in tl for k in ["de-minimis", "beihilfe", "technisches risiko", "innovationshöhe", "fördergebiet", "primäreffekt", "einsparwirkung"]):
        return "besonderheit"

    return None


def _normalize_summary_bullet(bucket: str, sentence: str) -> str:
    s = _clean_display_text(sentence).rstrip(".")

    if len(s) > 120:
        s = s[:120].rsplit(" ", 1)[0].strip()

    label_map = {
        "förderart": "Förderart",
        "zielgruppe": "Für wen geeignet",
        "förderfähig": "Was wird gefördert",
        "antragstellung": "Wichtige Voraussetzung",
        "besonderheit": "Worauf besonders zu achten ist",
    }

    label = label_map[bucket]

    if bucket == "antragstellung":
        s = f"Der Antrag muss gestellt werden, bevor das Projekt beginnt ({s})"
    elif bucket == "zielgruppe":
        s = f"Relevant für: {s}"
    elif bucket == "besonderheit":
        s = f"Besonders wichtig: {s}"

    return f"- {label}: {s}"


def _make_summary_bullets(program_id: str, retrieved: list[dict[str, Any]]) -> str:
    pairs = _pick_best_sentences(retrieved, n=20)
    prefix_lines = _summary_prefix_for_program(program_id)

    chosen: dict[str, str] = {}
    for sentence, _ref in pairs:
        bucket = _classify_summary_bucket(sentence)
        if not bucket or bucket in chosen:
            continue

        tl = sentence.lower()
        if bucket == "förderfähig" and any(k in tl for k in ["antrag stellen", "nachweis", "unterlagen", "de-minimis"]):
            continue

        chosen[bucket] = _normalize_summary_bullet(bucket, sentence)

    ordered = []
    bucket_order = ["förderart", "zielgruppe", "förderfähig", "antragstellung", "besonderheit"]

    existing_labels = {
        line.split(":", 1)[0].replace("- ", "").strip().lower()
        for line in prefix_lines
        if ":" in line
    }

    label_map = {
        "förderart": "förderart",
        "zielgruppe": "zielgruppe",
        "förderfähig": "förderfähig",
        "antragstellung": "antragstellung",
        "besonderheit": "besonderheit",
    }

    for bucket in bucket_order:
        if label_map[bucket] in existing_labels:
            continue
        if bucket in chosen:
            ordered.append(chosen[bucket])

    bullets = (prefix_lines + ordered)[:5]

    if not bullets:
        bullets = ["- Förderart: Keine belastbare Kurzfassung aus den gefundenen Quellen ableitbar"]

    return "\n".join(bullets)


def _generic_requirement_candidates(retrieved: list[dict[str, Any]]) -> list[tuple[str, SourceRef]]:
    candidates: list[tuple[str, SourceRef]] = []
    for sent, ref in _pick_best_sentences(retrieved, n=20):
        tl = sent.lower()

        if any(k in tl for k in ["antrag", "hausbank", "finanzierungspartner", "vorhabensbeginn", "vor beginn"]):
            candidates.append(("Antrag vor Projektbeginn einplanen", ref))
        elif any(k in tl for k in ["de-minimis", "beihilfe"]):
            candidates.append(("De-minimis-Vorgaben und Beihilferegeln prüfen", ref))
        elif any(k in tl for k in ["investitionen", "betriebsmittel", "maßnahmen", "förderfähig"]):
            candidates.append(("Förderfähige Maßnahmen und Kostenpositionen sauber abgrenzen", ref))
        elif any(k in tl for k in ["laufzeit", "zeitraum", "24 monaten", "projektlaufzeit"]):
            candidates.append(("Projektlaufzeit und Förderzeitraum beachten", ref))
        elif any(k in tl for k in ["nachweis", "unterlagen", "selbsterklärung"]):
            candidates.append(("Erforderliche Nachweise und Unterlagen vollständig vorbereiten", ref))
        elif any(k in tl for k in ["je vorhaben", "pro vorhaben", "ein antrag"]):
            candidates.append(("Für jedes Vorhaben einen eigenen Antrag vorsehen", ref))

    deduped: list[tuple[str, SourceRef]] = []
    seen: set[str] = set()
    for item, ref in candidates:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append((item, ref))
    return deduped


def _build_program_requirements(program_id: str, retrieved: list[dict[str, Any]], srcs: list[SourceRef]) -> list[ChecklistItem]:
    pid = (program_id or "").upper()
    default_ref = srcs[0] if srcs else None

    def _mk(text: str, criticality: str = "medium", ref: Optional[SourceRef] = None) -> Optional[ChecklistItem]:
        use_ref = ref or _find_best_ref_for_requirement(text, retrieved, default_ref)
        if not use_ref:
            return None
        return ChecklistItem(item=text, criticality=criticality, source_refs=[use_ref])

    items: list[ChecklistItem] = []

    if pid.startswith("KFW-ERP-DIGI-511") or pid.startswith("KFW-ERP-DIGI-512"):
        seed = [
            "Antrag vor Beginn des Digitalisierungsvorhabens einreichen",
            "Finanzierung über Hausbank oder Finanzierungspartner abwickeln",
            "Projektbezogene Investitionen und Betriebsmittel nachvollziehbar zuordnen",
            "Förderfähige Maßnahmen und Kostenpositionen sauber abgrenzen",
            "Für jedes Vorhaben einen eigenen Antrag vorsehen",
        ]
        for txt in seed:
            item = _mk(txt, "high" if "Antrag vor Beginn" in txt else "medium")
            if item:
                items.append(item)

    elif pid == "ZIM":
        seed = [
            "Antrag vor Beginn des FuE-Projekts vorbereiten",
            "Innovationsgehalt und technisches Risiko nachvollziehbar darstellen",
            "Projektziele, Arbeitsplan und Entwicklungslogik dokumentieren",
            "Projektkosten und Eigenanteil realistisch kalkulieren",
            "Kooperationsstruktur frühzeitig festlegen, falls Partner beteiligt sind",
        ]
        for txt in seed:
            item = _mk(txt, "high" if "Antrag vor Beginn" in txt else "medium")
            if item:
                items.append(item)

    elif pid == "KMU-INNOVATIV":
        seed = [
            "Einreichungsstichtage und Verfahrensschritte frühzeitig prüfen",
            "Forschungs- und Innovationsvorhaben klar abgrenzen",
            "Neuheitsgrad und Forschungsrisiko nachvollziehbar begründen",
            "Arbeitsplan und Verwertungsperspektive strukturieren",
            "Projektkosten und Ressourcen plausibel darstellen",
        ]
        for txt in seed:
            item = _mk(txt, "medium")
            if item:
                items.append(item)

    elif pid.startswith("EEW-BAFA-M1"):
        seed = [
            "Antrag vor Umsetzung der Energieeffizienzmaßnahme einreichen",
            "Energieeinsparpotenzial der Maßnahme nachvollziehbar nachweisen",
            "Investitionskosten und förderfähige Komponenten sauber dokumentieren",
            "Technische Anforderungen der förderfähigen Anlagen prüfen",
            "Umsetzung und Einsparwirkungen später belegbar dokumentieren",
        ]
        for txt in seed:
            item = _mk(txt, "high" if "Antrag vor Umsetzung" in txt else "medium")
            if item:
                items.append(item)

    elif pid.startswith("EEW-BAFA-M2"):
        seed = [
            "Antrag vor Umsetzung der Energieeffizienzmaßnahme einreichen",
            "Maßnahme einer förderfähigen Querschnittstechnologie zuordnen",
            "Technische Mindestanforderungen der Anlagen prüfen",
            "Energieeinsparungen nachvollziehbar dokumentieren",
            "Investitionskosten und Komponenten sauber aufschlüsseln",
        ]
        for txt in seed:
            item = _mk(txt, "high" if "Antrag vor Umsetzung" in txt else "medium")
            if item:
                items.append(item)

    elif pid.startswith("EEW-BAFA-M3"):
        seed = [
            "Antrag vor Einführung des Systems oder der Technik einreichen",
            "Förderfähige Software, Sensorik und Messtechnik sauber abgrenzen",
            "Energieverbrauchsdaten systematisch erfassen und auswerten",
            "Energiemanagement organisatorisch im Unternehmen verankern",
            "Mess- und Monitoringdaten nachvollziehbar dokumentieren",
        ]
        for txt in seed:
            item = _mk(txt, "medium")
            if item:
                items.append(item)

    elif pid.startswith("EEW-BAFA-M4"):
        seed = [
            "Antrag vor Beginn der Investitionsmaßnahme einreichen",
            "Einsparpotenzial von Energie oder Treibhausgasen nachweisen",
            "Technische Prozessänderung nachvollziehbar beschreiben",
            "Einsparkonzept und Investitionskosten sauber dokumentieren",
            "Umsetzung und Einsparwirkungen später belegen können",
        ]
        for txt in seed:
            item = _mk(txt, "high" if "Antrag vor Beginn" in txt else "medium")
            if item:
                items.append(item)

    elif pid == "GRW-MV-GEWERBE":
        seed = [
            "Investitionsvorhaben im ausgewiesenen Fördergebiet durchführen",
            "Antrag vor Beginn der Investition einreichen",
            "Wirtschaftliche Tragfähigkeit des Projekts nachweisen",
            "Investitionsvolumen und Beschäftigungseffekte dokumentieren",
            "Regionale Wirkung des Vorhabens nachvollziehbar darstellen",
        ]
        for txt in seed:
            item = _mk(txt, "high" if "Antrag vor Beginn" in txt else "medium")
            if item:
                items.append(item)

    elif pid == "GO-INNO":
        seed = [
            "Beratungsprojekt vor Beginn der Leistung beantragen",
            "Autorisierte Beratungsunternehmen einbinden",
            "Innovationsziel und Beratungsumfang klar festlegen",
            "Beratungsleistungen und Projektphasen dokumentieren",
            "Ergebnisse der Beratung für die weitere Umsetzung nutzbar machen",
        ]
        for txt in seed:
            item = _mk(txt, "medium")
            if item:
                items.append(item)

    seen_items = {x.item.lower() for x in items}
    for generic_text, generic_ref in _generic_requirement_candidates(retrieved):
        if generic_text.lower() in seen_items:
            continue
        item = _mk(generic_text, _criticality_from_text(generic_text), generic_ref)
        if item:
            items.append(item)
            seen_items.add(generic_text.lower())
        if len(items) >= 6:
            break

    return items[:6]

def _find_best_ref_for_requirement(text: str, retrieved: list[dict[str, Any]], fallback: Optional[SourceRef]) -> Optional[SourceRef]:
    text_l = text.lower()

    keyword_map = {
        "antrag": ["antrag", "vorhabensbeginn", "vor beginn", "einreichungsstichtage"],
        "hausbank": ["hausbank", "finanzierungspartner"],
        "förderfähig": ["förderfähig", "förderfaehig", "investitionen", "betriebsmittel", "maßnahmen"],
        "nachweise": ["nachweis", "unterlagen", "selbsterklärung"],
        "laufzeit": ["laufzeit", "zeitraum", "24 monaten", "projektlaufzeit"],
        "einsparung": ["einspar", "energieeffizienz", "treibhausgas", "thg"],
        "innovation": ["innovation", "fue", "forschung", "technisches risiko"],
    }

    wanted = []
    if "antrag" in text_l:
        wanted.extend(keyword_map["antrag"])
    if "hausbank" in text_l or "finanzierungspartner" in text_l:
        wanted.extend(keyword_map["hausbank"])
    if any(x in text_l for x in ["förderfähig", "investitionen", "betriebsmittel", "maßnahmen"]):
        wanted.extend(keyword_map["förderfähig"])
    if any(x in text_l for x in ["nachweis", "unterlagen"]):
        wanted.extend(keyword_map["nachweise"])
    if "laufzeit" in text_l or "zeitraum" in text_l:
        wanted.extend(keyword_map["laufzeit"])
    if any(x in text_l for x in ["einspar", "treibhausgas", "energieeffizienz"]):
        wanted.extend(keyword_map["einsparung"])
    if any(x in text_l for x in ["innovation", "fue", "forschung", "technisches risiko"]):
        wanted.extend(keyword_map["innovation"])

    for hit in retrieved:
        sent = _clean_display_text(str(hit.get("text") or "")).lower()
        if any(k in sent for k in wanted):
            ref = _extract_source_ref(hit)
            if ref:
                return ref

    return fallback


def _build_profile_agnostic_risks(program_id: str, retrieved: list[dict[str, Any]], srcs: list[SourceRef]) -> list[RiskItem]:
    if not srcs:
        return []

    joined = " ".join([_clean_display_text(str(x.get("text") or "")) for x in retrieved]).lower()
    ref = srcs[0]
    risks: list[RiskItem] = []

    if "vorhabensbeginn" in joined or "beginn der arbeiten" in joined or "vor beginn" in joined:
        risks.append(
            RiskItem(
                risk="Ein vorzeitiger Projektbeginn kann die Förderfähigkeit ausschließen.",
                criticality="high",
                source_refs=[ref],
            )
        )

    if "de-minimis" in joined:
        risks.append(
            RiskItem(
                risk="De-minimis-Vorgaben können Förderfähigkeit oder Förderhöhe begrenzen.",
                criticality="medium",
                source_refs=[ref],
            )
        )

    pid = (program_id or "").upper()
    if pid.startswith("KFW-ERP-DIGI-"):
        risks.append(
            RiskItem(
                risk="Die Antragstellung läuft nicht direkt, sondern über Hausbank oder Finanzierungspartner.",
                criticality="medium",
                source_refs=[ref],
            )
        )
    elif pid == "ZIM":
        risks.append(
            RiskItem(
                risk="Wenn technisches Risiko oder Innovationshöhe nicht klar belegt werden, sinken die Erfolgschancen deutlich.",
                criticality="high",
                source_refs=[ref],
            )
        )
    elif pid == "KMU-INNOVATIV":
        risks.append(
            RiskItem(
                risk="Das Vorhaben muss klar als risikoreiches FuE-Projekt begründet werden.",
                criticality="high",
                source_refs=[ref],
            )
        )
    elif pid.startswith("EEW-BAFA-"):
        risks.append(
            RiskItem(
                risk="Technische Anforderungen und Einsparwirkungen müssen nachvollziehbar dokumentiert werden.",
                criticality="high",
                source_refs=[ref],
            )
        )
    elif pid == "GO-INNO":
        risks.append(
            RiskItem(
                risk="Die Förderfähigkeit hängt davon ab, dass Beratungsinhalt und Beratungsunternehmen korrekt eingeordnet sind.",
                criticality="medium",
                source_refs=[ref],
            )
        )
    elif pid == "GRW-MV-GEWERBE":
        risks.append(
            RiskItem(
                risk="Standort, Primäreffekt und Investitionswirkung müssen belastbar nachgewiesen werden.",
                criticality="high",
                source_refs=[ref],
            )
        )

    deduped: list[RiskItem] = []
    seen: set[str] = set()
    for r in risks:
        key = r.risk.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    return deduped[:4]

# -----------------------------
# Public API
# -----------------------------

def build_grounded_detail_from_chunks(*, program_id: str, retrieved: list[dict[str, Any]]) -> GroundedDetail:
    retrieved = list(retrieved or [])

    srcs = _dedupe_sources([s for s in (_extract_source_ref(x) for x in retrieved) if s is not None])

    summary = _make_summary_bullets(program_id, retrieved)
    program_requirements = _build_program_requirements(program_id, retrieved, srcs)
    risks = _build_profile_agnostic_risks(program_id, retrieved, srcs)

    return GroundedDetail(
        program_id=program_id,
        summary=summary,
        program_requirements=program_requirements,
        risks=risks,
        sources=srcs,
    )


def validate_grounded_output(detail: GroundedDetail, *, retrieved_sources: list[SourceRef]) -> GroundedDetail:
    base = _dedupe_sources(retrieved_sources or detail.sources)
    allow = {(s.document_id, s.chunk_index, s.doc_type, s.page_ref, s.filename) for s in base}

    def _filter_refs(refs: list[SourceRef]) -> list[SourceRef]:
        out = []
        for r in refs or []:
            key = (r.document_id, r.chunk_index, r.doc_type, r.page_ref, r.filename)
            if key in allow:
                out.append(r)
        return _dedupe_sources(out)

    program_requirements2: list[ChecklistItem] = []
    for c in detail.program_requirements or []:
        refs = _filter_refs(list(c.source_refs or []))
        if not refs:
            continue
        txt = _clean_display_text(c.item)
        if len(txt) < 10:
            continue
        program_requirements2.append(
            ChecklistItem(item=txt, criticality=c.criticality, source_refs=refs)
        )

    risks2: list[RiskItem] = []
    for r in detail.risks or []:
        refs = _filter_refs(list(r.source_refs or []))
        if not refs:
            continue
        txt = _clean_display_text(r.risk)
        if len(txt) < 10:
            continue
        risks2.append(RiskItem(risk=txt, criticality=r.criticality, source_refs=refs))

    summary_lines = []
    for line in str(detail.summary or "").splitlines():
        line = _clean_display_text(line)
        if not line:
            continue
        if not line.startswith("- "):
            line = f"- {line.lstrip('- ').strip()}"
        summary_lines.append(line)

    summary_clean = "\n".join(summary_lines) if summary_lines else "- Förderart: Keine belastbare Kurzfassung verfügbar"

    return GroundedDetail(
        program_id=detail.program_id,
        summary=summary_clean,
        program_requirements=program_requirements2,
        risks=risks2,
        sources=base,
    )