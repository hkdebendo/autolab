"use strict";
/* AutoLab jury page: replay the reference run, or follow a live run on Modal.
   Plain JavaScript, no build step. 3D comes from 3Dmol.js (CDN) when reachable. */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtF = (n, d = 3) => (n == null || !isFinite(n) ? "–" : Number(n).toFixed(d));
const fmtE = (n) => (n == null || !isFinite(n) ? "–" : Number(n).toExponential(2));
const fmtUSD = (n) => (n == null ? "–" : "$" + Number(n).toFixed(n < 0.01 ? 4 : 2));
const good = (t) => `<span class="mark-good">✓ ${t}</span>`;
const bad = (t) => `<span class="mark-bad">✗ ${t}</span>`;
const warn = (t) => `<span class="mark-warn">! ${t}</span>`;

const FUNNEL = ["proposal", "Materials Project", "relaxation", "stability", "band gap",
  "electrodes", "reviews", "MD choice", "molecular dynamics", "ranking", "novelty"];

function funnelIndex(ev) {
  const k = ev.type + "/" + ev.step;
  if (k === "llm/proposal") return 0;
  if (k === "candidate/known_check") return 1;
  if (k === "candidate/relax") return 2;
  if (k === "candidate/hull") return 3;
  if (k === "candidate/bandgap") return 4;
  if (ev.step.startsWith("electrodes")) return 5;
  if (ev.step.startsWith("candidate_analyses")) return 6;
  if (k === "llm/md_selection" || ev.step === "md_selection") return 7;
  if (ev.step.startsWith("molecular_dynamics")) return 8;
  if (ev.step === "ranking") return 9;
  if (ev.step === "novelty") return 10;
  return -1;
}

function renderFunnel(active) {
  $("funnel").innerHTML = FUNNEL.map((name, i) =>
    `<span class="${i < active ? "done" : i === active ? "active" : ""}">${esc(name)}</span>`).join("");
}

const S = {
  mode: "replay", speed: 10,
  events: [], result: null, index: null, formulas: {},
  cands: {}, ehullMax: 0.05,
  timer: null, pollTimer: null, pumpTimer: null, queue: [],
  liveId: null, liveNext: 0,
  md: { cand: null, parent: null, frame: 0, playing: true, timer: null, vc: null, vp: null, zoom: {} },
};

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

/* ---------- timeline cards (newest on top) ---------- */

function pushCard(ev, title, body, mark = "") {
  const cand = ev.candidate_id ? `<span class="tag">${esc(ev.candidate_id)}</span>` : "";
  const when = ev.timestamp ? `<span class="when">${esc(ev.timestamp.slice(11, 19))}</span>` : "";
  $("timeline").insertAdjacentHTML("afterbegin",
    `<article class="card ${mark}"><h3>${when}${cand}${title}</h3>${body}</article>`);
}

function foot(d) {
  const parts = [];
  if (d.provider) parts.push(esc(d.provider));
  if (d.input_tokens != null) parts.push(`${d.input_tokens}→${d.output_tokens} tokens`);
  if (d.cost_usd != null) parts.push(fmtUSD(d.cost_usd));
  if (d.seconds != null) parts.push(`${d.seconds} s`);
  if (d.cached) parts.push("cached");
  return parts.length ? `<p class="foot">${parts.join(" · ")}</p>` : "";
}

function reasoning(d) {
  return d.reasoning_summary
    ? `<details><summary>reasoning</summary><p>${esc(d.reasoning_summary).replace(/\n/g, "<br>")}</p></details>`
    : "";
}

function kv(obj, skip = []) {
  return Object.entries(obj).filter(([k]) => !skip.includes(k)).map(([k, v]) => {
    const val = Array.isArray(v)
      ? v.map((x) => `<span class="tag">${esc(typeof x === "object" ? JSON.stringify(x) : x)}</span>`).join(" ")
      : esc(typeof v === "object" ? JSON.stringify(v) : v);
    return `<p><b>${esc(k)}</b>: ${val}</p>`;
  }).join("");
}

const RENDER = {
  "loop/start"(ev, d) {
    S.ehullMax = d.thresholds?.EHULL_SYNTHESIZABLE ?? 0.05;
    const parents = (d.parents || []).map((p) => `<span class="tag">${esc(p.formula)} · ${p.nsites} sites</span>`).join(" ");
    pushCard(ev, "Run starts",
      `<blockquote><b>${esc(d.goal)}</b></blockquote><p>${parents}</p>` +
      `<p class="foot">${esc(d.domain)} · ${(d.prior || []).length} earlier candidates · brain ${esc(d.brain)}</p>`);
  },
  "loop/iteration"(ev, d) {
    pushCard(ev, `Iteration ${d.iteration}`, "");
  },
  "llm/proposal"(ev, d) {
    const r = d.reply || {};
    const items = (r.proposals || []).map((p) => {
      const s = p.substitution || {};
      const sub = `${esc(s.remove)}→${esc(s.add)} ×${s.count}` +
        (s.li_vacancies ? ` (+${s.li_vacancies} Li vac.)` : "");
      return `<li><b>${esc(p.parent)}</b>: ${sub}<br><i>${esc(p.rationale)}</i></li>`;
    }).join("");
    pushCard(ev, `Muse Spark proposes ${r.proposals?.length ?? 0} substitutions`,
      `<blockquote><b>${esc(r.hypothesis)}</b></blockquote><ul>${items}</ul>${reasoning(d)}${foot(d)}`);
  },
  "llm/analysis"(ev, d) {
    const r = d.reply || {};
    pushCard(ev, "Muse Spark reads the results",
      `<ul>${(r.lessons || []).map((l) => `<li><b>${esc(l)}</b></li>`).join("")}</ul>` +
      `<p>Next: <b>${esc(r.next_direction)}</b></p>` +
      `<p class="foot">ranking: ${esc((r.ranking || []).join(", "))}${r.stop ? " · stop" : ""}</p>` +
      `${reasoning(d)}${foot(d)}`);
  },
  "llm/md_selection"(ev, d) {
    const r = d.reply || {};
    pushCard(ev, "Muse Spark chooses the MD candidates",
      `<p><b>${esc((r.selected || []).join(", "))}</b></p><p><i>${esc(r.rationale)}</i></p>` +
      `${reasoning(d)}${foot(d)}`);
  },
  "llm/error": (ev, d) => pushCard(ev, "Model failure", `<p>${bad(esc(d.error || d.provider))}</p>`, "bad"),
  "llm/budget": (ev, d) => pushCard(ev, "Budget reached", `<p>${warn(esc(d.error || d.provider))}</p>`, "warn"),
  "candidate/generate"(ev, d) {
    pushCard(ev, `Candidate <b>${esc(d.formula)}</b> built`,
      d.accepted ? `<p>${good(`charge-neutral, ${d.arrangements} arrangements`)}</p>`
        : `<p>${bad(esc(d.reason || "rejected"))}</p>`,
      d.accepted ? "good" : "bad");
  },
  "candidate/known_check"(ev, d) {
    const known = d.known || [];
    pushCard(ev, "Materials Project check",
      known.length ? `<p>${bad("already known: " + esc(known.join(", ")))}</p>`
        : `<p>${good("new — not in Materials Project")}</p>`,
      known.length ? "bad" : "good");
  },
  "candidate/relax"(ev, d) {
    const ok = d.converged === d.arrangements;
    pushCard(ev, "UMA relaxation",
      `<p>${ok ? good(`${d.converged}/${d.arrangements} converged`) : warn(`${d.converged}/${d.arrangements} converged`)}, ` +
      `spread ${fmtF(d.spread_meV, 1)} meV</p>`, ok ? "good" : "warn");
  },
  "candidate/hull"(ev, d) {
    const ok = d.e_hull != null && d.e_hull <= S.ehullMax;
    const decomp = (d.decomposition || []).map((x) => `<span class="tag">${esc(x.formula)}</span>`).join(" ");
    pushCard(ev, "Stability",
      `<p><b>E_hull = ${fmtF(d.e_hull, 4)} eV/atom</b> (${fmtF(d.e_hull_per_substitution, 3)} per substitution) ` +
      `${ok ? good("synthesisable") : warn("metastable")}</p><p>${decomp}</p>`, ok ? "good" : "warn");
  },
  "candidate/bandgap"(ev, d) {
    pushCard(ev, "Band gap",
      `<p><b>${fmtF(d.gap_optb88, 2)} eV</b> (MBJ ${fmtF(d.gap_mbj, 2)}) ` +
      `${d.passes ? good("insulating") : bad("too metallic")}</p>`, d.passes ? "good" : "bad");
  },
  "candidate/ss_check"(ev, d) {
    pushCard(ev, "S–S bonds check",
      d.ss_bonds ? `<p>${bad("S–S bonds found")}</p>` : `<p>${good("no S–S bonds")}</p>`,
      d.ss_bonds ? "bad" : "good");
  },
  "candidate/done"(ev, d) {
    const mark = d.status === "passed" ? "good" : d.status === "rejected" ? "bad" : "warn";
    const flag = d.status === "passed" ? good(d.status) : d.status === "rejected" ? bad(d.status) : warn(d.status);
    pushCard(ev, "Funnel result",
      `<p><b>${flag}</b>${d.rejected_at ? ` at ${esc(d.rejected_at)}` : ""}` +
      `${d.reason ? `<br>${esc(d.reason)}` : ""}</p>`, mark);
  },
  "candidate/electrodes:done"(ev, d) {
    const w = d.window || {};
    const pass = `<b class="${d.passivation === "passivating" ? "mark-good" : "mark-bad"}">${esc(d.passivation)}</b>`;
    pushCard(ev, "Electrodes",
      `<p>window <b>${fmtF(w.v_low, 2)}–${fmtF(w.v_high, 2)} V</b> · ${pass}` +
      `${d.excluded ? ` · ${bad("excluded")}` : ` · ${good("kept")}`}</p>` +
      `<p class="foot">interface ${fmtF(d.interface_reaction_energy, 3)} eV/atom` +
      `${d.reduced_confidence ? " · reduced confidence" : ""}</p>`,
      d.excluded ? "bad" : "good");
  },
  "candidate/candidate_analyses:done"(ev, d) {
    pushCard(ev, "Muse Spark Open review",
      `<p>${esc(d.summary)}</p><p>MD priority: <b>${esc(d.md_priority)}</b></p>` +
      `<ul>${(d.strengths || []).map((s) => `<li>${good(esc(s))}</li>`).join("")}` +
      `${(d.risks || []).map((s) => `<li>${bad(esc(s))}</li>`).join("")}</ul>${foot(d)}`);
  },
  "candidate/molecular_dynamics:done"(ev, d) {
    const mark = d.verdict === "lower" ? "bad" : "good";
    pushCard(ev, "Li diffusion (MD)",
      `<p><b>D = ${fmtE(d.D_cm2_per_s)} cm²/s</b> · D/D(parent) = <b>${fmtF(d.ratio, 2)}</b> · ` +
      `verdict <b>${esc(d.verdict)}</b> · conduction ${esc(d.conduction)}</p>`, mark);
  },
  "stage/electrodes:calibration"(ev, d) {
    pushCard(ev, "Calibration: Li3PS4 vs cathode",
      `<p>UMA ${fmtF(d.uma, 3)} vs MP ${fmtF(d.mp, 3)}, diff ${fmtF(d.diff, 4)} ` +
      `${d.ok ? good("ok") : bad("off")}</p>`, d.ok ? "good" : "bad");
  },
  "stage/molecular_dynamics:plan"(ev, d) {
    pushCard(ev, "MD plan",
      `<p>${d.runs} new runs (${d.total_runs} total) · ${fmtUSD(d.usd)} · ${(d.wall_s / 60).toFixed(0)} min wall</p>`);
  },
  "stage/*"(ev, d) {
    const mark = d.status === "done" ? "good" : d.status === "error" ? "bad" : "";
    pushCard(ev, `Stage ${esc(ev.step)}: ${esc(d.status)}`, kv(d, ["status"]), mark);
  },
  "loop/stop"(ev, d) {
    pushCard(ev, "Run ends",
      `<p>${esc(d.reason)}</p><p>${(d.final_ranking || []).map((c) => `<span class="tag">${esc(c)}</span>`).join(" ")}</p>`);
  },
  "*"(ev, d) {
    pushCard(ev, `${esc(ev.type)} / ${esc(ev.step)}`, kv(d));
  },
};

function showEvent(ev) {
  const d = ev.data || {};
  const fi = funnelIndex(ev);
  if (fi >= 0) renderFunnel(fi);
  updateTable(ev);
  (RENDER[ev.type + "/" + ev.step] || RENDER[ev.type + "/*"] || RENDER["*"])(ev, d);
  if ((ev.type === "stage" && ev.step === "molecular_dynamics" && d.status === "start") ||
      (ev.type === "candidate" && ev.step === "molecular_dynamics:done")) mdInit();
  if (ev.type === "loop" && ev.step === "stop") showEnd();
}

/* ---------- candidates table (right, updated live) ---------- */

function rowOf(id) {
  if (!S.cands[id]) S.cands[id] = { formula: S.formulas[id] || id };
  return S.cands[id];
}

function updateTable(ev) {
  const id = ev.candidate_id;
  if (!id) return;
  const d = ev.data || {};
  const row = rowOf(id);
  const k = ev.type + "/" + ev.step;
  if (k === "candidate/generate") {
    row.formula = d.formula || id;
    S.formulas[id] = row.formula;
  }
  else if (k === "candidate/hull") row.ehull = d.e_hull;
  else if (k === "candidate/bandgap") row.gap = d.gap_optb88;
  else if (k === "candidate/electrodes:done") {
    row.window = d.window;
    row.pass = d.passivation;
    if (d.excluded) row.status = "rejected";
  } else if (k === "candidate/molecular_dynamics:done") {
    row.ratio = d.ratio;
    row.verdict = d.verdict;
  } else if (k === "candidate/done") row.status = d.status;
  const tb = $("candidates").querySelector("tbody");
  tb.innerHTML = Object.entries(S.cands).map(([cid, r]) => {
    const w = r.window ? `${fmtF(r.window.v_low, 2)}–${fmtF(r.window.v_high, 2)}` : "–";
    const st = r.status
      ? `<span class="${r.status === "passed" ? "mark-good" : r.status === "rejected" ? "mark-bad" : "mark-warn"}">${esc(r.status)}</span>`
      : "–";
    return `<tr data-id="${esc(cid)}"><td>${esc(r.formula)}</td><td>${fmtF(r.ehull, 3)}</td>` +
      `<td>${fmtF(r.gap, 2)}</td><td>${w}</td><td>${esc(r.pass ?? "–")}</td>` +
      `<td>${fmtF(r.ratio, 2)}</td><td>${st}</td></tr>`;
  }).join("");
}

/* ---------- 3D helpers (3Dmol.js from CDN, if reachable) ---------- */

const mol3d = () => window.$3Dmol || null;

function xyz(atoms) {
  let s = `${atoms.length}\n\n`;
  for (const a of atoms) s += `${a.el} ${a.x.toFixed(3)} ${a.y.toFixed(3)} ${a.z.toFixed(3)}\n`;
  return s;
}

function drawCell(v, cell) {
  const [a, b, c] = cell;
  const corner = (i, j, k) => [a[0] * i + b[0] * j + c[0] * k, a[1] * i + b[1] * j + c[1] * k, a[2] * i + b[2] * j + c[2] * k];
  const P = (p) => ({ x: p[0], y: p[1], z: p[2] });
  for (const [i, j, k, di, dj, dk] of
    [[0, 0, 0, 1, 0, 0], [0, 1, 0, 1, 0, 0], [0, 0, 1, 1, 0, 0], [0, 1, 1, 1, 0, 0],
     [0, 0, 0, 0, 1, 0], [1, 0, 0, 0, 1, 0], [0, 0, 1, 0, 1, 0], [1, 0, 1, 0, 1, 0],
     [0, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 1], [0, 1, 0, 0, 0, 1], [1, 1, 0, 0, 0, 1]]) {
    v.addLine({ start: P(corner(i, j, k)), end: P(corner(i + di, j + dj, k + dk)), color: "0x999999" });
  }
}

/* ---------- structure viewer (click a candidate row) ---------- */

async function openStruct(id) {
  if (S.mode !== "replay") {
    alert("3D structures are available in replay mode.");
    return;
  }
  $("struct-modal").hidden = false;
  $("struct-title").textContent = `${S.formulas[id] || id} (${id})`;
  const entry = (S.index?.structures || []).find((e) => e.id === id);
  if (!entry) {
    $("struct-info").textContent = "No structure saved for this candidate.";
    $("struct-view").innerHTML = "";
    return;
  }
  const st = await fetchJSON(`/api/replay/replay/${entry.file}`);
  $("struct-info").textContent =
    `parent ${st.parent} · E_hull ${fmtF(st.e_hull, 4)} eV/atom` +
    (st.highlight ? ` · ${st.highlight} shown in red` : "");
  if (!mol3d()) {
    $("struct-view").innerHTML = "<p>3D needs network access to the CDN.</p>";
    return;
  }
  $("struct-view").innerHTML = "";
  const v = mol3d().createViewer($("struct-view"), { backgroundColor: "white" });
  v.addModel(xyz(st.symbols.map((el, i) =>
    ({ el, x: st.positions[i][0], y: st.positions[i][1], z: st.positions[i][2] }))), "xyz");
  v.setStyle({}, { stick: { radius: 0.12 }, sphere: { scale: 0.32 } });
  if (st.highlight) v.setStyle({ elem: st.highlight }, { sphere: { scale: 0.65, color: "red" } });
  drawCell(v, st.cell);
  v.zoomTo();
  v.render();
}

/* ---------- MD viewer: Li moving inside the static framework ---------- */

function mdCandidates() {
  return [...new Set((S.index?.md || []).filter((e) => e.kind === "candidate").map((e) => e.id))];
}

function mdInit() {
  if (S.mode !== "replay" || !$("md-box").hidden || !mdCandidates().length) return;
  $("md-box").hidden = false;
  $("md-pick").innerHTML = mdCandidates().map((id) => {
    const e = S.index.md.find((x) => x.kind === "candidate" && x.id === id);
    return `<option value="${esc(id)}">${esc(id)} · ${esc(e.formula)}</option>`;
  }).join("");
  $("md-pick").onchange = () => { mdSeeds(); mdLoad(); };
  $("md-seed").onchange = mdLoad;
  $("md-play").onclick = mdToggle;
  $("md-frame").oninput = () => { S.md.frame = +$("md-frame").value; mdDraw(); };
  $("md-trails").onchange = mdDraw;
  mdSeeds();
  mdLoad();
}

function mdSeeds() {
  const id = $("md-pick").value;
  const seeds = S.index.md.filter((e) => e.id === id).map((e) => e.seed);
  $("md-seed").innerHTML = seeds.map((s) => `<option>${s}</option>`).join("");
}

function mdFile(id, seed) {
  return S.index.md.find((e) => e.id === id && e.seed === +seed);
}

async function mdLoad() {
  const id = $("md-pick").value, seed = $("md-seed").value;
  const entry = mdFile(id, seed);
  if (!entry) return;
  const cand = await fetchJSON(`/api/replay/replay/${entry.file}`);
  let parent = null;
  const pentry = mdFile(cand.parent, seed) || mdFile(cand.parent, 0);
  if (pentry) parent = await fetchJSON(`/api/replay/replay/${pentry.file}`);
  S.md.cand = cand;
  S.md.parent = parent;
  S.md.frame = 0;
  S.md.zoom = {};
  $("md-frame").max = cand.frames.length - 1;
  $("md-frame").value = 0;
  $("md-sub").textContent = `${cand.formula}, ${cand.temperature_K} K, ${cand.frames.length} frames over 40 ps`;
  $("md-cand-cap").textContent = `${cand.id} · ${cand.formula}`;
  $("md-parent-cap").textContent = parent ? `${parent.id} · ${parent.formula} (parent)` : "parent not in replay";
  $("md-stats").innerHTML =
    `<b>D = ${fmtE(cand.D_cm2_per_s)} ± ${fmtE(cand.D_sem_cm2_per_s)} cm²/s</b> · ` +
    `D/D(parent) = <b>${fmtF(cand.ratio, 2)} ± ${fmtF(cand.ratio_err, 2)}</b> · ` +
    `verdict <b>${esc(cand.verdict)}</b> · conduction ${esc(cand.conduction)} (${esc(cand.conduction_reason)})`;
  $("md-msd").innerHTML = msdSVG(cand, parent);
  if (!S.md.playing) mdToggle();
  mdPlay();
  mdDraw();
}

function mdToggle() {
  S.md.playing = !S.md.playing;
  $("md-play").textContent = S.md.playing ? "Pause" : "Play";
  if (S.md.playing) mdPlay();
  else clearInterval(S.md.timer);
}

function mdPlay() {
  clearInterval(S.md.timer);
  S.md.playing = true;
  $("md-play").textContent = "Pause";
  S.md.timer = setInterval(() => {
    if (!S.md.cand) return;
    S.md.frame = (S.md.frame + 1) % S.md.cand.frames.length;
    $("md-frame").value = S.md.frame;
    mdDraw();
  }, 90);
}

function mdViewer(which) {
  if (!mol3d()) {
    $(which === "c" ? "md-cand" : "md-parent").innerHTML = "<p>3D needs network access to the CDN.</p>";
    return null;
  }
  const key = which === "c" ? "vc" : "vp";
  if (!S.md[key]) {
    $(which === "c" ? "md-cand" : "md-parent").innerHTML = "";
    S.md[key] = mol3d().createViewer($(which === "c" ? "md-cand" : "md-parent"), { backgroundColor: "white" });
  }
  return S.md[key];
}

function mdDraw() {
  drawMD(mdViewer("c"), S.md.cand, "c");
  drawMD(mdViewer("p"), S.md.parent, "p");
}

function drawMD(v, data, which) {
  if (!v || !data) return;
  const f = S.md.frame % data.frames.length;
  v.removeAllModels();
  v.removeAllShapes();
  const atoms = data.framework.symbols.map((el, i) =>
    ({ el, x: data.framework.positions[i][0], y: data.framework.positions[i][1], z: data.framework.positions[i][2] }));
  for (const p of data.frames[f]) atoms.push({ el: "Li", x: p[0], y: p[1], z: p[2] });
  v.addModel(xyz(atoms), "xyz");
  v.setStyle({ elem: "Li" }, { sphere: { scale: 0.6 } });
  for (const el of [...new Set(data.framework.symbols)])
    v.addStyle({ elem: el }, { stick: { radius: 0.14 }, sphere: { scale: 0.3 } });
  if ($("md-trails").checked) {
    const n = data.frames.length;
    for (let k = 1; k <= 6; k++) {
      for (const p of data.frames[(f - k + n) % n])
        v.addSphere({ center: { x: p[0], y: p[1], z: p[2] }, radius: 0.25, color: "0x66aaff", opacity: 0.22 });
    }
  }
  drawCell(v, data.cell);
  if (!S.md.zoom[which]) {
    v.zoomTo();
    S.md.zoom[which] = true;
  }
  v.render();
}

function msdSVG(cand, parent) {
  const W = 560, H = 220, L = 52, B = 30, T = 10;
  const t = cand.curve.t_ps;
  const series = [{ label: `Li (${cand.id})`, y: cand.curve.msd_li_A2, color: "#1f77b4", dash: "" }];
  for (const [el, y] of Object.entries(cand.curve.msd_framework_A2 || {}))
    series.push({ label: el, y, color: "#999999", dash: "" });
  if (parent) series.push({ label: `Li (${parent.id})`, y: parent.curve.msd_li_A2, color: "#1f77b4", dash: "4,3" });
  const ymax = Math.max(0.1, ...series.flatMap((s) => s.y));
  const X = (i) => L + (i / (t.length - 1)) * (W - L - 10);
  const Y = (v) => H - B - (v / ymax) * (H - B - T);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="MSD curve">`;
  s += `<line x1="${L}" y1="${T}" x2="${L}" y2="${H - B}" stroke="#333"/>` +
    `<line x1="${L}" y1="${H - B}" x2="${W - 10}" y2="${H - B}" stroke="#333"/>`;
  s += `<text x="4" y="${H / 2}" font-size="11" transform="rotate(-90 12 ${H / 2})" text-anchor="middle">MSD (Å²)</text>`;
  s += `<text x="${W - 44}" y="${H - 8}" font-size="11">t (ps)</text>`;
  s += `<text x="${L}" y="${H - 14}" font-size="10">0</text>` +
    `<text x="${W - 52}" y="${H - 14}" font-size="10">${t[t.length - 1].toFixed(0)}</text>` +
    `<text x="4" y="${Y(ymax) + 4}" font-size="10">${ymax.toFixed(1)}</text>`;
  for (const g of series)
    s += `<polyline fill="none" stroke="${g.color}" stroke-width="${g.label.startsWith("Li") ? 2 : 1.2}"` +
      (g.dash ? ` stroke-dasharray="${g.dash}"` : "") +
      ` points="${g.y.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ")}"/>`;
  s += series.map((g, i) =>
    `<text x="${L + 8 + i * 118}" y="${T + 12}" font-size="10" fill="${g.color}">— ${esc(g.label)}</text>`).join("");
  return s + "</svg>";
}

/* ---------- end: ranking, novelty, cost ---------- */

async function showEnd() {
  if (!$("end").hidden) return;
  if (!S.result) {
    try {
      S.result = S.mode === "replay"
        ? await fetchJSON("/api/replay/result.json")
        : await (await fetch(`/api/live/runs/${S.liveId}/result`)).json();
    } catch { return; }
  }
  if (!S.result.stages) {  // live result not stored yet: retry shortly
    S.result = null;
    setTimeout(showEnd, 2000);
    return;
  }
  const st = S.result.stages || {};
  const rk = st.ranking || {};
  const finals = new Set(rk.finalists || []);
  const name = (id) => `${S.formulas[id] || (S.cands[id] || {}).formula || id} (${id})`;
  $("ranking").innerHTML = (rk.ranking || []).map((id) =>
    `<li class="${finals.has(id) ? "finalist" : ""}">${finals.has(id) ? "★ " : ""}${esc(name(id))}</li>`).join("");
  $("excluded").innerHTML = Object.entries(rk.excluded || {}).map(([id, why]) =>
    `<li><b>${esc(name(id))}</b>: ${esc(why)}</li>`).join("") || "<li>none</li>";
  const nv = st.novelty || {};
  const entry = (e, ctl) => `<div class="entry"><b>${ctl ? "control: " : ""}${esc(e.formula)} (${esc(e.id)})</b> ` +
    `<span class="tag">${esc(e.level)}: ${esc(e.label)}</span><p>${esc(e.summary)}</p>` +
    `<p>sources: ${(e.sources || []).map((x) =>
      `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a>`).join(" · ")}</p></div>`;
  $("novelty").innerHTML = (nv.control ? entry(nv.control, true) : "") +
    (nv.candidates || []).map((e) => entry(e, false)).join("");
  const u = S.result.usage || {};
  const rows = [];
  for (const [k, v] of Object.entries(u.llm || {}))
    rows.push([`LLM ${k}`, `${v.calls} calls · ${v.input_tokens}→${v.output_tokens} tokens · ${fmtUSD(v.cost_usd)}`]);
  for (const k of ["analyst", "novelty"]) {
    const v = u[k];
    if (v) rows.push([k, `${v.calls} calls · ${v.input_tokens}→${v.output_tokens} tokens · ${fmtUSD(v.cost_usd)}`]);
  }
  if (u.relaxations) rows.push(["relaxations", `${u.relaxations.new}/${u.relaxations.limit} new`]);
  if (u.md) rows.push(["molecular dynamics",
    `${u.md.runs} new runs (${u.md.total_runs} total) · ${fmtUSD(u.md.usd)} · ${(u.md.wall_s / 60).toFixed(0)} min wall`]);
  if (u.seconds) rows.push(["wall time", `${(u.seconds / 60).toFixed(0)} min`]);
  $("usage").innerHTML = rows.map(([k, v]) => `<tr><td><b>${esc(k)}</b></td><td>${esc(v)}</td></tr>`).join("");
  if (S.mode === "replay") {
    try {
      $("report").innerHTML = await (await fetch("/api/replay/report.html")).text();
      $("report-box").hidden = false;
    } catch { $("report-box").hidden = true; }
  } else $("report-box").hidden = true;
  $("end").hidden = false;
}

/* ---------- replay ---------- */

function resetRun() {
  for (const t of ["timer", "pollTimer", "pumpTimer"]) clearInterval(S[t]);
  clearInterval(S.md.timer);
  S.timer = S.pollTimer = S.pumpTimer = null;
  S.queue = [];
  S.cands = {};
  S.events = [];
  S.result = null;
  S.formulas = {};
  S.liveId = null;
  S.md.cand = S.md.parent = S.md.vc = S.md.vp = null;
  S.md.frame = 0;
  S.md.zoom = {};
  $("timeline").innerHTML = "";
  $("candidates").querySelector("tbody").innerHTML = "";
  $("end").hidden = true;
  $("md-box").hidden = true;
  $("md-cand").innerHTML = "";
  $("md-parent").innerHTML = "";
  renderFunnel(-1);
}

function playReplay(i) {
  clearTimeout(S.timer);
  if (i >= S.events.length) return;
  showEvent(S.events[i]);
  if (i + 1 >= S.events.length) return;
  const dt = (Date.parse(S.events[i + 1].timestamp) - Date.parse(S.events[i].timestamp)) / 1000 / S.speed;
  S.timer = setTimeout(() => playReplay(i + 1), Math.min(3, Math.max(0.4, isFinite(dt) ? dt : 1)) * 1000);
}

async function startReplay() {
  resetRun();
  try {
    [S.events, S.result, S.index] = await Promise.all([
      fetchJSON("/api/replay/events.jsonl"), fetchJSON("/api/replay/result.json"),
      fetchJSON("/api/replay/replay/index.json")]);
  } catch (e) {
    pushCard({ timestamp: null, candidate_id: null }, "Replay files missing",
      `<p>${bad("could not load the reference run")}</p>`, "bad");
    return;
  }
  $("goal").textContent = S.result.goal;
  S.formulas = {};
  for (const e of S.index.structures || []) S.formulas[e.id] = e.formula;
  playReplay(0);
}

/* ---------- live ---------- */

async function liveHealth() {
  let msg = "Live backend unreachable.";
  try {
    const r = await fetch("/api/live/health");
    const j = await r.json().catch(() => ({}));
    if (r.status === 403) msg = "Live mode is disabled on this server.";
    else if (r.ok) msg = j.busy ? "A run is already going — try again later."
      : `Ready · ${j.live_runs_used}/${j.live_runs_allowed} runs used.`;
  } catch { /* keep default */ }
  $("live-health").textContent = msg;
}

async function liveSubmit(e) {
  e.preventDefault();
  const goal = $("live-goal").value.trim();
  const code = $("live-code").value;
  if (!goal || goal.length > 500) {
    $("live-status").textContent = "The request must be 1 to 500 characters.";
    return;
  }
  resetRun();
  $("live-status").textContent = "Starting…";
  let r;
  try {
    r = await fetch("/api/live/runs", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, access_code: code }),
    });
  } catch {
    $("live-status").textContent = "Live backend unreachable.";
    return;
  }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    $("live-status").textContent = `Refused (${r.status}): ${j.detail || "unknown reason"}`;
    return;
  }
  S.liveId = j.run_id;
  S.liveNext = 0;
  $("live-status").textContent = `Run ${S.liveId} running…`;
  S.pumpTimer = setInterval(() => {
    if (S.queue.length) showEvent(S.queue.shift());
    else if (!S.pollTimer) {
      clearInterval(S.pumpTimer);
      S.pumpTimer = null;
    }
  }, 400);
  const poll = async () => {
    try {
      const pr = await fetch(`/api/live/runs/${S.liveId}/events?after=${S.liveNext}`);
      const pj = await pr.json();
      S.queue.push(...(pj.events || []));
      S.liveNext = pj.next;
      $("live-status").textContent = `Run ${S.liveId}: ${pj.status?.state} · ${S.liveNext} events`;
      if (pj.status?.state === "done" || pj.status?.state === "error") {
        clearInterval(S.pollTimer);
        S.pollTimer = null;
        try {
          S.result = await fetchJSON(`/api/live/runs/${S.liveId}/result`);
        } catch { /* result renders when it arrives */ }
        $("live-status").textContent += pj.status?.error ? ` · error: ${pj.status.error}` : " · done";
      }
    } catch {
      $("live-status").textContent = `Run ${S.liveId}: poll failed, retrying…`;
    }
  };
  poll();
  S.pollTimer = setInterval(poll, 2000);
}

/* ---------- init ---------- */

function setMode(mode) {
  S.mode = mode;
  $("mode-replay").classList.toggle("on", mode === "replay");
  $("mode-live").classList.toggle("on", mode === "live");
  $("live-box").hidden = mode !== "live";
  $("speed-label").style.display = mode === "replay" ? "" : "none";
  if (mode === "replay") startReplay();
  else {
    resetRun();
    liveHealth();
    $("live-status").textContent = "";
  }
}

$("mode-replay").onclick = () => setMode("replay");
$("mode-live").onclick = () => setMode("live");
$("speed").onchange = () => { S.speed = +$("speed").value; };
$("restart").onclick = () => setMode("replay");
$("live-form").onsubmit = liveSubmit;
$("candidates").querySelector("tbody").addEventListener("click", (e) => {
  const tr = e.target.closest("tr");
  if (tr) openStruct(tr.dataset.id);
});
$("struct-close").onclick = () => { $("struct-modal").hidden = true; };
$("struct-modal").addEventListener("click", (e) => {
  if (e.target === $("struct-modal")) $("struct-modal").hidden = true;
});

renderFunnel(-1);
startReplay();

