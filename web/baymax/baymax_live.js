// Baymax live theater: CoWork visual design + real backend data.

const API_DEFAULT = "https://healthcare-ai-data-2ihyeqmb6q-uw.a.run.app";
const PATIENT_ID = "mom-001";
const CORRELATION_ID = "mom-leg-swelling-demo";
const ACTION_ID = "ref-1";
const COMPLAINT = "leg swelling shortness of breath weight gain reduced urine output";
const CLASSIFY_PAYLOAD = {
  age: 72,
  chief_complaint: "leg swelling, shortness of breath, reduced urine output",
  vitals: { heart_rate: 96, respiratory_rate: 22, spo2_pct: 93, bp_systolic: 138, bp_diastolic: 86, temperature_f: 98.6 },
};

function apiBase() {
  const qs = new URLSearchParams(location.search).get("api");
  return (qs || window.BAYMAX_API || API_DEFAULT).replace(/\/$/, "");
}

const organs = [
  { k: "eye", i: "👁", n: "Eyes · evidence" },
  { k: "nose", i: "👃", n: "Nose · signals" },
  { k: "nerves", i: "⚡", n: "Nerves · live state" },
  { k: "brain", i: "🧠", n: "Brain · tradeoff" },
  { k: "hands", i: "🤚", n: "Hands · workflow" },
  { k: "brake", i: "🛑", n: "Brakes · authority" },
  { k: "memory", i: "🎯", n: "Memory · objective" },
  { k: "verify", i: "🔍", n: "Verify · outcome" },
  { k: "voice", i: "🗣️", n: "Voice · explain" },
];

const stream = document.getElementById("bf-stream");
const status = document.getElementById("bf-status");
const apiStatus = document.getElementById("bf-api-status");
const apiBaseEl = document.getElementById("bf-api-base");
const organWrap = document.getElementById("bf-organs");
const organEls = {};
let timers = [];

function initOrgans() {
  organWrap.innerHTML = "";
  organs.forEach((o) => {
    const row = document.createElement("div");
    row.className = "organ";
    row.innerHTML = `<span style="font-size:14px;">${o.i}</span><span class="name">${o.n}</span><span class="dot"></span>`;
    organWrap.appendChild(row);
    organEls[o.k] = row;
  });
}

function setOrgan(k, state) {
  const el = organEls[k];
  if (!el) return;
  const dot = el.querySelector(".dot");
  if (state === "active") {
    el.style.opacity = "1";
    el.style.background = "var(--color-background-info)";
    dot.style.background = "var(--color-text-info)";
    dot.style.boxShadow = "0 0 0 4px var(--color-background-info)";
  } else if (state === "done") {
    el.style.opacity = "1";
    el.style.background = "var(--color-background-secondary)";
    dot.style.background = "var(--color-text-success)";
    dot.style.boxShadow = "none";
  } else {
    el.style.opacity = "0.45";
    el.style.background = "var(--color-background-secondary)";
    dot.style.background = "var(--color-border-secondary)";
    dot.style.boxShadow = "none";
  }
}

async function getJson(path, opts) {
  const res = await fetch(`${apiBase()}${path}`, opts);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function chip(text, bg = "var(--color-background-secondary)", fg = "var(--color-text-secondary)") {
  return `<span class="chip" style="background:${bg};color:${fg};">${text}</span>`;
}

function chipRow(items) {
  return `<div class="chiprow">${items.filter(Boolean).join("")}</div>`;
}

function addStep(step) {
  const el = document.createElement("div");
  el.className = `step ${step.kind || ""}`;
  el.innerHTML = step.html;
  stream.appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));
}

function addDual(clinical, family) {
  const wrap = document.createElement("div");
  wrap.className = "dual";
  wrap.innerHTML = `
    <div class="voice" style="background:var(--color-background-info);">
      <p class="label" style="color:var(--color-text-info);">🩺 To the clinician</p>
      <p style="color:var(--color-text-info);">${clinical}</p>
    </div>
    <div class="voice" style="background:var(--color-background-success);">
      <p class="label" style="color:var(--color-text-success);">👧 To the daughter</p>
      <p style="color:var(--color-text-success);">${family}</p>
    </div>`;
  stream.appendChild(wrap);
  requestAnimationFrame(() => wrap.classList.add("show"));
}

async function loadEvidence() {
  const [root, retrieval, meds, signals, state, bed, lab, tradeoff, goal, classify, outcome, trajectory, caseStatus, drugRisk] =
    await Promise.all([
      getJson("/"),
      getJson(`/api/retrieve?q=${encodeURIComponent(COMPLAINT)}&k=5`),
      getJson("/api/medications").catch(() => null),
      getJson("/api/signals"),
      getJson(`/api/state-diff?patient_id=${PATIENT_ID}`),
      getJson(`/api/ops/bed?patient_id=${PATIENT_ID}`),
      getJson(`/api/lab-status?patient_id=${PATIENT_ID}`),
      getJson("/api/tradeoff", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ patient_id: PATIENT_ID }) }),
      getJson(`/api/goal?patient_id=${PATIENT_ID}`),
      getJson("/api/classify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(CLASSIFY_PAYLOAD) }),
      getJson(`/api/outcome?action_id=${ACTION_ID}`),
      getJson(`/api/trajectory?patient_id=${PATIENT_ID}`),
      getJson(`/v1/cases/${CORRELATION_ID}/status`),
      getJson(`/api/drug-risk?patient_id=${PATIENT_ID}`).catch(() => null),
    ]);
  return { root, retrieval, meds, signals, state, bed, lab, tradeoff, goal, classify, outcome, trajectory, caseStatus, drugRisk };
}

function buildSteps(data) {
  const topEvidence = (data.retrieval.results || []).slice(0, 4);
  const retrievedChips = topEvidence.map((r) =>
    chip(`${r.medical_condition || "unknown"} · ESI ${r.esi_tier_truth ?? "?"}`, "var(--color-background-secondary)", "var(--color-text-secondary)")
  );
  const meds = (data.meds?.data || []).slice(0, 4).map((m) => m.Medication).join(", ");
  const signalChips = (data.signals.signals || []).map((s) =>
    chip(`${s.name}: ${s.headline_metric}=${s.headline_value}`, "var(--color-background-purple)", "var(--color-text-purple)")
  );
  const stateChips = (data.state.changed || []).map((c) =>
    chip(`${c.field}: ${c.from} → ${c.to}`, "var(--color-background-success)", "var(--color-text-success)")
  );
  const optionChips = (data.tradeoff.options || []).map((o) =>
    chip(`${o.id}: ${o.label} · fits today=${o.fits_today}`, o.fits_today ? "var(--color-background-success)" : "var(--color-background-danger)", o.fits_today ? "var(--color-text-success)" : "var(--color-text-danger)")
  );

  return [
    {
      organ: "eye",
      html: `👁 Surface symptom: <b>leg swelling</b><br><span style="color:var(--color-text-secondary);font-size:12px;">Baymax does not answer yet. It opens evidence first.</span>`,
    },
    {
      organ: "eye",
      html: `🗂 Retrieved ${topEvidence.length} similar records from <code>${data.retrieval.corpus}</code>.${chipRow(retrievedChips)}<span style="color:var(--color-text-secondary);font-size:12px;">Medication lens available: ${meds || "not available"}</span>`,
    },
    {
      organ: "nose",
      html: `👃 Cheap signals run before expensive reasoning.${chipRow(signalChips)}<span style="color:var(--color-text-secondary);font-size:12px;">${data.signals.nose_read}</span>`,
    },
    {
      organ: "nose",
      kind: data.drugRisk?.cross_domain_flag ? "danger" : "",
      html: data.drugRisk?.available
        ? `👂 The openFDA whisper — Baymax joins <b>her own meds</b> against real FAERS adverse-event reports:${chipRow((data.drugRisk.per_drug || []).map((d) => chip(`${d.drug}: ${d.serious_reports} serious · ${d.renal_reaction_reports} renal`, d.renal_reaction_reports ? "var(--color-background-danger)" : "var(--color-background-warning)", d.renal_reaction_reports ? "var(--color-text-danger)" : "var(--color-text-warning)")))}<span style="font-size:12px;">She is at <b>${data.drugRisk.patient_renal_state}</b>. ${data.drugRisk.cross_domain_flag ? "A drug she takes has renal adverse-event reports — review before continuing it." : "No renal-specific conflict found."} <span style="color:var(--color-text-tertiary);">(population signal, not proof of causation)</span></span>`
        : `👂 No medication record to cross-check against openFDA for this patient.`,
    },
    {
      organ: "nerves",
      html: `⚡ Prior success is not enough if today's state changed.${chipRow(stateChips)}<span style="color:var(--color-text-warning);font-size:12px;">${data.state.verdict}</span>`,
      kind: "warn",
    },
    {
      organ: "hands",
      html: `🤚 Workflow check: nurse_said_sent=<b>${data.bed.nurse_said_sent}</b>, registered=<b>${data.bed.registered}</b>, ack=<b>${data.bed.ack}</b>.<br><span style="color:var(--color-text-danger);font-size:12px;">${data.bed.note}</span>${chipRow([chip(data.bed.reason_code), chip(data.lab.reason_code)])}`,
      kind: "danger",
    },
    {
      organ: "brain",
      html: `🧠 Baymax weighs options across ${data.tradeoff.dimensions.join(", ")}.${chipRow(optionChips)}<b>Recommended preparation path: option ${data.tradeoff.recommend}.</b><br><span style="font-size:12px;">${data.tradeoff.why}</span>`,
    },
    {
      organ: "memory",
      html: `🎯 Baymax remembers the real objective, not just the literal request.<br><span style="font-size:12px;">Stated request: <b>${data.goal.stated_request}</b></span><br><span style="font-size:12px;">Inferred goal: <b>${data.goal.inferred_goal}</b></span>${chipRow((data.goal.preferences || []).map((p) => chip(p)))}`,
    },
    {
      organ: "brake",
      html: `🛑 Authority check: ESI ${data.classify.esi_tier}, confidence=${data.classify.confidence}, human_review_required=${data.classify.human_review_required}.<br><span style="color:var(--color-text-danger);font-size:12px;">Baymax prepares and escalates. It does not pretend to be the clinician.</span>`,
      kind: "danger",
    },
    {
      organ: "verify",
      html: `🔍 Outcome check: stage=<b>${data.outcome.stage}</b>, tool_success=<b>${data.outcome.tool_success}</b>, real_world_verified=<b>${data.outcome.real_world_verified}</b>.<br><span style="font-size:12px;color:var(--color-text-warning);">${data.outcome.note}</span><br><span style="font-size:12px;">Trajectory: ${(data.trajectory.points || []).map((p) => `${p.date}: CKD ${p.ckd_stage}`).join(" → ")} (${data.trajectory.slope})</span>`,
      kind: "warn",
    },
    {
      organ: "nerves",
      html: `⚡ Current execution state: <b>${data.caseStatus.current_stage}</b> · owner=${data.caseStatus.current_owner}.<br><span style="font-size:12px;">Next expected event: ${data.caseStatus.next_expected_event}</span><br><span style="font-size:12px;color:var(--color-text-warning);">${data.caseStatus.blocking_reason}</span>`,
      kind: "warn",
    },
    {
      organ: "voice",
      dual: true,
      clinical: `"This looks like a fluid-overload trajectory with kidney risk. Current state changed from CKD stage 2 to 3; bed ACK and fresh renal labs are still pending. I recommend preparation for lower-intensity renal review and human escalation."`,
      family: `"I found signs that this may be more than leg swelling. Baymax is waiting for the bed confirmation and fresh kidney labs before anyone treats this as done."`,
    },
  ];
}

function clearTheater() {
  timers.forEach(clearTimeout);
  timers = [];
  stream.innerHTML = "";
  status.textContent = "";
  organs.forEach((o) => setOrgan(o.k, "idle"));
}

async function run() {
  clearTheater();
  apiBaseEl.textContent = apiBase().replace("https://", "");
  apiStatus.textContent = "calling API...";
  try {
    const data = await loadEvidence();
    apiStatus.textContent = `API online · ${(data.root.total_encounters || 0).toLocaleString()} encounters`;
    apiStatus.style.color = "var(--color-text-success)";
    const steps = buildSteps(data);
    let delay = 250;
    steps.forEach((step, idx) => {
      timers.push(setTimeout(() => {
        organs.forEach((o) => {
          if (organEls[o.k]?.dataset.done) setOrgan(o.k, "done");
        });
        setOrgan(step.organ, "active");
        if (step.dual) addDual(step.clinical, step.family);
        else addStep(step);
        organEls[step.organ].dataset.done = "1";
        if (idx === steps.length - 1) {
          status.textContent = "done · answer came after evidence, state, action, and verification checks";
          timers.push(setTimeout(() => organs.forEach((o) => setOrgan(o.k, "done")), 500));
        }
      }, delay));
      delay += step.dual ? 950 : 850;
    });
  } catch (e) {
    apiStatus.textContent = "API offline";
    apiStatus.style.color = "var(--color-text-danger)";
    addStep({ html: `⚠️ Baymax could not reach the backend: ${e.message}`, kind: "danger" });
  }
}

initOrgans();
document.getElementById("bf-replay").addEventListener("click", run);
run();
