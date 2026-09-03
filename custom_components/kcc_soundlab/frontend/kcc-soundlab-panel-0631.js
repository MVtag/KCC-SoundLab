import "./kcc-soundlab-panel-0634-base.js?v=0.6.1";

const RESPONSE_TAG = "kcc-measurement-response-0622";
const ResponseElement = customElements.get(RESPONSE_TAG);
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const safe = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[char]));
const signed = (value) => `${value > 0 ? "+" : ""}${value}`;

const repeatabilityAdjustment = (evidence) => {
  if (!evidence?.total) return 0;
  const ratio = evidence.matches / evidence.total;
  if (evidence.total >= 2 && evidence.matches === evidence.total) return 12;
  if (ratio >= 0.75) return 8;
  if (ratio >= 0.5) return 3;
  if (evidence.matches === 0) return -15;
  return -8;
};

const positionAdjustment = (evidence) => {
  if (!evidence?.total) return 0;
  const ratio = evidence.matches / evidence.total;
  if (evidence.total >= 2 && evidence.matches === evidence.total) return 10;
  if (evidence.matches === evidence.total) return 6;
  if (ratio >= 0.75) return 7;
  if (ratio >= 0.5) return 3;
  if (evidence.matches === 0) return -12;
  return -6;
};

if (ResponseElement && !ResponseElement.prototype.__kccCrossPositionConfidence0635) {
  const proto = ResponseElement.prototype;
  proto.__kccCrossPositionConfidence0635 = true;

  const baseInjectMultiPosition = proto.injectMultiPosition;

  proto.injectMultiPosition = function injectMultiPosition(...args) {
    const result = baseInjectMultiPosition?.apply(this, args);
    const card = this.querySelector("[data-multi-position-evidence]");
    if (!card) return result;
    const heading = card.querySelector(".difference-head small");
    if (heading) heading.textContent = "MULTI-POSITION CONFIDENCE EVIDENCE · READ ONLY";
    const notes = [...card.querySelectorAll(".muted-copy")];
    const note = notes.at(-1);
    if (note) {
      note.textContent = "Multi-Position contributes advisory Confidence evidence in v0.6.35. It never changes Guards, filter On/Off, Prediction, Apply Preview or SoundLab EQ.";
    }
    return result;
  };

  proto.decorateConfidenceRepeatability = function decorateConfidenceEvidence() {
    if (!this.response || !this.confidenceRows || !this.confidenceFor) return;

    const rows = this.confidenceRows();
    const smoothingSets = this.confidenceSmoothingSets?.() || [];
    const repeatComparisons = this.repeatabilityComparisons?.() || [];
    const positionComparisons = this.multiPositionComparisons?.() || [];
    if (!repeatComparisons.length && !positionComparisons.length) return;

    const results = [];
    for (const item of rows) {
      const base = this.confidenceFor(item, smoothingSets);
      const repeat = this.repeatabilityFeatureMatches?.(item, repeatComparisons)
        || { matches: 0, total: 0 };
      const position = this.multiPositionFeatureMatches?.(item, positionComparisons)
        || { matches: 0, total: 0 };
      const repeatDelta = base.level === "Avoid" ? 0 : repeatabilityAdjustment(repeat);
      const positionDelta = base.level === "Avoid" ? 0 : positionAdjustment(position);
      let score = base.score;
      let level = base.level;

      if (base.level !== "Avoid") {
        score = Math.round(clamp(score + repeatDelta + positionDelta, 0, 100));
        level = score >= 75 ? "High confidence" : "Review";
      }

      results.push({ level, score });
      const badge = item.row.querySelector("[data-eq-confidence]");
      if (!badge) continue;
      const palette = level === "High confidence"
        ? { border: "#2e6b43", background: "#10251a", color: "#78d39a" }
        : level === "Avoid"
          ? { border: "#713b3b", background: "#281313", color: "#ef9a9a" }
          : { border: "#6b5424", background: "#241d0d", color: "#e2be67" };
      badge.textContent = level === "Avoid" ? "Avoid · guarded" : `${level} · ${score}/100`;
      const reasons = [
        ...(Array.isArray(base.reasons) ? base.reasons : []),
        `smoothing repeatability ${base.matches}/3`,
      ];
      if (repeat.total) {
        reasons.push(`measurement repeatability ${repeat.matches}/${repeat.total} (${signed(repeatDelta)})`);
      }
      if (position.total) {
        reasons.push(`cross-position ${position.matches}/${position.total} (${signed(positionDelta)})`);
      }
      badge.title = reasons.join(" · ");
      badge.style.borderColor = palette.border;
      badge.style.background = palette.background;
      badge.style.color = palette.color;
    }

    const summary = this.querySelector("[data-eq-confidence-summary]");
    if (!summary) return;
    const high = results.filter((item) => item.level === "High confidence").length;
    const review = results.filter((item) => item.level === "Review").length;
    const avoid = results.filter((item) => item.level === "Avoid").length;
    const measurementCount = (this.repeatabilityRepeats || []).length + 1;
    const positionCount = (this.multiPositionContext?.().others?.length || 0) + 1;
    const evidence = [];
    if (repeatComparisons.length) evidence.push(`${measurementCount} same-position measurements`);
    if (positionComparisons.length) evidence.push(`${positionCount} listening positions`);
    summary.innerHTML = `<b style="color:#69b2ff">EQ ASSISTANT CONFIDENCE</b> · <span style="color:#78d39a">${high} high</span> · <span style="color:#e2be67">${review} review</span> · <span style="color:#ef9a9a">${avoid} avoid</span><br><span style="color:#8195a4">Quality weighs smoothing${evidence.length ? `, ${safe(evidence.join(" and "))}` : ""}. Cross-position evidence is advisory; Crossover Guard and Null / Boost Guard remain the only automatic blocks.</span>`;
  };
}
