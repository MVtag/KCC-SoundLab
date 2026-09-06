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

const evidenceRatio = (evidence) => (
  evidence?.total ? evidence.matches / evidence.total : null
);

const robustnessFor = (baseLevel, repeat, position) => {
  if (baseLevel === "Avoid") {
    return {
      level: "Guarded",
      detail: "Safety guard active; consensus cannot promote this filter",
    };
  }

  const repeatRatio = evidenceRatio(repeat);
  const positionRatio = evidenceRatio(position);

  if (repeatRatio == null && positionRatio == null) {
    return {
      level: "Need evidence",
      detail: "No same-position repeat or cross-position evidence yet",
    };
  }

  if (repeatRatio != null && repeatRatio < 0.5) {
    return {
      level: "Unstable",
      detail: `Same-position repeat agreement ${repeat.matches}/${repeat.total}`,
    };
  }

  if (positionRatio != null && positionRatio >= 0.75) {
    return {
      level: "Robust",
      detail: `Cross-position agreement ${position.matches}/${position.total}${repeatRatio == null ? "" : ` · repeats ${repeat.matches}/${repeat.total}`}`,
    };
  }

  if (positionRatio != null && positionRatio < 0.5) {
    return {
      level: "Seat-specific",
      detail: `Feature is not reproduced across positions (${position.matches}/${position.total})`,
    };
  }

  if (positionRatio == null && repeatRatio != null && repeatRatio >= 0.75) {
    return {
      level: "Seat-specific",
      detail: `Stable at this mic position (${repeat.matches}/${repeat.total} repeats), but no cross-position evidence yet`,
    };
  }

  return {
    level: "Unstable",
    detail: `Mixed evidence${repeatRatio == null ? "" : ` · repeats ${repeat.matches}/${repeat.total}`}${positionRatio == null ? "" : ` · positions ${position.matches}/${position.total}`}`,
  };
};

const robustnessPalette = (level) => {
  if (level === "Robust") {
    return { border: "#2e6b43", background: "#10251a", color: "#78d39a" };
  }
  if (level === "Seat-specific") {
    return { border: "#31536b", background: "#0e1d28", color: "#9dc8ea" };
  }
  if (level === "Guarded") {
    return { border: "#713b3b", background: "#281313", color: "#ef9a9a" };
  }
  return { border: "#6b5424", background: "#241d0d", color: "#e2be67" };
};

if (ResponseElement && !ResponseElement.prototype.__kccPositionRobustness0636) {
  const proto = ResponseElement.prototype;
  proto.__kccPositionRobustness0636 = true;

  const baseInjectMultiPosition = proto.injectMultiPosition;

  proto.injectMultiPosition = function injectMultiPosition(...args) {
    const result = baseInjectMultiPosition?.apply(this, args);
    const card = this.querySelector("[data-multi-position-evidence]");
    if (!card) return result;
    const heading = card.querySelector(".difference-head small");
    if (heading) heading.textContent = "MULTI-POSITION CONSENSUS EVIDENCE · READ ONLY";
    const notes = [...card.querySelectorAll(".muted-copy")];
    const note = notes.at(-1);
    if (note) {
      note.textContent = "Multi-Position contributes advisory Confidence and Robustness evidence in v0.6.36. It never changes Guards, filter On/Off, Prediction, Apply Preview or SoundLab EQ.";
    }
    return result;
  };

  proto.decorateConfidenceRepeatability = function decorateConfidenceEvidence() {
    if (!this.response || !this.confidenceRows || !this.confidenceFor) return;

    const rows = this.confidenceRows();
    const smoothingSets = this.confidenceSmoothingSets?.() || [];
    const repeatComparisons = this.repeatabilityComparisons?.() || [];
    const positionComparisons = this.multiPositionComparisons?.() || [];
    const results = [];

    for (const item of rows) {
      const base = this.confidenceFor(item, smoothingSets);
      const repeat = this.repeatabilityFeatureMatches?.(item, repeatComparisons)
        || { matches: 0, total: 0 };
      const position = this.multiPositionFeatureMatches?.(item, positionComparisons)
        || { matches: 0, total: 0 };
      const repeatDelta = base.level === "Avoid" ? 0 : repeatabilityAdjustment(repeat);
      const positionDelta = base.level === "Avoid" ? 0 : positionAdjustment(position);
      const robustness = robustnessFor(base.level, repeat, position);
      let score = base.score;
      let level = base.level;

      if (base.level !== "Avoid") {
        score = Math.round(clamp(score + repeatDelta + positionDelta, 0, 100));
        level = score >= 75 ? "High confidence" : "Review";
      }

      results.push({ level, score, robustness: robustness.level });
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

      let robustnessBadge = item.row.querySelector("[data-eq-robustness]");
      if (!robustnessBadge) {
        robustnessBadge = document.createElement("span");
        robustnessBadge.dataset.eqRobustness = "true";
        robustnessBadge.style.display = "inline-block";
        robustnessBadge.style.marginLeft = "6px";
        robustnessBadge.style.marginTop = "4px";
        robustnessBadge.style.padding = "2px 6px";
        robustnessBadge.style.border = "1px solid";
        robustnessBadge.style.borderRadius = "10px";
        robustnessBadge.style.fontSize = "8px";
        badge.insertAdjacentElement("afterend", robustnessBadge);
      }
      const robustPalette = robustnessPalette(robustness.level);
      robustnessBadge.textContent = robustness.level;
      robustnessBadge.title = robustness.detail;
      robustnessBadge.style.borderColor = robustPalette.border;
      robustnessBadge.style.background = robustPalette.background;
      robustnessBadge.style.color = robustPalette.color;
    }

    const summary = this.querySelector("[data-eq-confidence-summary]");
    if (!summary) return;
    const high = results.filter((item) => item.level === "High confidence").length;
    const review = results.filter((item) => item.level === "Review").length;
    const avoid = results.filter((item) => item.level === "Avoid").length;
    const robust = results.filter((item) => item.robustness === "Robust").length;
    const seatSpecific = results.filter((item) => item.robustness === "Seat-specific").length;
    const unstable = results.filter((item) => item.robustness === "Unstable").length;
    const guarded = results.filter((item) => item.robustness === "Guarded").length;
    const needEvidence = results.filter((item) => item.robustness === "Need evidence").length;
    const measurementCount = (this.repeatabilityRepeats || []).length + 1;
    const positionCount = (this.multiPositionContext?.().others?.length || 0) + 1;
    const evidence = [];
    if (repeatComparisons.length) evidence.push(`${measurementCount} same-position measurements`);
    if (positionComparisons.length) evidence.push(`${positionCount} listening positions`);
    summary.innerHTML = `<b style="color:#69b2ff">EQ ASSISTANT CONFIDENCE</b> · <span style="color:#78d39a">${high} high</span> · <span style="color:#e2be67">${review} review</span> · <span style="color:#ef9a9a">${avoid} avoid</span><br><span style="color:#8195a4">Quality weighs smoothing${evidence.length ? `, ${safe(evidence.join(" and "))}` : ""}. Cross-position evidence is advisory; Crossover Guard and Null / Boost Guard remain the only automatic blocks.</span><br><b style="color:#9dc8ea">POSITION ROBUSTNESS</b> · <span style="color:#78d39a">${robust} robust</span> · <span style="color:#9dc8ea">${seatSpecific} seat-specific</span> · <span style="color:#e2be67">${unstable} unstable</span> · <span style="color:#ef9a9a">${guarded} guarded</span>${needEvidence ? ` · <span style="color:#8195a4">${needEvidence} need evidence</span>` : ""}<br><span style="color:#8195a4">Robustness is consensus guidance only and never changes filter On/Off or Apply eligibility.</span>`;
  };
}
