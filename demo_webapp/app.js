let currentResults = [];
let currentDetail = null;
let currentProfile = null;
let currentQueryText = "";

function $(id) {
  return document.getElementById(id);
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getApiBase() {
  return "https://foerdermatch-ai-backend.up.railway.app";
}

function getEffectiveScore(item) {
  return Number(item?.effective_total_score ?? item?.total_score ?? 0) || 0;
}

function getNormalizedRuleScore(item) {
  const raw = Number(item?.rule_score ?? 0);
  const normalized = (raw / 60) * 100;
  return Math.max(0, Math.min(95, Math.round(normalized)));
}

function getNormalizedSemanticScore(item) {
  const raw = Number(item?.semantic_score ?? 0);
  const normalized = (raw / 40) * 100;
  return Math.max(0, Math.min(95, Math.round(normalized)));
}

function getCurrentSortMode() {
  return $("sortMode")?.value || "effective_total_score";
}

function statusMeta(item) {
  const score = getEffectiveScore(item);
  const hardFail = item?.hard_fail === true || item?.status === "blocked";

  if (hardFail) {
    return {
      label: "Nicht förderfähig",
      badgeClass: "badge badge--blocked",
      icon: "⛔",
      shortLabel: "Blocked",
    };
  }

  if (score >= 70) {
    return {
      label: "Gute Passung",
      badgeClass: "badge badge--eligible",
      icon: "🟢",
      shortLabel: "Stark",
    };
  }

  if (score >= 40) {
    return {
      label: "Teilweise passend",
      badgeClass: "badge badge--maybe",
      icon: "🟡",
      shortLabel: "Mittel",
    };
  }

  return {
    label: "Schwache Passung",
    badgeClass: "badge badge--blocked",
    icon: "🔴",
    shortLabel: "Schwach",
  };
}

function apiPillState(text, state = "idle") {
  const el = $("apiStatus");
  if (!el) return;
  el.textContent = text;
  el.className = "api-pill";
  if (state === "ok") el.classList.add("api-pill--ok");
  else if (state === "error") el.classList.add("api-pill--error");
  else el.classList.add("api-pill--idle");
}

function bannerState(text, variant = "neutral") {
  const el = $("statusBanner");
  if (!el) return;
  el.textContent = text;
  el.className = "status-banner";
  el.classList.add(`status-banner--${variant}`);
}

function showLoading(show) {
  $("loadingBox")?.classList.toggle("hidden", !show);
}

function employeesToSizeClass(employees) {
  if (!employees || employees <= 0) return "";
  if (employees <= 9) return "micro";
  if (employees <= 49) return "small";
  if (employees <= 249) return "medium";
  return "large";
}

function revenueToBand(mioValue) {
  const x = Number(mioValue);
  if (!Number.isFinite(x) || x <= 0) return "unknown";
  if (x < 2) return "under_2m";
  if (x <= 10) return "2m_to_10m";
  if (x <= 50) return "10m_to_50m";
  if (x <= 100) return "50m_to_100m";
  return "over_100m";
}

function buildProfileFromForm() {
  const employees = Number($("mitarbeiterzahl")?.value || 0);
  const revenueMio = Number($("jahresumsatz")?.value || 0);

  const ageRaw = $("unternehmensalter")?.value || "";
  let companyAgeYears = null;
  if (ageRaw === "startup") companyAgeYears = 2;
  else if (ageRaw === "scaleup") companyAgeYears = 7;
  else if (ageRaw === "established") companyAgeYears = 12;

  return {
    company: {
      industry: $("branche")?.value || "",
      employee_count: employees,
      company_age_years: companyAgeYears,
      revenue_band: revenueToBand(revenueMio),
      state: $("standortBundesland")?.value || "",
      size_class: employeesToSizeClass(employees),
      is_kmu: employees > 0 ? employees < 250 : null,
      country: "DE",
      in_grw_funding_area: $("inGrwArea")?.checked === true,
    },
    project: {
      category: $("projektKategorie")?.value || "",
      start_status: $("projektStatus")?.value || "planned",
      is_r_and_d: $("isRandD")?.checked === true,
      has_technical_risk: $("hasTechnicalRisk")?.checked === true,
      has_primary_effect: $("hasPrimaryEffect")?.checked === true,
      meets_10_percent_jobs_or_50_percent_depreciation:
        $("meetsInvestmentThreshold")?.checked === true,
    },
    constraints: {
      de_minimis_status: $("deMinimis")?.value || "unknown",
      is_excluded_sector: $("excludedSector")?.checked === true,
    },
    financing: {
      needs_guarantee: $("needsGuarantee")?.checked === true,
    },
  };
}

function buildAutoQuery(profile) {
  const parts = [
    profile.company.industry ? `Branche: ${profile.company.industry}` : "",
    profile.project.category ? `Vorhaben: ${profile.project.category}` : "",
    profile.project.start_status === "started"
      ? "Projekt wurde bereits gestartet."
      : "Projekt ist noch nicht gestartet.",
    profile.project.is_r_and_d ? "FuE-Bezug vorhanden." : "",
    profile.project.has_technical_risk ? "Technisches Risiko vorhanden." : "",
    profile.financing.needs_guarantee ? "Haftungsfreistellung relevant." : "",
    profile.constraints.de_minimis_status
      ? `De-minimis: ${profile.constraints.de_minimis_status}`
      : "",
  ].filter(Boolean);

  return parts.join(" ");
}

async function checkHealth() {
  apiPillState("Backend wird geprüft …", "idle");

  try {
    const response = await fetch(`${getApiBase()}/health`, { method: "GET" });

    if (!response.ok) {
      throw new Error(`Health check fehlgeschlagen (${response.status})`);
    }

    const data = await response.json();
    if (data.status === "ok") {
      apiPillState("Backend verbunden", "ok");
    } else {
      apiPillState("Backend antwortet unerwartet", "idle");
    }
  } catch (error) {
    apiPillState("Backend nicht erreichbar", "error");
    console.error("checkHealth failed:", error);
  }
}

function scoreBar(label, value) {
  const safe = Math.max(0, Math.min(100, Number(value) || 0));
  return `
    <div class="score-bar">
      <div class="score-bar__label">${escapeHtml(label)}</div>
      <div class="score-bar__track"><span class="score-bar__fill" style="width:${safe}%"></span></div>
      <div class="score-bar__value">${safe}</div>
    </div>
  `;
}

function getSortedResults(results) {
  const sortMode = getCurrentSortMode();
  const sorted = [...safeArray(results)];

  sorted.sort((a, b) => {
    const aHardFail = a?.hard_fail === true ? 1 : 0;
    const bHardFail = b?.hard_fail === true ? 1 : 0;

    if (aHardFail !== bHardFail) {
      return aHardFail - bHardFail;
    }

    let aValue = 0;
    let bValue = 0;

    if (sortMode === "rule_score") {
      aValue = Number(a?.rule_score ?? 0);
      bValue = Number(b?.rule_score ?? 0);
    } else if (sortMode === "semantic_score") {
      aValue = Number(a?.semantic_score ?? 0);
      bValue = Number(b?.semantic_score ?? 0);
    } else {
      aValue = getEffectiveScore(a);
      bValue = getEffectiveScore(b);
    }

    if (bValue !== aValue) {
      return bValue - aValue;
    }

    return getEffectiveScore(b) - getEffectiveScore(a);
  });

  return sorted;
}

function formatMissingField(field) {
  const mapping = {
    "constraints.de_minimis_status": "De-minimis-Status",
    "project.start_status": "Projektstatus",
    "company.is_kmu": "KMU-Status",
    "company.size_class": "Unternehmensgröße",
    "company.employee_count": "Mitarbeiterzahl",
    "company.revenue_band": "Umsatzband",
    "company.state": "Standort / Bundesland",
    "project.category": "Projektkategorie",
    "project.is_r_and_d": "FuE-Bezug",
    "project.has_technical_risk": "Technisches Risiko",
    "financing.needs_guarantee": "Haftungsfreistellung / Risikoübernahme",
  };
  return mapping[field] || field;
}

function buildWhyFits(item, profile = null) {
  const reasons = [];
  const score = getEffectiveScore(item);
  const missingFields = safeArray(item?.missing_fields);
  const rules = safeArray(item?.rules);

  if (item?.hard_fail) {
    const failReasons = safeArray(item?.hard_fail_reasons);
    if (failReasons.length) {
      reasons.push(`Ausschlussgrund erkannt: ${failReasons[0]}`);
    } else {
      reasons.push("Für dieses Profil wurde ein Ausschlusskriterium erkannt.");
    }
    return reasons;
  }

  const passedRules = rules.filter((r) => {
    const status = String(r?.status || "").toLowerCase();
    return status === "passed" || status === "fulfilled" || r?.passed === true;
  });

  for (const rule of passedRules) {
    const reason = String(rule?.reason || rule?.message || "").trim();
    if (!reason) continue;

    const cleaned = reason
      .replace(/^profil passt[:,]?\s*/i, "")
      .replace(/^erfüllt[:,]?\s*/i, "")
      .replace(/^passed[:,]?\s*/i, "")
      .trim();

    if (cleaned && cleaned.length >= 12) {
      reasons.push(cleaned.charAt(0).toUpperCase() + cleaned.slice(1));
    }

    if (reasons.length >= 2) break;
  }

  const joined = reasons.join(" ").toLowerCase();

  if (
    profile?.project?.start_status === "planned" &&
    !joined.includes("begonnen") &&
    !joined.includes("vorhaben")
  ) {
    reasons.push("Das Vorhaben wurde laut Profil noch nicht begonnen.");
  }

  if (
    profile?.project?.is_r_and_d === true &&
    !joined.includes("fu") &&
    !joined.includes("f&e")
  ) {
    reasons.push("Das Vorhaben weist laut Profil einen FuE-Bezug auf.");
  }

  if (
    profile?.project?.has_technical_risk === true &&
    !joined.includes("technisch") &&
    !joined.includes("risiko")
  ) {
    reasons.push("Das Vorhaben enthält laut Profil technisches Risiko bzw. Neuheitsgrad.");
  }

  if (profile?.company?.is_kmu === true && !joined.includes("kmu")) {
    reasons.push("Das Unternehmen erfüllt die KMU-Kriterien.");
  }

  if (reasons.length < 3) {
    if (score >= 70) {
      reasons.push("Die Gesamtbewertung fällt deutlich positiv aus.");
    } else if (score >= 40) {
      reasons.push("Das Profil zeigt eine grundsätzliche Passung zum Programm.");
    }
  }

  if (!reasons.length && missingFields.length) {
    reasons.push(
      `Eine abschließende Bewertung ist noch eingeschränkt, weil Angaben fehlen: ${missingFields
        .slice(0, 2)
        .map(formatMissingField)
        .join(", ")}.`
    );
  }

  const deduped = [];
  const seen = new Set();

  for (const reason of reasons) {
    const cleaned = String(reason || "").trim();
    if (!cleaned) continue;
    const key = cleaned.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(cleaned);
    if (deduped.length >= 4) break;
  }

  if (!deduped.length) {
    deduped.push("Die Bewertung zeigt eine grundsätzliche Passung zum Programm.");
  }

  return deduped;
}

function renderRanking(results) {
  const list = $("rankingList");
  if (!list) return;

  const sorted = getSortedResults(results);

  if (!sorted.length) {
    list.innerHTML = `<div class="empty-state">Keine Programme gefunden.</div>`;
    return;
  }

  list.innerHTML = sorted
    .map((item, idx) => {
      const meta = statusMeta(item);
      const blockers = item.hard_fail
        ? safeArray(item.hard_fail_reasons)
        : safeArray(item.missing_fields).map(formatMissingField);
      const whyFits = buildWhyFits(item, currentProfile);

      return `
      <article class="result-card">
        <div class="result-card__header">
          <div>
            <span class="${meta.badgeClass}">${meta.icon} ${escapeHtml(meta.label)}</span>
            <h4>${escapeHtml(item.program_id || "Förderprogramm")}</h4>
          </div>
          <div class="rank-chip">${idx + 1}</div>
        </div>

        <div class="result-card__meta">
          <div class="score-summary">
            ${scoreBar("Gesamt", getEffectiveScore(item))}
            ${scoreBar("Rule Score", getNormalizedRuleScore(item))}
            ${scoreBar("Semantic Score", getNormalizedSemanticScore(item))}
          </div>

          <div class="kpi-group">
            <div class="kpi">
              <div class="kpi-label">Gesamtscore</div>
              <strong>${escapeHtml(getEffectiveScore(item))}</strong>
            </div>
            <div class="kpi">
              <div class="kpi-label">Bewertung</div>
              <strong>${escapeHtml(meta.shortLabel)}</strong>
            </div>
          </div>
        </div>

        <div class="card-grid">
          <div style="display: grid; gap: 14px; width: 100%;">
            <div class="info-box">
              <div class="meta-label">Warum es passt</div>
              <ul class="report-list">
                ${whyFits.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}
              </ul>
            </div>

            ${
              blockers.length
                ? `
                <div class="info-box">
                  <div class="meta-label">Blocker / offene Punkte</div>
                  <ul class="blocker-list">
                    ${blockers.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}
                  </ul>
                </div>
              `
                : ""
            }
          </div>
        </div>

        <div class="result-card__footer">
          <button class="button button--ghost button--small" type="button" onclick="loadDetail('${escapeHtml(item.program_id)}')">
            Details
          </button>
        </div>
      </article>
    `;
    })
    .join("");
}

function renderSources(sources) {
  const items = groupSourcesByDocument(sources);

  if (!items.length) {
    return `<p class="muted">Keine Quellen vorhanden.</p>`;
  }

  return items
    .map((src) => {
      const label = escapeHtml(src.filename || src.doc_type || "Quelle");
      const pages = src.page_refs.length
        ? `S. ${escapeHtml(src.page_refs.join(", "))}`
        : "Seitenangabe nicht verfügbar";

      const officialLink = src.source_url || null;
      const localLink = src.local_url || null;
      const primaryLink = officialLink || localLink;

      return `
        <div class="source-card">
          <div><strong>${
            primaryLink
              ? `<a href="${escapeHtml(primaryLink)}" target="_blank" rel="noopener noreferrer">${label}</a>`
              : label
          }</strong></div>
          <div class="source-meta">${escapeHtml(src.doc_type || "Dokument")} · ${pages}</div>
          ${
            localLink && officialLink && localLink !== officialLink
              ? `<div class="source-meta"><a href="${escapeHtml(localLink)}" target="_blank" rel="noopener noreferrer">Lokale Datei öffnen</a></div>`
              : ""
          }
        </div>
      `;
    })
    .join("");
}

function buildReportHtml(result) {
  const detail = result?.detail || {};
  const meta = statusMeta(result);
  const sources = safeArray(detail.sources);
  const programRequirements = safeArray(detail.program_requirements);
  const risks = safeArray(detail.typical_risks);
  const blockers = result?.hard_fail
    ? safeArray(result?.hard_fail_reasons)
    : safeArray(result?.missing_fields).map(formatMissingField);
  const disclaimer = detail.disclaimer || "";

  return `
    <div class="report-card">
      <div class="report-header">
        <div>
          <span class="${meta.badgeClass}">${meta.icon} ${escapeHtml(meta.label)}</span>
          <h4>${escapeHtml(result.program_id || "Programm")}</h4>
        </div>
        <div class="kpi-group">
          <div class="kpi">
            <div class="kpi-label">Gesamtscore</div>
            <strong>${escapeHtml(getEffectiveScore(result))}</strong>
          </div>
          <div class="kpi">
            <div class="kpi-label">Rule Score</div>
            <strong>${escapeHtml(getNormalizedRuleScore(result))}</strong>
          </div>
          <div class="kpi">
            <div class="kpi-label">Semantic Score</div>
            <strong>${escapeHtml(getNormalizedSemanticScore(result))}</strong>
          </div>
        </div>
      </div>
    </div>

    <div class="report-card">
      <h4>Zusammenfassung</h4>
      <div class="detail-summary">
        ${
          String(detail.summary || "")
            .split("\n")
            .filter((line) => line.trim())
            .map((line) => {
              const cleaned = line.replace(/^\-\s*/, "").trim();
              return `<div>• ${escapeHtml(cleaned)}</div>`;
            })
            .join("") || "Keine Zusammenfassung verfügbar."
        }
      </div>
    </div>

    <div class="report-card">
      <h4>Nächste Schritte</h4>
      ${
        safeArray(result.next_actions).length
          ? `<ul class="report-list">${safeArray(result.next_actions)
              .map((x) => `<li>${escapeHtml(x)}</li>`)
              .join("")}</ul>`
          : `<p class="muted">Keine zusätzlichen nächsten Schritte vorhanden.</p>`
      }
    </div>

    ${
      blockers.length
        ? `
        <div class="report-card">
          <h4>Blocker / offene Punkte</h4>
          <ul class="blocker-list">
            ${blockers.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}
          </ul>
        </div>
      `
        : ""
    }

    <div class="report-card">
      <h4>Anforderungen des Förderprogramms</h4>
      <p class="muted">Diese Punkte gelten unabhängig vom Unternehmensprofil und sollten bei der Antragstellung berücksichtigt werden.</p>
      ${
        programRequirements.length
          ? `<ul class="report-list">${programRequirements
              .map((x) => `<li>${escapeHtml(x.item || "")}</li>`)
              .join("")}</ul>`
          : `<p class="muted">Keine programmspezifischen Anforderungen verfügbar.</p>`
      }
    </div>

    <div class="report-card">
      <h4>Typische Risiken</h4>
      ${
        risks.length
          ? `<ul class="risk-list">${risks
              .map((x) => `<li>${escapeHtml(x.risk || "")}</li>`)
              .join("")}</ul>`
          : `<p class="muted">Keine typischen Risiken vorhanden.</p>`
      }
    </div>

    <div class="report-card">
      <h4>Quellen</h4>
      ${renderSources(sources)}
    </div>

    ${
      disclaimer
        ? `
        <div class="report-card">
          <h4>Hinweis</h4>
          <p class="muted">${escapeHtml(disclaimer)}</p>
        </div>
      `
        : ""
    }
  `;
}

function sanitizeFilename(value) {
  return (
    String(value || "report")
      .normalize("NFKD")
      .replace(/[^\w\-]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 80) || "report"
  );
}

function formatExportDate(date = new Date()) {
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const yyyy = String(date.getFullYear());
  const hh = String(date.getHours()).padStart(2, "0");
  const min = String(date.getMinutes()).padStart(2, "0");
  return `${dd}.${mm}.${yyyy}, ${hh}:${min}`;
}

function normalizePdfText(value) {
  return String(value ?? "")
    .replace(/\u2022/g, "-")
    .replace(/\u00A0/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function wrapPdfText(text, maxLen = 90) {
  const raw = normalizePdfText(text);
  if (!raw) return [""];

  const words = raw.split(" ");
  const lines = [];
  let line = "";

  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (next.length <= maxLen) {
      line = next;
      continue;
    }

    if (line) lines.push(line);

    if (word.length <= maxLen) {
      line = word;
      continue;
    }

    let rest = word;
    while (rest.length > maxLen) {
      lines.push(rest.slice(0, maxLen));
      rest = rest.slice(maxLen);
    }
    line = rest;
  }

  if (line) lines.push(line);
  return lines;
}

function buildSummaryLines(summary) {
  return String(summary || "")
    .split("\n")
    .map((line) => line.replace(/^\-\s*/, "").trim())
    .filter(Boolean);
}


function normalizePageRef(pageRef) {
  return String(pageRef || "")
    .replace(/^S\.\s*/i, "")
    .trim();
}

function groupSourcesByDocument(items) {
  const groups = new Map();

  for (const src of safeArray(items)) {
    const documentId = Number(src?.document_id || 0);
    const filename = String(src?.filename || src?.doc_type || "Quelle").trim();
    const docType = String(src?.doc_type || "Dokument").trim();
    const sourceUrl = src?.source_url || null;
    const localUrl = src?.url || src?.filepath || null;
    const pageRef = normalizePageRef(src?.page_ref);

    const key = documentId > 0
      ? `doc:${documentId}`
      : `file:${filename}::${sourceUrl || localUrl || ""}`;

    if (!groups.has(key)) {
      groups.set(key, {
        document_id: documentId,
        filename,
        doc_type: docType,
        source_url: sourceUrl,
        local_url: localUrl,
        page_refs: [],
      });
    }

    const group = groups.get(key);

    if (pageRef && !group.page_refs.includes(pageRef)) {
      group.page_refs.push(pageRef);
    }
  }

  return Array.from(groups.values()).sort((a, b) => {
    return String(a.filename).localeCompare(String(b.filename), "de");
  });
}

async function createReportPdfBlob(result) {
  if (!window.PDFLib) {
    throw new Error("PDF-Library nicht geladen.");
  }

  const { PDFDocument, StandardFonts, rgb } = window.PDFLib;

  const pdfDoc = await PDFDocument.create();
  const fontRegular = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const fontBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

  const pageWidth = 595.28;
  const pageHeight = 841.89;
  const margin = 44;
  const contentWidth = pageWidth - margin * 2;
  const footerReserve = 30;

  const colorText = rgb(0.13, 0.16, 0.2);
  const colorMuted = rgb(0.42, 0.47, 0.54);
  const colorLine = rgb(0.84, 0.87, 0.91);
  const colorPanel = rgb(0.97, 0.98, 0.99);
  const colorPanelAlt = rgb(0.94, 0.96, 0.99);
  const colorAccent = rgb(0.16, 0.33, 0.58);

  const detail = result?.detail || {};
  const meta = statusMeta(result);
  const blockers = result?.hard_fail
    ? safeArray(result?.hard_fail_reasons)
    : safeArray(result?.missing_fields).map(formatMissingField);

  const nextActions = safeArray(result?.next_actions);
  const requirements = safeArray(detail?.program_requirements);
  const risks = safeArray(detail?.typical_risks);
  const sources = groupSourcesByDocument(detail?.sources);
  const disclaimer = normalizePdfText(detail?.disclaimer || "");
  const summaryLines = buildSummaryLines(detail?.summary);

  let page = pdfDoc.addPage([pageWidth, pageHeight]);
  let y = pageHeight - margin;

  function addPage() {
    page = pdfDoc.addPage([pageWidth, pageHeight]);
    y = pageHeight - margin;
  }

  function ensureSpace(heightNeeded) {
    if (y - heightNeeded < margin + footerReserve) {
      addPage();
    }
  }


  function drawWrappedParagraph(text, opts = {}) {
    const {
      x = margin,
      size = 11,
      lineHeight = 15,
      maxLen = 92,
      font = fontRegular,
      color = colorText,
      indent = 0,
    } = opts;

    const lines = wrapPdfText(text, maxLen);
    for (const line of lines) {
      ensureSpace(lineHeight);
      page.drawText(line, {
        x: x + indent,
        y,
        size,
        font,
        color,
      });
      y -= lineHeight;
    }
  }

  function drawSectionTitle(title) {
    ensureSpace(34);
    y -= 4;
    page.drawLine({
      start: { x: margin, y: y + 14 },
      end: { x: pageWidth - margin, y: y + 14 },
      thickness: 1,
      color: colorLine,
    });
    page.drawText(normalizePdfText(title), {
      x: margin,
      y,
      size: 14,
      font: fontBold,
      color: colorAccent,
    });
    y -= 24;
  }

  function drawBulletList(items, emptyText) {
    if (!safeArray(items).length) {
      drawWrappedParagraph(emptyText, { color: colorMuted });
      y -= 6;
      return;
    }

    for (const item of items) {
      const text = typeof item === "string" ? item : item?.item || item?.risk || "";
      const lines = wrapPdfText(`- ${text}`, 88);
      for (const line of lines) {
        ensureSpace(15);
        page.drawText(normalizePdfText(line), {
          x: margin,
          y,
          size: 11,
          font: fontRegular,
          color: colorText,
        });
        y -= 15;
      }
      y -= 2;
    }
  }

  function drawChecklist(items) {
    if (!safeArray(items).length) {
      drawWrappedParagraph("Keine zusätzlichen nächsten Schritte vorhanden.", {
        color: colorMuted,
      });
      y -= 6;
      return;
    }

    for (const item of items) {
      const lines = wrapPdfText(`- ${item}`, 88);
      for (const line of lines) {
        ensureSpace(15);
        page.drawText(normalizePdfText(line), {
          x: margin,
          y,
          size: 11,
          font: fontRegular,
          color: colorText,
        });
        y -= 15;
      }
      y -= 2;
    }
  }

  function fitTextToWidth(text, font, maxSize, minSize, maxWidth) {
    let size = maxSize;
    const safeText = normalizePdfText(text);

    while (size > minSize && font.widthOfTextAtSize(safeText, size) > maxWidth) {
      size -= 0.5;
    }

    return Math.max(size, minSize);
  }

  function drawSourceEntries(items) {
    if (!safeArray(items).length) {
      drawWrappedParagraph("Keine Quellen vorhanden.", { color: colorMuted });
      y -= 6;
      return;
    }

    for (const src of items) {
      const title = normalizePdfText(src?.filename || src?.doc_type || "Quelle");
      const pagesText =
        safeArray(src?.page_refs).length
          ? `Genutzte Seiten: S. ${src.page_refs.join(", ")}`
          : "Genutzte Seiten: keine Seitenangabe";

      const metaLine = normalizePdfText(
        `${src?.doc_type || "Dokument"} · ${pagesText}`
      );

      const visibleLink = normalizePdfText(
        src?.source_url || src?.local_url || ""
      );

      const urlFontSize = visibleLink
        ? fitTextToWidth(visibleLink, fontRegular, 9, 6, contentWidth - 24)
        : 8;

      const estimatedHeight = 18 + 14 + 16 + 14;
      ensureSpace(estimatedHeight);

      const boxTop = y + 6;
      const boxHeight = estimatedHeight - 6;

      page.drawRectangle({
        x: margin,
        y: boxTop - boxHeight,
        width: contentWidth,
        height: boxHeight,
        color: colorPanel,
        borderWidth: 1,
        borderColor: colorLine,
      });

      page.drawText(title, {
        x: margin + 12,
        y: y - 6,
        size: 11,
        font: fontBold,
        color: colorText,
      });

      page.drawText(metaLine, {
        x: margin + 12,
        y: y - 22,
        size: 9,
        font: fontRegular,
        color: colorMuted,
      });

      if (visibleLink) {
        page.drawText(visibleLink, {
          x: margin + 12,
          y: y - 42,
          size: urlFontSize,
          font: fontRegular,
          color: colorAccent,
        });
      } else {
        page.drawText("Kein Link verfügbar", {
          x: margin + 12,
          y: y - 42,
          size: 8,
          font: fontRegular,
          color: colorMuted,
        });
      }

      y = boxTop - boxHeight - 10;
    }
  }

  function drawFooter(pageIndex, totalPages) {
    const footerText = `FörderMatch AI · Export · Seite ${pageIndex} von ${totalPages}`;
    const size = 9;
    const width = fontRegular.widthOfTextAtSize(footerText, size);
    page.drawLine({
      start: { x: margin, y: 28 },
      end: { x: pageWidth - margin, y: 28 },
      thickness: 1,
      color: colorLine,
    });
    page.drawText(footerText, {
      x: pageWidth - margin - width,
      y: 14,
      size,
      font: fontRegular,
      color: colorMuted,
    });
  }

  ensureSpace(120);

  page.drawRectangle({
    x: margin,
    y: y - 84,
    width: contentWidth,
    height: 84,
    color: colorPanelAlt,
    borderWidth: 1,
    borderColor: colorLine,
  });

  page.drawText("FörderMatch AI · Exportreport", {
    x: margin + 16,
    y: y - 22,
    size: 11,
    font: fontBold,
    color: colorAccent,
  });

  page.drawText(normalizePdfText(result?.program_id || "Programm"), {
    x: margin + 16,
    y: y - 44,
    size: 18,
    font: fontBold,
    color: colorText,
  });

  page.drawText(`Status: ${normalizePdfText(meta.label)}`, {
    x: margin + 16,
    y: y - 64,
    size: 10,
    font: fontRegular,
    color: colorText,
  });

  page.drawText(`Erstellt am: ${formatExportDate()}`, {
    x: pageWidth - margin - 150,
    y: y - 22,
    size: 10,
    font: fontRegular,
    color: colorMuted,
  });

  const kpiTopY = y - 112;
  const cardWidth = (contentWidth - 16) / 3;

  [
    { label: "Gesamtscore", value: String(getEffectiveScore(result)) },
    { label: "Rule Score", value: String(getNormalizedRuleScore(result)) },
    { label: "Semantic Score", value: String(getNormalizedSemanticScore(result)) },
  ].forEach((kpi, index) => {
    const x = margin + index * (cardWidth + 8);
    page.drawRectangle({
      x,
      y: kpiTopY - 42,
      width: cardWidth,
      height: 42,
      color: colorPanel,
      borderWidth: 1,
      borderColor: colorLine,
    });
    page.drawText(kpi.label, {
      x: x + 10,
      y: kpiTopY - 14,
      size: 9,
      font: fontRegular,
      color: colorMuted,
    });
    page.drawText(kpi.value, {
      x: x + 10,
      y: kpiTopY - 31,
      size: 14,
      font: fontBold,
      color: colorText,
    });
  });

  y = kpiTopY - 58;

  drawSectionTitle("Zusammenfassung");
  if (summaryLines.length) {
    drawBulletList(summaryLines, "Keine Zusammenfassung verfügbar.");
  } else {
    drawWrappedParagraph("Keine Zusammenfassung verfügbar.", { color: colorMuted });
  }
  y -= 8;

  drawSectionTitle("Nächste Schritte");
  drawChecklist(nextActions);
  y -= 8;

  if (blockers.length) {
    drawSectionTitle("Blocker / offene Punkte");
    drawBulletList(blockers, "Keine offenen Punkte vorhanden.");
    y -= 8;
  }

  drawSectionTitle("Anforderungen des Förderprogramms");
  drawBulletList(
    requirements.map((x) => x?.item || ""),
    "Keine programmspezifischen Anforderungen verfügbar."
  );
  y -= 8;

  drawSectionTitle("Typische Risiken");
  drawBulletList(
    risks.map((x) => x?.risk || ""),
    "Keine typischen Risiken vorhanden."
  );
  y -= 8;

  drawSectionTitle("Quellen");
  drawSourceEntries(sources);
  y -= 8;

  if (disclaimer) {
    drawSectionTitle("Hinweis");
    drawWrappedParagraph(disclaimer, {
      color: colorMuted,
      maxLen: 90,
      lineHeight: 15,
    });
    y -= 6;
  }

  const totalPages = pdfDoc.getPageCount();
  pdfDoc.getPages().forEach((p, index) => {
    page = p;
    drawFooter(index + 1, totalPages);
  });

  const bytes = await pdfDoc.save();
  return new Blob([bytes], { type: "application/pdf" });
}

async function downloadCurrentReportPdf() {
  if (!currentDetail) {
    if (currentResults.length) {
      bannerState(
        "Bitte zuerst ein Programmdetail öffnen, bevor du den PDF-Report exportierst.",
        "warning"
      );
    } else {
      bannerState("Bitte zuerst eine Analyse starten.", "warning");
    }
    return;
  }

  try {
    const blob = await createReportPdfBlob(currentDetail);
    const url = URL.createObjectURL(blob);
    const fileBase = sanitizeFilename(
      currentDetail?.program_id || "FoerderMatch_Report"
    );

    const a = document.createElement("a");
    a.href = url;
    a.download = `${fileBase}_Report.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();

    setTimeout(() => URL.revokeObjectURL(url), 2000);
    bannerState("PDF-Report wurde erstellt.", "success");
  } catch (error) {
    console.error("downloadCurrentReportPdf failed:", error);
    bannerState(
      `PDF-Export fehlgeschlagen: ${error.message || "Unbekannter Fehler"}`,
      "error"
    );
  }
}

async function runRanking(event) {
  event?.preventDefault();

  const rankingList = $("rankingList");
  const resultsMeta = $("resultsMeta");
  const detailSection = $("detailSection");
  const detailContent = $("detailContent");

  currentDetail = null;

  if (rankingList) rankingList.innerHTML = "";
  if (resultsMeta) resultsMeta.classList.add("hidden");
  if (detailSection) detailSection.classList.add("hidden");
  if (detailContent) detailContent.innerHTML = "";

  currentProfile = buildProfileFromForm();

  const queryField = $("queryText");
  const autoQuery = buildAutoQuery(currentProfile);
  if (queryField && !queryField.value.trim()) {
    queryField.value = autoQuery;
  }
  currentQueryText = queryField?.value?.trim() || autoQuery;

  bannerState("Analyse läuft … Programme werden bewertet.", "neutral");
  showLoading(true);

  const payload = {
    query_text: currentQueryText,
    profile: currentProfile,
    retrieval_k: 5,
    limit: 10,
    include_detail_top_n: 0,
  };

  try {
    const response = await fetch(`${getApiBase()}/rank`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data = null;
    try {
      data = await response.json();
    } catch (_) {
      data = null;
    }

    if (!response.ok) {
      throw new Error(data?.detail || data?.error || `HTTP ${response.status}`);
    }

    currentResults = safeArray(data?.results);
    renderRanking(currentResults);

    if (resultsMeta) {
      const sortText =
        getCurrentSortMode() === "rule_score"
          ? "Rule Score"
          : getCurrentSortMode() === "semantic_score"
          ? "Semantic Score"
          : "Gesamtranking";

      resultsMeta.textContent = `${currentResults.length} Programme bewertet · Sortierung: ${sortText} · Query: ${currentQueryText}`;
      resultsMeta.classList.remove("hidden");
    }

    bannerState("Ranking erfolgreich erzeugt.", "success");
  } catch (error) {
    console.error("runRanking failed:", error);
    bannerState(
      `Analyse fehlgeschlagen: ${error.message || "Unbekannter Fehler"}`,
      "error"
    );
    if (rankingList) {
      rankingList.innerHTML = `
        <div class="error-box">
          <strong>Ranking konnte nicht geladen werden.</strong>
          <div>${escapeHtml(error.message || "Unbekannter Fehler")}</div>
        </div>
      `;
    }
  } finally {
    showLoading(false);
  }
}

async function loadDetail(programId) {
  const detailSection = $("detailSection");
  const detailContent = $("detailContent");
  if (!detailSection || !detailContent) return;

  detailSection.classList.remove("hidden");
  detailContent.innerHTML =
    `<div class="loading-box">Programm-Detailansicht wird geladen …</div>`;

  const payload = {
    program_id: programId,
    query_text: currentQueryText || $("queryText")?.value || "",
    profile: currentProfile || buildProfileFromForm(),
    retrieval_k: 5,
  };

  try {
    const response = await fetch(`${getApiBase()}/detail`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data = null;
    try {
      data = await response.json();
    } catch (_) {
      data = null;
    }

    if (!response.ok) {
      throw new Error(data?.detail || data?.error || `HTTP ${response.status}`);
    }

    currentDetail = data;
    detailContent.innerHTML = buildReportHtml(data);
    detailSection.classList.remove("hidden");
    detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    console.error("loadDetail failed:", error);
    detailContent.innerHTML = `
      <div class="error-box">
        <strong>Detailansicht konnte nicht geladen werden.</strong>
        <div>${escapeHtml(error.message || "Unbekannter Fehler")}</div>
      </div>
    `;
  }
}

function loadExampleScenario() {
  $("branche").value = "it";
  $("mitarbeiterzahl").value = "84";
  $("jahresumsatz").value = "11";
  $("standortBundesland").value = "BW";
  $("unternehmensalter").value = "established";
  $("projektKategorie").value = "digitalisierung";
  $("projektStatus").value = "planned";
  $("deMinimis").value = "unknown";
  $("isRandD").checked = false;
  $("hasTechnicalRisk").checked = false;
  $("needsGuarantee").checked = false;
  $("hasPrimaryEffect").checked = false;
  $("inGrwArea").checked = false;
  $("meetsInvestmentThreshold").checked = false;
  $("excludedSector").checked = false;
  $("queryText").value = "";
}

function handleSortChange() {
  if (!currentResults.length) return;

  renderRanking(currentResults);

  const resultsMeta = $("resultsMeta");
  if (resultsMeta && !resultsMeta.classList.contains("hidden")) {
    const sortText =
      getCurrentSortMode() === "rule_score"
        ? "Rule Score"
        : getCurrentSortMode() === "semantic_score"
        ? "Semantic Score"
        : "Gesamtranking";

    resultsMeta.textContent = `${currentResults.length} Programme bewertet · Sortierung: ${sortText} · Query: ${currentQueryText}`;
  }

  bannerState(
    `Sortierung aktualisiert: ${
      $("sortMode")?.selectedOptions?.[0]?.textContent || "Gesamtranking"
    }.`,
    "neutral"
  );
}

function resetUiState() {
  currentResults = [];
  currentDetail = null;
  currentProfile = null;
  currentQueryText = "";

  bannerState("Noch keine Analyse gestartet.", "neutral");
  $("rankingList").innerHTML = "";
  $("resultsMeta")?.classList.add("hidden");
  $("detailSection")?.classList.add("hidden");

  if ($("detailContent")) $("detailContent").innerHTML = "";
}

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();

  $("healthBtn")?.addEventListener("click", checkHealth);
  $("loadScenarioBtn")?.addEventListener("click", loadExampleScenario);
  $("profileForm")?.addEventListener("submit", runRanking);
  $("sortMode")?.addEventListener("change", handleSortChange);
  $("resetBtn")?.addEventListener("click", resetUiState);
  $("printBtn")?.addEventListener("click", downloadCurrentReportPdf);
});