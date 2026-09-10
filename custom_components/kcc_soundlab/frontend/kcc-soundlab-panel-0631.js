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

const recommendationFor = (confidence, robustness) => {
  if (confidence === "Avoid" || robustness === "Guarded") {
    return {
      level: "Guarded",
      detail: "Safety guard active; consensus cannot recommend this filter",
    };
  }
  if (confidence === "High confidence" && robustness === "Robust") {
    return {
      level: "Recommended",
      detail: "High confidence and reproduced across listening positions",
    };
  }
  if (confidence === "High confidence" && robustness === "Seat-specific") {
    return {
      level: "Seat tune",
      detail: "High confidence for the current listening position, but not across seats",
    };
  }
  if (robustness === "Need evidence") {
    return {
      level: "Review",
      detail: "More repeat or cross-position evidence is needed before recommendation",
    };
  }
  if (robustness === "Unstable") {
    return {
      level: "Review",
      detail: "Repeat or cross-position evidence is mixed or unstable",
    };
  }
  return {
    level: "Review",
    detail: "Confidence is below the recommendation threshold",
  };
};

const recommendationPalette = (level) => {
  if (level === "Recommended") {
    return { border: "#2e6b43", background: "#153320", color: "#9ce5b3" };
  }
  if (level === "Seat tune") {
    return { border: "#31536b", background: "#122938", color: "#b4dcf5" };
  }
  if (level === "Guarded") {
    return { border: "#713b3b", background: "#321818", color: "#ffb0b0" };
  }
  return { border: "#6b5424", background: "#302611", color: "#f1ce78" };
};

const readinessFor = (results) => {
  const active = results.filter((item) => item.active);
  const recommended = active.filter((item) => item.recommendation === "Recommended").length;
  if (!active.length) {
    return {
      level: "No active filters",
      color: "#9fb0bc",
      count: "0 active filters",
      detail: "Select at least one EQ suggestion before opening Apply Preview",
    };
  }
  if (recommended === active.length) {
    return {
      level: "Ready for Apply Preview",
      color: "#9ce5b3",
      count: `${recommended}/${active.length} active recommended`,
      detail: "Every active EQ suggestion is both High confidence and Robust",
    };
  }
  const seatTune = active.filter((item) => item.recommendation === "Seat tune").length;
  const review = active.filter((item) => item.recommendation === "Review").length;
  const guarded = active.filter((item) => item.recommendation === "Guarded").length;
  const reasons = [];
  if (seatTune) reasons.push(`${seatTune} seat tune`);
  if (review) reasons.push(`${review} review`);
  if (guarded) reasons.push(`${guarded} guarded`);
  return {
    level: "Review active set",
    color: "#f1ce78",
    count: `${recommended}/${active.length} active recommended`,
    detail: `Active set also contains ${reasons.join(" and ") || "a non-recommended filter"}`,
  };
};

if (ResponseElement && !ResponseElement.prototype.__kccRecommendedSetReadiness0639) {
  const proto = ResponseElement.prototype;
  proto.__kccRecommendedSetReadiness0639 = true;

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
      note.textContent = "Multi-Position contributes advisory Confidence, Robustness, Recommendation and active-set readiness evidence in v0.6.39. Tap a recommendation badge to see its evidence. Nothing here changes Guards, filter On/Off, Prediction, Apply Preview or SoundLab EQ.";
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

      const recommendation = recommendationFor(level, robustness.level);
      results.push({
        level,
        score,
        robustness: robustness.level,
        recommendation: recommendation.level,
        active: Boolean(item.row.querySelector("[data-assistant-toggle]")?.checked),
      });
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

      let recommendationBadge = item.row.querySelector("[data-eq-recommendation]");
      if (!recommendationBadge) {
        recommendationBadge = document.createElement("span");
        recommendationBadge.dataset.eqRecommendation = "true";
        recommendationBadge.style.display = "inline-block";
        recommendationBadge.style.marginLeft = "6px";
        recommendationBadge.style.marginTop = "4px";
        recommendationBadge.style.padding = "2px 6px";
        recommendationBadge.style.border = "1px solid";
        recommendationBadge.style.borderRadius = "10px";
        recommendationBadge.style.fontSize = "8px";
        robustnessBadge.insertAdjacentElement("afterend", recommendationBadge);
      }
      const recommendationColors = recommendationPalette(recommendation.level);
      recommendationBadge.textContent = recommendation.level;
      recommendationBadge.title = `Consensus recommendation · ${recommendation.detail} · Activate for evidence details`;
      recommendationBadge.setAttribute("role", "button");
      recommendationBadge.setAttribute("tabindex", "0");
      recommendationBadge.setAttribute("aria-label", `${recommendation.level}: ${recommendation.detail}. Activate for evidence details.`);
      recommendationBadge.style.borderColor = recommendationColors.border;
      recommendationBadge.style.background = recommendationColors.background;
      recommendationBadge.style.color = recommendationColors.color;
      recommendationBadge.style.cursor = "pointer";
      recommendationBadge.style.userSelect = "none";

      let recommendationDetail = item.row.querySelector("[data-eq-recommendation-detail]");
      if (!recommendationDetail) {
        recommendationDetail = document.createElement("div");
        recommendationDetail.dataset.eqRecommendationDetail = "true";
        recommendationDetail.hidden = true;
        recommendationDetail.style.marginTop = "6px";
        recommendationDetail.style.maxWidth = "360px";
        recommendationDetail.style.color = "#9fb0bc";
        recommendationDetail.style.fontSize = "9px";
        recommendationDetail.style.lineHeight = "1.4";
        recommendationBadge.insertAdjacentElement("afterend", recommendationDetail);

        const toggleRecommendationDetail = (event) => {
          event.stopPropagation();
          const detail = item.row.querySelector("[data-eq-recommendation-detail]");
          if (!detail) return;
          detail.hidden = !detail.hidden;
          recommendationBadge.setAttribute("aria-expanded", String(!detail.hidden));
        };
        recommendationBadge.addEventListener("click", toggleRecommendationDetail);
        recommendationBadge.addEventListener("keydown", (event) => {
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          toggleRecommendationDetail(event);
        });
      }

      const confidenceDetail = level === "Avoid"
        ? "Confidence: Avoid (guarded)"
        : `Confidence: ${level} ${score}/100`;
      recommendationBadge.setAttribute("aria-expanded", String(!recommendationDetail.hidden));
      recommendationDetail.textContent = `${recommendation.level} — ${recommendation.detail}. ${confidenceDetail}. Robustness: ${robustness.level} — ${robustness.detail}.`;
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
    const recommended = results.filter((item) => item.recommendation === "Recommended").length;
    const seatTune = results.filter((item) => item.recommendation === "Seat tune").length;
    const recommendationReview = results.filter((item) => item.recommendation === "Review").length;
    const recommendationGuarded = results.filter((item) => item.recommendation === "Guarded").length;
    const readiness = readinessFor(results);
    const measurementCount = (this.repeatabilityRepeats || []).length + 1;
    const positionCount = (this.multiPositionContext?.().others?.length || 0) + 1;
    const evidence = [];
    if (repeatComparisons.length) evidence.push(`${measurementCount} same-position measurements`);
    if (positionComparisons.length) evidence.push(`${positionCount} listening positions`);
    summary.innerHTML = `<b style="color:#69b2ff">EQ ASSISTANT CONFIDENCE</b> · <span style="color:#78d39a">${high} high</span> · <span style="color:#e2be67">${review} review</span> · <span style="color:#ef9a9a">${avoid} avoid</span><br><span style="color:#8195a4">Quality weighs smoothing${evidence.length ? `, ${safe(evidence.join(" and "))}` : ""}. Cross-position evidence is advisory; Crossover Guard and Null / Boost Guard remain the only automatic blocks.</span><br><b style="color:#9dc8ea">POSITION ROBUSTNESS</b> · <span style="color:#78d39a">${robust} robust</span> · <span style="color:#9dc8ea">${seatSpecific} seat-specific</span> · <span style="color:#e2be67">${unstable} unstable</span> · <span style="color:#ef9a9a">${guarded} guarded</span>${needEvidence ? ` · <span style="color:#8195a4">${needEvidence} need evidence</span>` : ""}<br><b style="color:#b4dcf5">CONSENSUS RECOMMENDATION</b> · <span style="color:#9ce5b3">${recommended} recommended</span> · <span style="color:#b4dcf5">${seatTune} seat tune</span> · <span style="color:#f1ce78">${recommendationReview} review</span> · <span style="color:#ffb0b0">${recommendationGuarded} guarded</span><br><span style="color:#8195a4">Recommendation combines Confidence and Robustness as guidance only. Tap a recommendation badge to see why; it never changes filter On/Off or Apply eligibility.</span><br><b style="color:#d2e4ef">ACTIVE SET READINESS</b> · <span style="color:${readiness.color}">${safe(readiness.level)}</span> · <span style="color:#9fb0bc">${safe(readiness.count)}</span><br><span style="color:#8195a4">${safe(readiness.detail)}. Readiness is advisory and does not bypass Apply Preview, free-slot, snapshot or Restore safeguards.</span>`;
  };
}
