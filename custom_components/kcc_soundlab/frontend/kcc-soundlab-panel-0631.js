import "./kcc-soundlab-panel-0629.js?v=0.6.1";

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
const fmtDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value || "—") : date.toLocaleString();
};
const median = (values) => {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
};
const smoothingFraction = (id) => ({
  raw: 0,
  "1/24": 24,
  "1/12": 12,
  "1/6": 6,
}[String(id || "raw")] ?? 0);

const targetValue = (points, frequency) => {
  if (!points?.length) return 0;
  const sorted = [...points].sort(
    (a, b) => Number(a.frequency_hz) - Number(b.frequency_hz),
  );
  if (frequency <= Number(sorted[0].frequency_hz)) return Number(sorted[0].gain_db) || 0;
  if (frequency >= Number(sorted.at(-1).frequency_hz)) return Number(sorted.at(-1).gain_db) || 0;
  for (let index = 0; index < sorted.length - 1; index += 1) {
    const left = sorted[index];
    const right = sorted[index + 1];
    const leftFrequency = Number(left.frequency_hz);
    const rightFrequency = Number(right.frequency_hz);
    if (frequency < leftFrequency || frequency > rightFrequency) continue;
    const position = (Math.log(frequency) - Math.log(leftFrequency))
      / (Math.log(rightFrequency) - Math.log(leftFrequency));
    return (Number(left.gain_db) || 0)
      + ((Number(right.gain_db) || 0) - (Number(left.gain_db) || 0)) * position;
  }
  return 0;
};

const smoothPoints = (points, fraction) => {
  const source = (points || [])
    .map((point) => ({
      frequency_hz: Number(point.frequency_hz),
      spl_db: Number(point.spl_db),
    }))
    .filter((point) => Number.isFinite(point.frequency_hz) && Number.isFinite(point.spl_db));
  if (!fraction || source.length < 3) return source;
  const sigma = 1 / (2 * fraction);
  const radius = sigma * 3;
  return source.map((point) => {
    let weighted = 0;
    let total = 0;
    for (const candidate of source) {
      const distance = Math.abs(Math.log2(candidate.frequency_hz / point.frequency_hz));
      if (distance > radius) continue;
      const weight = Math.exp(-0.5 * Math.pow(distance / sigma, 2));
      weighted += candidate.spl_db * weight;
      total += weight;
    }
    return {
      frequency_hz: point.frequency_hz,
      spl_db: total ? weighted / total : point.spl_db,
    };
  });
};

const comparisonFor = (response, target, smoothing) => {
  const points = smoothPoints(response?.points || [], smoothingFraction(smoothing));
  const curve = target?.points || [];
  if (!points.length) return [];
  const offsets = points.map((point) => ({
    frequency: point.frequency_hz,
    value: point.spl_db - targetValue(curve, point.frequency_hz),
  }));
  const referencePool = offsets
    .filter((item) => item.frequency >= 500 && item.frequency <= 2000)
    .map((item) => item.value);
  const reference = median(referencePool.length ? referencePool : offsets.map((item) => item.value));
  return points.map((point) => ({
    frequency_hz: point.frequency_hz,
    delta_db: (point.spl_db - reference) - targetValue(curve, point.frequency_hz),
  }));
};

const interpolate = (points, frequency) => {
  if (!points?.length) return null;
  if (frequency <= points[0].frequency_hz) return Number(points[0].delta_db);
  if (frequency >= points.at(-1).frequency_hz) return Number(points.at(-1).delta_db);
  for (let index = 0; index < points.length - 1; index += 1) {
    const left = points[index];
    const right = points[index + 1];
    if (frequency < left.frequency_hz || frequency > right.frequency_hz) continue;
    const position = (Math.log(frequency) - Math.log(left.frequency_hz))
      / (Math.log(right.frequency_hz) - Math.log(left.frequency_hz));
    return Number(left.delta_db)
      + (Number(right.delta_db) - Number(left.delta_db)) * position;
  }
  return null;
};

const downsample = (points, maxPoints = 256) => {
  if (points.length <= maxPoints) return points;
  const first = points[0].frequency_hz;
  const last = points.at(-1).frequency_hz;
  const low = Math.log(first);
  const high = Math.log(last);
  const result = [];
  const used = new Set();
  let cursor = 0;
  for (let index = 0; index < maxPoints; index += 1) {
    const wanted = Math.exp(low + ((high - low) * index) / (maxPoints - 1));
    while (
      cursor + 1 < points.length
      && Math.abs(Math.log(points[cursor + 1].frequency_hz) - Math.log(wanted))
        <= Math.abs(Math.log(points[cursor].frequency_hz) - Math.log(wanted))
    ) cursor += 1;
    const point = points[cursor];
    const key = point.frequency_hz.toFixed(3);
    if (!used.has(key)) {
      used.add(key);
      result.push(point);
    }
  }
  return result;
};

const parseRepeatFile = (text) => {
  const raw = [];
  for (const line of String(text || "").split(/\r?\n/)) {
    const values = line.trim().split(/[,;\t ]+/).filter(Boolean);
    if (values.length < 2) continue;
    const frequency = Number(values[0]);
    const spl = Number(values[1]);
    if (
      !Number.isFinite(frequency)
      || !Number.isFinite(spl)
      || frequency < 20
      || frequency > 20000
      || spl < -200
      || spl > 200
    ) continue;
    raw.push({ frequency_hz: frequency, spl_db: spl });
  }
  raw.sort((a, b) => a.frequency_hz - b.frequency_hz);
  const unique = [];
  for (const point of raw) {
    if (unique.length && Math.abs(point.frequency_hz - unique.at(-1).frequency_hz) < 0.001) {
      unique[unique.length - 1] = point;
    } else unique.push(point);
  }
  if (unique.length < 5) {
    throw new Error("No usable REW frequency response found. Export frequency + SPL as text.");
  }
  return { originalCount: unique.length, points: downsample(unique) };
};

if (ResponseElement && !ResponseElement.prototype.__kccMeasurementEvidence0634) {
  const proto = ResponseElement.prototype;
  proto.__kccMeasurementEvidence0634 = true;

  const baseConnected = proto.connectedCallback;
  const baseLoad = proto.load;
  const baseRender = proto.render;
  const baseClick = proto.onClick;
  const baseChange = proto.onChange;
  const baseImportFile = proto.importFile;
  const baseClear = proto.clear;

  const resetEvidenceState = function resetEvidenceState() {
    this.repeatabilityRepeats = [];
    this.repeatabilityMax = 4;
    this.repeatabilityBusy = false;
    this.repeatabilityMessage = "";
    this.repeatabilityError = "";
    this.multiPositionMeasurements = [];
    this.multiPositionError = "";
  };

  proto.connectedCallback = function connectedCallback(...args) {
    resetEvidenceState.call(this);
    return baseConnected?.apply(this, args);
  };

  proto.loadRepeatability = async function loadRepeatability() {
    const panel = this.panel();
    const session = this.sessionId();
    const channel = this.selectedChannel();
    if (!panel?.send || !session) {
      this.repeatabilityRepeats = [];
      return;
    }
    try {
      const data = await panel.send("kcc_soundlab/get_frequency_response_repeats", {
        session_id: session,
        channel,
      });
      this.repeatabilityRepeats = Array.isArray(data?.repeats) ? data.repeats : [];
      this.repeatabilityMax = Number(data?.max_repeats) || 4;
      this.repeatabilityError = "";
    } catch (error) {
      this.repeatabilityRepeats = [];
      this.repeatabilityError = String(error?.message || error);
    }
  };

  proto.loadMultiPosition = async function loadMultiPosition() {
    const panel = this.panel();
    const channel = this.selectedChannel();
    if (!panel?.send) {
      this.multiPositionMeasurements = [];
      return;
    }
    try {
      const data = await panel.send("kcc_soundlab/get_multi_position_responses", { channel });
      this.multiPositionMeasurements = Array.isArray(data?.measurements) ? data.measurements : [];
      this.multiPositionError = "";
    } catch (error) {
      this.multiPositionMeasurements = [];
      this.multiPositionError = String(error?.message || error);
    }
  };

  proto.loadEvidence = async function loadEvidence() {
    await Promise.all([this.loadRepeatability(), this.loadMultiPosition()]);
    this.render();
  };

  proto.load = async function load(...args) {
    this.repeatabilityRepeats = [];
    this.repeatabilityMessage = "";
    this.repeatabilityError = "";
    this.multiPositionMeasurements = [];
    this.multiPositionError = "";
    const result = await baseLoad.apply(this, args);
    await this.loadEvidence();
    return result;
  };

  proto.importFile = async function importFile(file) {
    const result = await baseImportFile.call(this, file);
    await this.loadMultiPosition();
    this.render();
    return result;
  };

  proto.clear = async function clear() {
    const result = await baseClear.call(this);
    await this.loadMultiPosition();
    this.render();
    return result;
  };

  proto.repeatabilityComparisons = function repeatabilityComparisons() {
    const target = this.panel()?.workspace?.target_curve || { points: [] };
    const smoothing = this.selectedSmoothing?.() || "raw";
    return (this.repeatabilityRepeats || [])
      .map((sample) => comparisonFor(sample, target, smoothing))
      .filter((points) => points.length);
  };

  proto.repeatabilityStats = function repeatabilityStats() {
    const target = this.panel()?.workspace?.target_curve || { points: [] };
    const smoothing = this.selectedSmoothing?.() || "raw";
    const primary = comparisonFor(this.response, target, smoothing);
    const repeats = this.repeatabilityComparisons();
    if (!primary.length || !repeats.length) {
      return { meanSpread: null, within15: null, grade: "Need repeats" };
    }
    const errors = [];
    for (const repeat of repeats) {
      for (const point of primary) {
        const other = interpolate(repeat, point.frequency_hz);
        if (Number.isFinite(other)) errors.push(Math.abs(other - point.delta_db));
      }
    }
    if (!errors.length) return { meanSpread: null, within15: null, grade: "Need repeats" };
    const meanSpread = errors.reduce((sum, value) => sum + value, 0) / errors.length;
    const within15 = (errors.filter((value) => value <= 1.5).length / errors.length) * 100;
    const grade = meanSpread <= 1 && within15 >= 80
      ? "Strong"
      : meanSpread <= 1.5 && within15 >= 65
        ? "Good"
        : "Review";
    return { meanSpread, within15, grade };
  };

  proto.repeatabilityFeatureMatches = function repeatabilityFeatureMatches(
    item,
    comparisons = this.repeatabilityComparisons(),
  ) {
    const wantedSign = item.originalGain < 0 ? 1 : -1;
    const frequency = Number(item.originalFrequency || item.frequency);
    let matches = 0;
    for (const points of comparisons) {
      const found = points.some((point) => (
        Math.abs(Math.log2(point.frequency_hz / frequency)) <= 0.25
        && Math.sign(point.delta_db) === wantedSign
        && Math.abs(point.delta_db) >= 1.5
      ));
      if (found) matches += 1;
    }
    return { matches, total: comparisons.length };
  };

  proto.decorateConfidenceRepeatability = function decorateConfidenceRepeatability() {
    if (
      !this.response
      || !(this.repeatabilityRepeats || []).length
      || !this.confidenceRows
      || !this.confidenceFor
    ) return;

    const rows = this.confidenceRows();
    const smoothingSets = this.confidenceSmoothingSets?.() || [];
    const comparisons = this.repeatabilityComparisons();
    const results = [];

    for (const item of rows) {
      const base = this.confidenceFor(item, smoothingSets);
      const repeat = this.repeatabilityFeatureMatches(item, comparisons);
      let score = base.score;
      let level = base.level;

      if (base.level !== "Avoid" && repeat.total) {
        const ratio = repeat.matches / repeat.total;
        if (repeat.total >= 2 && repeat.matches === repeat.total) score += 12;
        else if (ratio >= 0.75) score += 8;
        else if (ratio >= 0.5) score += 3;
        else if (repeat.matches === 0) score -= 15;
        else score -= 8;
        score = Math.round(clamp(score, 0, 100));
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
      badge.title = `${base.reasons.join(" · ")} · smoothing repeatability ${base.matches}/3 · measurement repeatability ${repeat.matches}/${repeat.total}`;
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
    summary.innerHTML = `<b style="color:#69b2ff">EQ ASSISTANT CONFIDENCE</b> · <span style="color:#78d39a">${high} high</span> · <span style="color:#e2be67">${review} review</span> · <span style="color:#ef9a9a">${avoid} avoid</span><br><span style="color:#8195a4">Quality also weighs feature agreement across ${safe(measurementCount)} stored measurements. Measurement repeatability is advisory; Crossover Guard and Null / Boost Guard remain the only automatic blocks.</span>`;
  };

  proto.injectRepeatability = function injectRepeatability() {
    const host = this.querySelector(".response-card");
    if (!host || !this.response) return;

    const repeats = this.repeatabilityRepeats || [];
    const stats = this.repeatabilityStats();
    const comparisons = this.repeatabilityComparisons();
    const confidenceRows = this.confidenceRows?.() || [];
    const heading = repeats.length
      ? `${repeats.length + 1} measurements compared`
      : "Add repeat REW measurements";

    const featureChips = confidenceRows.length && repeats.length
      ? confidenceRows.map((item) => {
        const result = this.repeatabilityFeatureMatches(item, comparisons);
        const color = result.total && result.matches === result.total
          ? "#78d39a"
          : result.matches
            ? "#e2be67"
            : "#ef9a9a";
        return `<span style="border:1px solid #30485c;border-radius:10px;padding:4px 7px;color:${color}">${Math.round(item.originalFrequency)} Hz · ${result.matches}/${result.total} repeats</span>`;
      }).join("")
      : "";

    const repeatRows = repeats.map((sample) => `
      <div style="display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;border-top:1px solid #21323d;padding:8px 0">
        <div>
          <b>${safe(sample.source_name)}</b>
          <small style="display:block;color:#788b99">${safe(sample.point_count)} stored points · ${safe(fmtDate(sample.imported_at))}</small>
        </div>
        <button type="button" class="danger-btn" data-repeatability-delete="${safe(sample.id)}" ${this.repeatabilityBusy ? "disabled" : ""}>Remove</button>
      </div>
    `).join("");

    const message = this.repeatabilityError
      ? `<div style="border:1px solid #713b3b;background:#281313;color:#ef9a9a;border-radius:8px;padding:9px;margin-top:10px">${safe(this.repeatabilityError)}</div>`
      : this.repeatabilityMessage
        ? `<div style="border:1px solid #28503a;background:#0d2118;color:#78d39a;border-radius:8px;padding:9px;margin-top:10px">${safe(this.repeatabilityMessage)}</div>`
        : "";

    const card = document.createElement("div");
    card.className = "difference-panel";
    card.dataset.measurementRepeatability = "true";
    card.style.borderColor = "#31536b";
    card.innerHTML = `
      <div class="difference-head">
        <div><small>MEASUREMENT REPEATABILITY</small><strong>${heading}</strong></div>
        <span>Same output · same mic position</span>
      </div>
      <div class="response-stats">
        <div><small>MEASUREMENTS</small><strong>${repeats.length + 1}</strong><span>1 primary + ${repeats.length} repeats</span></div>
        <div><small>MEAN SPREAD</small><strong>${stats.meanSpread == null ? "—" : `${stats.meanSpread.toFixed(1)} dB`}</strong><span>Repeat vs primary</span></div>
        <div><small>WITHIN ±1.5 dB</small><strong>${stats.within15 == null ? "—" : `${stats.within15.toFixed(0)}%`}</strong><span>Compared points</span></div>
        <div><small>AGREEMENT</small><strong>${safe(stats.grade)}</strong><span>Advisory evidence</span></div>
      </div>
      ${featureChips ? `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;font-size:8px">${featureChips}</div>` : ""}
      <div style="margin-top:10px">
        <div><b>Primary:</b> ${safe(this.response.source_name || "REW response")}</div>
        ${repeatRows || '<p class="muted-copy">Import the same output again without moving the microphone or changing level/setup. SoundLab will compare the Difference Curve shape and use it as extra Confidence evidence.</p>'}
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px">
        <label class="primary response-file" style="${repeats.length >= this.repeatabilityMax || this.repeatabilityBusy ? "opacity:.45;pointer-events:none" : ""}">
          ${this.repeatabilityBusy ? "Importing…" : "Add repeat REW measurement"}
          <input data-repeatability-file type="file" accept=".txt,.frd,.dat,text/plain" multiple ${repeats.length >= this.repeatabilityMax || this.repeatabilityBusy ? "disabled" : ""}>
        </label>
        <span style="color:#788b99;font-size:8px">${repeats.length}/${this.repeatabilityMax} repeat slots used</span>
      </div>
      ${message}
      <p class="muted-copy" style="margin-top:10px">Repeat measurements never replace the primary response and never write EQ. They only add repeatability evidence to analysis and Confidence.</p>
    `;

    const controlledApply = [...host.querySelectorAll(".difference-panel")]
      .find((panel) => panel.querySelector("[data-eq-assistant-apply]"));
    const meta = host.querySelector(".response-meta");
    if (controlledApply) controlledApply.before(card);
    else if (meta) meta.before(card);
    else host.append(card);
  };

  proto.multiPositionContext = function multiPositionContext() {
    const sessionId = this.sessionId();
    const all = this.multiPositionMeasurements || [];
    const current = all.find((item) => String(item.session_id) === sessionId);
    const fallback = this.panel()?.workspace?.measurement_sessions?.find?.(
      (item) => String(item.id) === sessionId,
    );
    const position = String(current?.position || fallback?.position || "Driver seat");
    const byPosition = new Map();

    for (const item of all) {
      const itemSession = String(item.session_id || "");
      const itemPosition = String(item.position || "Other");
      if (itemSession === sessionId || itemPosition === position) continue;
      const existing = byPosition.get(itemPosition);
      const existingTime = existing ? new Date(existing.created_at || 0).getTime() : -Infinity;
      const candidateTime = new Date(item.created_at || 0).getTime();
      if (!existing || candidateTime >= existingTime) byPosition.set(itemPosition, item);
    }

    return { position, others: [...byPosition.values()] };
  };

  proto.multiPositionComparisons = function multiPositionComparisons() {
    const target = this.panel()?.workspace?.target_curve || { points: [] };
    const smoothing = this.selectedSmoothing?.() || "raw";
    return this.multiPositionContext().others
      .map((item) => ({ item, points: comparisonFor(item.response, target, smoothing) }))
      .filter((entry) => entry.points.length);
  };

  proto.multiPositionStats = function multiPositionStats() {
    const target = this.panel()?.workspace?.target_curve || { points: [] };
    const smoothing = this.selectedSmoothing?.() || "raw";
    const primary = comparisonFor(this.response, target, smoothing);
    const others = this.multiPositionComparisons();
    if (!primary.length || !others.length) {
      return { meanSpread: null, within15: null, grade: "Need another position" };
    }
    const errors = [];
    for (const entry of others) {
      for (const point of primary) {
        const other = interpolate(entry.points, point.frequency_hz);
        if (Number.isFinite(other)) errors.push(Math.abs(other - point.delta_db));
      }
    }
    if (!errors.length) {
      return { meanSpread: null, within15: null, grade: "Need another position" };
    }
    const meanSpread = errors.reduce((sum, value) => sum + value, 0) / errors.length;
    const within15 = (errors.filter((value) => value <= 1.5).length / errors.length) * 100;
    const grade = meanSpread <= 1 && within15 >= 80
      ? "Strong"
      : meanSpread <= 1.5 && within15 >= 65
        ? "Good"
        : "Review";
    return { meanSpread, within15, grade };
  };

  proto.multiPositionFeatureMatches = function multiPositionFeatureMatches(
    item,
    comparisons = this.multiPositionComparisons(),
  ) {
    const wantedSign = item.originalGain < 0 ? 1 : -1;
    const frequency = Number(item.originalFrequency || item.frequency);
    let matches = 0;
    for (const entry of comparisons) {
      const found = entry.points.some((point) => (
        Math.abs(Math.log2(point.frequency_hz / frequency)) <= 0.25
        && Math.sign(point.delta_db) === wantedSign
        && Math.abs(point.delta_db) >= 1.5
      ));
      if (found) matches += 1;
    }
    return { matches, total: comparisons.length };
  };

  proto.injectMultiPosition = function injectMultiPosition() {
    const host = this.querySelector(".response-card");
    if (!host || !this.response) return;

    const context = this.multiPositionContext();
    const comparisons = this.multiPositionComparisons();
    const stats = this.multiPositionStats();
    const confidenceRows = this.confidenceRows?.() || [];
    const positionCount = context.others.length + 1;
    const heading = context.others.length
      ? `${positionCount} positions compared`
      : "Add another measurement position";

    const featureChips = confidenceRows.length && context.others.length
      ? confidenceRows.map((item) => {
        const result = this.multiPositionFeatureMatches(item, comparisons);
        const color = result.total && result.matches === result.total
          ? "#78d39a"
          : result.matches
            ? "#e2be67"
            : "#ef9a9a";
        return `<span style="border:1px solid #30485c;border-radius:10px;padding:4px 7px;color:${color}">${Math.round(item.originalFrequency)} Hz · ${result.matches}/${result.total} positions</span>`;
      }).join("")
      : "";

    const positionRows = context.others.map((item) => `
      <div style="display:grid;grid-template-columns:120px 1fr auto;gap:10px;align-items:center;border-top:1px solid #21323d;padding:8px 0">
        <b style="color:#9dc8ea">${safe(item.position)}</b>
        <span>${safe(item.session_name)}<small style="display:block;color:#788b99">${safe(item.response?.source_name || "REW response")}</small></span>
        <span style="color:#788b99">${Number(item.repeat_count) || 0} repeats</span>
      </div>
    `).join("");

    const error = this.multiPositionError
      ? `<div style="border:1px solid #713b3b;background:#281313;color:#ef9a9a;border-radius:8px;padding:9px;margin-top:10px">${safe(this.multiPositionError)}</div>`
      : "";

    const card = document.createElement("div");
    card.className = "difference-panel";
    card.dataset.multiPositionEvidence = "true";
    card.style.borderColor = "#3e4f74";
    card.innerHTML = `
      <div class="difference-head">
        <div><small>MULTI-POSITION FOUNDATION · READ ONLY</small><strong>${heading}</strong></div>
        <span>Current: ${safe(context.position)}</span>
      </div>
      <div class="response-stats">
        <div><small>POSITIONS</small><strong>${positionCount}</strong><span>Current + ${context.others.length} other</span></div>
        <div><small>MEAN SPREAD</small><strong>${stats.meanSpread == null ? "—" : `${stats.meanSpread.toFixed(1)} dB`}</strong><span>Other positions vs current</span></div>
        <div><small>WITHIN ±1.5 dB</small><strong>${stats.within15 == null ? "—" : `${stats.within15.toFixed(0)}%`}</strong><span>Cross-position points</span></div>
        <div><small>AGREEMENT</small><strong>${safe(stats.grade)}</strong><span>Read-only evidence</span></div>
      </div>
      ${featureChips ? `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;font-size:8px">${featureChips}</div>` : ""}
      <div style="margin-top:10px">
        ${positionRows || '<p class="muted-copy">Create another Measurement session with a different listening position and import a primary REW response for the same output. Same-position repeats stay in Measurement Repeatability.</p>'}
      </div>
      ${error}
      <p class="muted-copy" style="margin-top:10px">Multi-Position is evidence only in v0.6.34. It does not change Confidence, Guards, Prediction, Apply Preview or SoundLab EQ.</p>
    `;

    const repeatability = host.querySelector("[data-measurement-repeatability]");
    const controlledApply = [...host.querySelectorAll(".difference-panel")]
      .find((panel) => panel.querySelector("[data-eq-assistant-apply]"));
    const meta = host.querySelector(".response-meta");
    if (repeatability) repeatability.after(card);
    else if (controlledApply) controlledApply.before(card);
    else if (meta) meta.before(card);
    else host.append(card);
  };

  proto.addRepeatFiles = async function addRepeatFiles(files) {
    const panel = this.panel();
    const session = this.sessionId();
    const channel = this.selectedChannel();
    if (!panel?.send || !session || !this.response || !files?.length || this.repeatabilityBusy) return;

    this.repeatabilityBusy = true;
    this.repeatabilityError = "";
    this.repeatabilityMessage = "";
    this.render();
    try {
      for (const file of files) {
        if ((this.repeatabilityRepeats || []).length >= this.repeatabilityMax) break;
        const parsed = parseRepeatFile(await file.text());
        const data = await panel.send("kcc_soundlab/add_frequency_response_repeat", {
          session_id: session,
          channel,
          source_name: file.name || "REW repeat",
          original_point_count: parsed.originalCount,
          points: parsed.points,
        });
        this.repeatabilityRepeats = Array.isArray(data?.repeats)
          ? data.repeats
          : this.repeatabilityRepeats;
        this.repeatabilityMax = Number(data?.max_repeats) || this.repeatabilityMax;
      }
      this.repeatabilityMessage = `Stored ${this.repeatabilityRepeats.length} repeat measurement${this.repeatabilityRepeats.length === 1 ? "" : "s"} for this output`;
    } catch (error) {
      this.repeatabilityError = String(error?.message || error);
    } finally {
      this.repeatabilityBusy = false;
      this.render();
    }
  };

  proto.deleteRepeatability = async function deleteRepeatability(repeatId) {
    const panel = this.panel();
    const session = this.sessionId();
    const channel = this.selectedChannel();
    if (!panel?.send || !session || !repeatId || this.repeatabilityBusy) return;
    if (
      globalThis.confirm
      && !globalThis.confirm("Remove this repeat measurement? The primary REW response is not changed.")
    ) return;

    this.repeatabilityBusy = true;
    this.repeatabilityError = "";
    this.render();
    try {
      const data = await panel.send("kcc_soundlab/delete_frequency_response_repeat", {
        session_id: session,
        channel,
        repeat_id: repeatId,
      });
      this.repeatabilityRepeats = Array.isArray(data?.repeats) ? data.repeats : [];
      this.repeatabilityMessage = "Repeat measurement removed";
    } catch (error) {
      this.repeatabilityError = String(error?.message || error);
    } finally {
      this.repeatabilityBusy = false;
      this.render();
    }
  };

  proto.onChange = function onChange(event) {
    const repeatInput = event.target.closest?.("[data-repeatability-file]");
    if (repeatInput?.files?.length) {
      this.addRepeatFiles([...repeatInput.files]);
      return;
    }
    if (event.target.matches?.("[data-response-channel]")) {
      this.repeatabilityRepeats = [];
      this.repeatabilityMessage = "";
      this.repeatabilityError = "";
      this.multiPositionMeasurements = [];
      this.multiPositionError = "";
    }
    return baseChange.call(this, event);
  };

  proto.onClick = function onClick(event) {
    const remove = event.target.closest?.("[data-repeatability-delete]");
    if (remove) {
      this.deleteRepeatability(String(remove.dataset.repeatabilityDelete || ""));
      return;
    }
    return baseClick.call(this, event);
  };

  proto.render = function render(...args) {
    const result = baseRender.apply(this, args);
    this.injectRepeatability();
    this.injectMultiPosition();
    this.decorateConfidenceRepeatability();
    return result;
  };
}
