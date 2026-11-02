/* AutoLab web interface (interface.md): a conversation-first research assistant.
   Everything shown comes from the AutoLab service: steps from real events, numbers from stored results. The models at
   work are named with what they do (owner, 2026-11-02); no providers, no costs. Chemical formulas are written with
   subscripts (Li₇P₃S₁₁). */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const ACTIVE = new Set(["queued", "running", "stopping"]);

/* chemical formulas with subscripts: Li7P3S11 -> Li₇P₃S₁₁ (only tokens made of at least two element symbols with a
   count, so that "40 ps", "H100" or "mp-641703" are left alone) */
const ELEMENTS = new Set(("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br " +
  "Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re " +
  "Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U").split(" "));
const SUBSCRIPT = "₀₁₂₃₄₅₆₇₈₉";
const FORMULA = new RegExp("^(?:[A-Z][a-z]?\\d*|\\((?:[A-Z][a-z]?\\d*)+\\)\\d*)+$");
function isFormula(tok) {
  if (!/\d/.test(tok) || !FORMULA.test(tok)) return false;
  const els = tok.match(/[A-Z][a-z]?/g) || [];
  return els.length >= 2 && els.every((e) => ELEMENTS.has(e));
}
function chem(text) {
  return String(text ?? "").replace(/[A-Za-z0-9]+(?:\([A-Za-z0-9]+\)[0-9]*[A-Za-z0-9]*)*/g,
    (tok) => (isFormula(tok) ? tok.replace(/\d/g, (d) => SUBSCRIPT[d]) : tok));
}
const tx = (s) => chem(esc(s));  // text shown to the reader: escaped, formulas with subscripts
function chemHTML(html) {  // formulas in rendered HTML (report, notes), code left alone
  const tpl = document.createElement("template");
  tpl.innerHTML = html;
  const walk = document.createTreeWalker(tpl.content, NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    if (!n.parentElement || !n.parentElement.closest("code, pre")) n.nodeValue = chem(n.nodeValue);
  }
  return tpl.innerHTML;
}
const POLL_MS = 2500;
const AI_ICON = `<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="3.2" fill="currentColor"/><ellipse cx="16" cy="16" rx="13" ry="5.2"/><ellipse cx="16" cy="16" rx="13" ry="5.2" transform="rotate(60 16 16)"/><ellipse cx="16" cy="16" rx="13" ry="5.2" transform="rotate(120 16 16)"/></svg>`;
const CHECK = `<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>`;
const CROSS = `<svg viewBox="0 0 24 24"><path d="M7 7l10 10M17 7 7 17"/></svg>`;
const PAUSE = `<svg viewBox="0 0 24 24"><path d="M9 7v10M15 7v10"/></svg>`;

const S = { id: null, view: null, events: [], next: 0, timer: null, tab: "progress", index: null, history: [],
            viewers: [], mdTimer: null, sending: false };

/* ---------- service calls ---------- */

const busy = { n: 0, timer: 0 };
function busyStart() { if (busy.n++ === 0) busy.timer = setTimeout(() => $("loadbar").classList.add("on"), 120); }
function busyEnd() {
  busy.n = Math.max(0, busy.n - 1);
  if (!busy.n) { clearTimeout(busy.timer); $("loadbar").classList.remove("on"); }
}

async function api(path, opts = {}) {  // opts.quiet: a background refresh, no loading bar
  if (!opts.quiet) busyStart();
  try {
    const res = await fetch(`/api${path}`, {
      method: opts.method || "GET",
      headers: opts.body ? { "Content-Type": "application/json" } : undefined,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch { /* empty body */ }
    if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
    return data;
  } finally {
    if (!opts.quiet) busyEnd();
  }
}

const loadingHTML = (text) => `<div class="thread"><div class="loading-block" role="status"><div class="spinner"></div>
  <p>${esc(text)}</p><i></i><i></i><i class="short"></i></div></div>`;

function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 4200);
}

/* ---------- theme (light by default, saved between visits) ---------- */

function themeChoice() { try { return localStorage.getItem("autolab-theme") || "light"; } catch { return "light"; } }
function applyTheme(choice) {
  try { localStorage.setItem("autolab-theme", choice); } catch { /* private mode */ }
  const dark = choice === "dark" || (choice === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  for (const r of document.querySelectorAll('#theme-choice input')) r.checked = r.value === choice;
  const bg = getComputedStyle(document.documentElement).getPropertyValue("--viewer-bg").trim();
  for (const v of S.viewers) { try { v.setBackgroundColor(bg); v.render(); } catch { /* viewer gone */ } }
  if (S.view) renderResearch();  // charts read the theme colours
}

/* ---------- navigation ---------- */

function navigate(path, replace = false) {
  if (location.pathname !== path) history[replace ? "replaceState" : "pushState"]({}, "", path);
  route();
}

function route() {
  closeDrawer();
  document.querySelector(".main").classList.remove("results-page");
  const m = location.pathname.match(/^\/c\/([\w-]+)/);
  const r = location.pathname.match(/^\/results(?:\/([\w-]+))?/);
  const st = location.pathname.match(/^\/settings(?:\/([\w-]+))?(\/edit)?/);
  const bm = location.pathname.match(/^\/benchmarks(?:\/([\w-]+))?/);
  if (m) openConversation(m[1]);
  else if (r) showResults(r[1]);
  else if (st) showSettings(st[1], !!st[2]);
  else if (bm) showBenchmarks(bm[1]);
  else showHome();
}

function stopTimers() {
  labStop();
  clearInterval(S.timer); S.timer = null;
  clearInterval(S.mdTimer); S.mdTimer = null;
  cancelAnimationFrame(sphere.raf);
}

/* ---------- history (left) ---------- */

async function loadHistory() {
  try { S.history = await api("/conversations", { quiet: true }); } catch (e) { S.history = S.history || []; }
  S.historyLoaded = true;
  renderHistory();
}

function dayGroup(iso) {
  const d = new Date(iso), now = new Date();
  const days = Math.floor((new Date(now.toDateString()) - new Date(d.toDateString())) / 864e5);
  return days <= 0 ? "Today" : days === 1 ? "Yesterday" : days < 7 ? "Previous 7 days" : "Older";
}

function shortTime(iso) {
  const d = new Date(iso);
  return dayGroup(iso) === "Today" ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString([], { day: "numeric", month: "short" });
}

function renderHistory() {
  const nav = $("history");
  if (!S.history.length) {
    nav.innerHTML = S.historyLoaded ? `<p class="h-empty">Your researches will appear here.</p>`
      : `<p class="h-empty"><span class="spinner small"></span> Loading your researches…</p>`;
    return;
  }
  let html = "", group = null;
  for (const c of S.history) {
    const g = dayGroup(c.updated_at);
    if (g !== group) { html += `<h3>${g}</h3>`; group = g; }
    const st = ACTIVE.has(c.status) ? "running" : c.status === "interrupted" ? "interrupted" : c.status === "error" ? "error" : "";
    html += `<a class="h-item${c.id === S.id ? " active" : ""}" href="/c/${esc(c.id)}" data-id="${esc(c.id)}">
      <span class="status-dot ${st}" title="${esc(c.status)}"></span><span class="t">${tx(c.title)}</span>
      <span class="d">${esc(shortTime(c.updated_at))}</span>
      <button class="icon-btn menu-btn" type="button" aria-label="Options for ${esc(c.title)}" data-menu="${esc(c.id)}">
        <svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></svg>
      </button></a>`;
  }
  nav.innerHTML = html;
}

$("history").addEventListener("click", (ev) => {
  const menu = ev.target.closest("[data-menu]");
  if (menu) { ev.preventDefault(); ev.stopPropagation(); openItemMenu(menu.dataset.menu, menu.closest(".h-item")); return; }
  const a = ev.target.closest(".h-item");
  if (a && !ev.target.closest("input")) { ev.preventDefault(); navigate(`/c/${a.dataset.id}`); }
});

function openItemMenu(id, item) {
  document.querySelector(".h-menu")?.remove();
  const m = document.createElement("div");
  m.className = "h-menu";
  m.innerHTML = `<button type="button" data-act="rename">Rename</button><button type="button" class="danger" data-act="delete">Delete</button>`;
  item.appendChild(m);
  m.addEventListener("click", (ev) => {
    ev.preventDefault(); ev.stopPropagation();
    const act = ev.target.dataset.act;
    m.remove();
    if (act === "rename") renameInline(id, item);
    if (act === "delete") confirmDelete(id);
  });
  setTimeout(() => document.addEventListener("click", () => m.remove(), { once: true }));
}

function renameInline(id, item) {
  const t = item.querySelector(".t");
  const input = document.createElement("input");
  input.value = t.textContent;
  t.replaceWith(input);
  input.focus(); input.select();
  const done = async (save) => {
    input.onblur = null;
    if (save && input.value.trim() && input.value.trim() !== t.textContent) {
      try { await api(`/conversations/${id}`, { method: "PATCH", body: { title: input.value.trim() } }); }
      catch (e) { toast(e.message); }
    }
    await loadHistory();
    if (S.id === id) refreshCrumb();
  };
  input.onkeydown = (e) => { if (e.key === "Enter") done(true); if (e.key === "Escape") done(false); };
  input.onblur = () => done(true);
  input.onclick = (e) => { e.preventDefault(); e.stopPropagation(); };
}

function confirmDelete(id) {
  const c = S.history.find((x) => x.id === id);
  $("confirm-title").textContent = "Delete this research?";
  $("confirm-text").textContent = `“${c ? c.title : ""}” will be removed from the history. Computations already done stay available to future researches.`;
  openModal("confirm");
  $("confirm-ok").onclick = async () => {
    closeModal("confirm");
    try {
      await api(`/conversations/${id}`, { method: "DELETE" });
      if (S.id === id) navigate("/");
      await loadHistory();
    } catch (e) { toast(e.message); }
  };
}

/* ---------- sidebar ---------- */

const mobile = () => matchMedia("(max-width: 900px)").matches;
function closeDrawer() { $("app").classList.remove("drawer"); $("scrim").hidden = true; }
$("collapse").onclick = () => { if (mobile()) closeDrawer(); else $("app").classList.add("collapsed"); };
$("open-sidebar").onclick = () => {
  if (mobile()) { $("app").classList.add("drawer"); $("scrim").hidden = false; }
  else $("app").classList.remove("collapsed");
};
$("scrim").onclick = closeDrawer;
$("new-chat").onclick = () => navigate("/");
$("results-btn").onclick = () => navigate("/results");
$("bench-btn").onclick = () => navigate("/benchmarks");
document.querySelector(".brand").addEventListener("click", (e) => { e.preventDefault(); navigate("/"); });

/* ---------- modals ---------- */

let lastFocus = null;
function openModal(id) { lastFocus = document.activeElement; $(id).hidden = false; $(id).querySelector("button")?.focus(); }
function closeModal(id) {
  $(id).hidden = true;
  if (id === "viewer-modal") $("viewer-body").innerHTML = "";
  lastFocus?.focus?.();
}
for (const m of document.querySelectorAll(".modal")) {
  m.addEventListener("click", (e) => { if (e.target === m || e.target.closest("[data-close]")) closeModal(m.id); });
}
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const open = [...document.querySelectorAll(".modal")].find((m) => !m.hidden);
  if (open) closeModal(open.id);
  else if (L.on && L.full && !L.hidden) labSetFull(false);
});
$("settings-btn").onclick = () => navigate("/settings");
$("theme-choice").addEventListener("change", (e) => applyTheme(e.target.value));
$("theme-btn").onclick = () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");

/* ---------- voice: dictation with Muse Voice Transcribe, the agent's voice from the browser ---------- */

const VOICE = { on: (() => { try { return localStorage.getItem("autolab-voice") === "on"; } catch { return false; } })(),
  spoken: new Set(), conv: null, fresh: false, queue: 0, rec: null };
const plainText = (s) => String(s || "").replace(/<[^>]+>/g, " ").replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
  .replace(/[*_`#>|]/g, " ").replace(/\s+/g, " ").trim();
function pickVoice() {
  // local voices only (installed on this computer): an online neural voice (Edge "Online (Natural)") is a remote AI
  // service, not a browser function, and is never used
  const vs = ("speechSynthesis" in window ? speechSynthesis.getVoices() : [])
    .filter((v) => v.localService && !/online|natural|neural|cloud/i.test(v.name));
  return vs.find((v) => /^en-US/i.test(v.lang)) || vs.find((v) => /^en/i.test(v.lang)) || null;
}
function say(text, important = false) {
  if (!VOICE.on || !("speechSynthesis" in window)) return;
  const t = plainText(text);
  if (!t || (!important && VOICE.queue > 2)) return;  // keep pace with the lab: skip a line rather than lag behind
  const u = new SpeechSynthesisUtterance(t.length > 280 ? `${t.slice(0, 277)}…` : t);
  const v = pickVoice();
  if (!v) {  // never let the browser fall back on its default voice, which may be an online one
    if (!say.warned && speechSynthesis.getVoices().length) {  // the list loads asynchronously: warn once it is there
      say.warned = true;
      toast("No local voice is installed on this computer: the agent stays silent.");
    }
    return;
  }
  u.voice = v;
  u.lang = v.lang;
  u.rate = 1.04;
  VOICE.queue++;
  u.onend = u.onerror = () => { VOICE.queue = Math.max(0, VOICE.queue - 1); };
  speechSynthesis.speak(u);
}
function hush() { if ("speechSynthesis" in window) speechSynthesis.cancel(); VOICE.queue = 0; }
function setVoice(on) {
  VOICE.on = on;
  try { localStorage.setItem("autolab-voice", on ? "on" : "off"); } catch { /* private window */ }
  if (!on) hush();
  const b = $("voice-btn");
  b.setAttribute("aria-pressed", String(on));
  b.title = `Agent voice: ${on ? "on" : "off"}`;
}
setVoice(VOICE.on);
$("voice-btn").onclick = () => { setVoice(!VOICE.on); if (VOICE.on) say("Voice on.", true); };

function voiceMessages(shown) {
  if (VOICE.conv !== S.id) {  // a conversation just opened: its past messages are not read, unless it was just asked
    VOICE.conv = S.id;
    if (!VOICE.fresh) { for (const m of shown) VOICE.spoken.add(m.id); return; }
  }
  VOICE.fresh = false;
  for (const m of shown) {
    if (VOICE.spoken.has(m.id)) continue;
    VOICE.spoken.add(m.id);
    if (m.kind === "report") say("The final report is ready.", true);
    else if (m.kind !== "notice") say(m.content, true);
  }
}

async function startDictation() {
  hush();
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { toast("This browser cannot use a microphone."); return; }
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } }); }
  catch { toast("The microphone is not available."); return; }
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/voice`);
  ws.binaryType = "arraybuffer";
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const src = ctx.createMediaStreamSource(stream);
  const proc = ctx.createScriptProcessor(4096, 1, 1);
  const mute = ctx.createGain();
  mute.gain.value = 0;
  const ratio = ctx.sampleRate / 16000, FRAME = 1280;  // 80 ms of 16 kHz PCM16
  let pending = new Int16Array(0);
  const start = $("prompt").value.trim();
  proc.onaudioprocess = (e) => {
    if (ws.readyState !== 1) return;
    const x = e.inputBuffer.getChannelData(0), n = Math.floor(x.length / ratio), out = new Int16Array(n);
    for (let i = 0; i < n; i++) {  // average each window: a simple low-pass before the 16 kHz resampling
      const a = Math.floor(i * ratio), b = Math.min(x.length, Math.floor((i + 1) * ratio));
      let sum = 0;
      for (let k = a; k < b; k++) sum += x[k];
      out[i] = Math.max(-1, Math.min(1, sum / Math.max(1, b - a))) * 0x7fff;
    }
    const all = new Int16Array(pending.length + out.length);
    all.set(pending); all.set(out, pending.length);
    let k = 0;
    for (; k + FRAME <= all.length; k += FRAME) ws.send(all.slice(k, k + FRAME).buffer);
    pending = all.slice(k);
  };
  src.connect(proc); proc.connect(mute); mute.connect(ctx.destination);
  ws.onmessage = (e) => {
    const d = JSON.parse(e.data);
    if (d.type === "partial" || d.type === "final") { $("prompt").value = start ? `${start} ${d.text}` : d.text; autosize(); }
    else if (d.type === "error") toast(`Dictation: ${d.message}.`);
    if (d.type === "done" || d.type === "error") ws.close();
  };
  ws.onerror = () => toast("Dictation: the voice relay cannot be reached.");
  const stopAudio = () => {
    try { proc.disconnect(); src.disconnect(); ctx.close(); } catch { /* already closed */ }
    stream.getTracks().forEach((t) => t.stop());
  };
  VOICE.rec = { ws, stopAudio, timer: setTimeout(() => stopDictation(), 30000) };
  $("mic").classList.add("recording");
  $("mic").title = "Stop dictation";
}
function stopDictation() {
  const r = VOICE.rec;
  if (!r) return;
  VOICE.rec = null;
  clearTimeout(r.timer);
  r.stopAudio();
  if (r.ws.readyState === 1) r.ws.send(JSON.stringify({ type: "stop" }));
  $("mic").classList.remove("recording");
  $("mic").title = "Dictate (Muse Voice Transcribe)";
  $("prompt").focus();
}
$("mic").onclick = () => (VOICE.rec ? stopDictation() : startDictation());

/* ---------- tutorial: how AutoLab works, six cards ---------- */

const TUT = [
  { title: "An autonomous materials researcher",
    text: "A researcher writes a goal in plain language. An AI agent runs the whole investigation in their place.",
    points: ["“Find a solid electrolyte that stays stable against lithium metal”", "Hypotheses, simulations, analysis and report, without supervision", "Built for industrial materials research; applied today to batteries"],
    art: `<svg viewBox="0 0 200 120"><rect x="14" y="30" width="82" height="40" rx="10"/><path d="M28 44h54M28 56h36"/><path d="M104 50h22" /><path d="M120 44l7 6-7 6"/>
      <circle cx="160" cy="50" r="7" fill="currentColor"/><ellipse cx="160" cy="50" rx="28" ry="10"/><ellipse cx="160" cy="50" rx="28" ry="10" transform="rotate(60 160 50)"/><ellipse cx="160" cy="50" rx="28" ry="10" transform="rotate(-60 160 50)"/>
      <path d="M40 96h120" stroke-dasharray="3 5"/></svg>` },
  { title: "Meta models at the core",
    text: "Muse Spark leads the research and sends its candidates to the simulation tools.",
    roles: [["Muse Spark", "proposes, decides, learns from failures, writes the report", "meta"],
      ["Muse Spark Open", "reviews each candidate independently", "meta"],
      ["Muse Glimmer", "summarizes each step in plain language", "meta"],
      ["UMA · Meta FAIR", "simulates the atoms for Muse Spark: structure, energy, ion motion", "meta"],
      ["GapModel · Materials Project", "band gaps and known phases, queried for Muse Spark", "tool"]],
    art: `<svg viewBox="0 0 200 120"><circle cx="100" cy="60" r="16" fill="currentColor" fill-opacity=".15"/><circle cx="100" cy="60" r="16"/>
      <circle cx="38" cy="26" r="9"/><circle cx="162" cy="26" r="9"/><circle cx="38" cy="94" r="9"/><circle cx="162" cy="94" r="9"/>
      <path d="M86 52 46 31M114 52l40-21M86 68 46 89M114 68l40 21"/><circle cx="100" cy="60" r="4" fill="currentColor"/></svg>` },
  { title: "From hypothesis to verdict",
    text: "Each candidate goes through filters from the cheapest to the most demanding.",
    points: ["Charge balance, and no recomputation of known materials", "Stability and band gap, computed by UMA and GapModel", "Domain tests: contact with the metal, ion motion, voltage"],
    art: `<svg viewBox="0 0 200 120"><path d="M30 18h140l-44 46v34l-52 14V64z"/>
      ${[48, 70, 92, 114, 136, 152].map((x, k) => `<circle cx="${x}" cy="${k % 2 ? 30 : 38}" r="3.5"/>`).join("")}
      <circle cx="94" cy="72" r="3.5"/><circle cx="106" cy="80" r="3.5"/><circle cx="100" cy="96" r="4" fill="currentColor"/></svg>` },
  { title: "It learns from its failures",
    text: "Every failure goes back to Muse Spark with its numbers. It explains the cause as a hypothesis and corrects the next round.",
    points: ["Three rounds of proposals", "Failures are data, never hidden", "Each correction is traced in the report"],
    art: `<svg viewBox="0 0 200 120"><path d="M64 60a36 36 0 0 1 66-20"/><path d="M136 60a36 36 0 0 1-66 20"/><path d="M124 30l7 11-13 2"/><path d="M76 90l-7-11 13-2"/>
      <circle cx="100" cy="60" r="6" fill="currentColor"/><path d="M152 60h28M20 60h28" stroke-dasharray="3 4"/></svg>` },
  { title: "One agent, three research areas",
    text: "Applied today to energy storage. Only the starting crystals and the tests change: the loop stays the same.",
    points: ["Lithium solid electrolytes: safer lithium-metal batteries", "Cobalt-free cathodes: without a critical metal", "Sodium solid electrolytes: beyond lithium"],
    art: `<svg viewBox="0 0 200 120"><rect x="6" y="30" width="58" height="56" rx="8"/><rect x="71" y="30" width="58" height="56" rx="8"/><rect x="136" y="30" width="58" height="56" rx="8"/>
      <text x="35" y="64" text-anchor="middle" font-size="16" fill="currentColor" stroke="none">Li⁺</text><text x="100" y="58" text-anchor="middle" font-size="12" fill="currentColor" stroke="none">cathode</text>
      <text x="100" y="72" text-anchor="middle" font-size="10" fill="currentColor" stroke="none">no Co</text>
      <text x="165" y="64" text-anchor="middle" font-size="16" fill="currentColor" stroke="none">Na⁺</text><path d="M35 94v8h130v-8M100 102v8"/></svg>` },
  { title: "Science you can check",
    text: "The rules are fixed in the code, never by the models. Every method is first tested on known materials.",
    points: ["Truth tests and blind benchmarks, failures kept", "Error bars and a literature check of the finalists", "Results, Benchmark & Tests and Settings pages"],
    art: `<svg viewBox="0 0 200 120"><path d="M24 100h156M24 100V16"/>
      ${[[52, 70, 12], [92, 52, 9], [132, 34, 10]].map(([x, y, e]) => `<path d="M${x} ${y - e}v${2 * e}M${x - 5} ${y - e}h10M${x - 5} ${y + e}h10"/><circle cx="${x}" cy="${y}" r="4" fill="currentColor"/>`).join("")}
      <path d="M150 74l9 9 17-19"/></svg>` },
];
let tutIndex = 0;
function renderTutorial() {
  const c = TUT[tutIndex];
  $("tut-art").innerHTML = c.art;
  $("tut-step").textContent = `Step ${tutIndex + 1} of ${TUT.length}`;
  $("tut-title").textContent = c.title;
  $("tut-text").textContent = c.text;
  $("tut-points").className = c.roles ? "tut-roles" : "tut-points";
  $("tut-points").innerHTML = c.roles
    ? c.roles.map(([m, r, k]) => `<li><span class="role-model ${k}">${esc(m)}</span><span>${esc(r)}</span></li>`).join("")
    : c.points.map((p) => `<li>${esc(p)}</li>`).join("");
  $("tut-dots").innerHTML = TUT.map((_, i) => `<i class="${i === tutIndex ? "on" : ""}"></i>`).join("");
  $("tut-prev").disabled = tutIndex === 0;
  $("tut-next").textContent = tutIndex === TUT.length - 1 ? "Done" : "Next";
}
$("tutorial-btn").onclick = () => { tutIndex = 0; renderTutorial(); openModal("tutorial"); };
$("tut-prev").onclick = () => { if (tutIndex > 0) { tutIndex--; renderTutorial(); } };
$("tut-next").onclick = () => { if (tutIndex < TUT.length - 1) { tutIndex++; renderTutorial(); } else closeModal("tutorial"); };

/* ---------- home ---------- */

const EXAMPLES = [  // config.REPLAY_EXAMPLES, word for word: each replays one finished research of its domain
  "Find new solid electrolytes for lithium batteries that conduct lithium as fast as their parent and stay stable against lithium metal.",
  "Find new cobalt-free cathodes for lithium-ion batteries that store more energy than LiFePO4.",
  "Find new sodium solid electrolytes that stay stable against sodium metal and let sodium ions move fast.",
];

function showHome() {
  stopTimers();
  S.id = null; S.view = null; S.events = []; S.next = 0; S.index = null;
  disposeViewers();
  document.querySelector(".main").classList.add("home");
  document.querySelector(".main").appendChild($("composer-wrap"));  // keep it: the page below is rebuilt
  $("crumb").textContent = "";
  $("view").innerHTML = `<section class="hero">
      <canvas id="sphere" width="336" height="336" aria-hidden="true"></canvas>
      <h1>What material shall we discover today?</h1>
      <p>Describe your scientific goal. AutoLab will investigate, evaluate and compare candidate materials.</p>
    </section>`;
  const hero = $("view").querySelector(".hero");
  hero.appendChild($("composer-wrap"));
  const ex = document.createElement("div");
  ex.className = "examples";
  ex.innerHTML = `<h2 class="try-title">Try with these sentences</h2>` +
    EXAMPLES.map((t, i) => `<button type="button" data-i="${i}">${tx(t)}</button>`).join("");
  ex.onclick = (e) => { const b = e.target.closest("button"); if (b) { $("prompt").value = EXAMPLES[+b.dataset.i]; autosize(); $("prompt").focus(); } };
  hero.appendChild(ex);
  setComposer("new");
  renderHistory();
  sphere.start($("sphere"));
  $("prompt").focus();
}

/* a slowly turning molecular sphere (decorative, light, stops when hidden or when motion is reduced) */
const sphere = {
  raf: 0,
  start(canvas) {
    const ctx = canvas.getContext("2d");
    const N = 54, pts = [];
    for (let i = 0; i < N; i++) {  // Fibonacci sphere
      const y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), th = i * 2.39996;
      pts.push([Math.cos(th) * r, y, Math.sin(th) * r, i % 9 === 0]);
    }
    const bonds = [];
    for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) {
      const d = Math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1], pts[i][2] - pts[j][2]);
      if (d < 0.42) bonds.push([i, j]);
    }
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let a = 0.6;
    const draw = () => {
      if (!canvas.isConnected) return;
      const css = getComputedStyle(document.documentElement);
      const accent = css.getPropertyValue("--accent").trim(), line = css.getPropertyValue("--border-strong").trim();
      const W = canvas.width, R = W * 0.38, c = W / 2;
      ctx.clearRect(0, 0, W, W);
      const ca = Math.cos(a), sa = Math.sin(a), tilt = 0.35;
      const P = pts.map(([x, y, z, hi]) => {
        const x1 = x * ca + z * sa, z1 = -x * sa + z * ca;
        const y1 = y * Math.cos(tilt) - z1 * Math.sin(tilt), z2 = y * Math.sin(tilt) + z1 * Math.cos(tilt);
        return [c + x1 * R, c + y1 * R, z2, hi];
      });
      ctx.lineWidth = 1.2;
      for (const [i, j] of bonds) {
        ctx.globalAlpha = 0.18 + 0.35 * ((P[i][2] + P[j][2]) / 2 + 1) / 2;
        ctx.strokeStyle = line;
        ctx.beginPath(); ctx.moveTo(P[i][0], P[i][1]); ctx.lineTo(P[j][0], P[j][1]); ctx.stroke();
      }
      for (const [x, y, z, hi] of [...P].sort((p, q) => p[2] - q[2])) {
        const depth = (z + 1) / 2;
        ctx.globalAlpha = 0.35 + 0.65 * depth;
        ctx.fillStyle = accent;
        ctx.beginPath(); ctx.arc(x, y, (hi ? 6.5 : 3.6) * (0.65 + 0.5 * depth), 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalAlpha = 1;
      if (!still && !document.hidden) a += 0.0032;
      sphere.raf = requestAnimationFrame(draw);
    };
    cancelAnimationFrame(sphere.raf);
    draw();
  },
};

/* ---------- composer ---------- */

function autosize() { const t = $("prompt"); t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 220) + "px"; }
$("prompt").addEventListener("input", autosize);
$("prompt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("composer").requestSubmit(); }
});

function setComposer(mode) {  // new | followup | running | stopping
  const f = $("composer"), t = $("prompt");
  f.dataset.mode = mode;
  f.classList.toggle("stop", mode === "running" || mode === "stopping");
  t.disabled = mode === "running" || mode === "stopping";
  $("send").disabled = mode === "stopping" || S.sending;
  $("send").setAttribute("aria-label", mode === "running" ? "Stop the research" : "Send");
  t.placeholder = mode === "new" ? "Describe the material you are looking for…"
    : mode === "followup" ? "Ask a follow-up question about this research…"
      : mode === "stopping" ? "Stopping the research…" : "AutoLab is researching… you can stop it at any time.";
}

$("composer").addEventListener("submit", async (e) => {
  e.preventDefault();
  const mode = $("composer").dataset.mode;
  if (mode === "running") return stopResearch();
  if (mode === "stopping" || S.sending) return;
  const text = $("prompt").value.trim();
  if (!text) return;
  if (VOICE.rec) stopDictation();
  VOICE.fresh = true;
  S.sending = true;
  $("prompt").value = ""; autosize();
  setComposer(mode);
  try {
    if (mode === "new") {
      showPending(text, "Understanding your goal…");
      const v = await api("/conversations", { method: "POST", body: { message: text } });
      history.pushState({}, "", `/c/${v.conversation.id}`);
      S.sending = false;
      await loadHistory();
      S.autoplay = true;
      showConversation(v);
    } else {
      appendPending(text);
      const v = await api(`/conversations/${S.id}/messages`, { method: "POST", body: { message: text } });
      S.sending = false;
      S.view = v;
      renderThread();
    }
  } catch (err) {
    S.sending = false;
    toast(err.message);
    $("prompt").value = text; autosize();
    if (mode === "new") showHome(); else renderThread();
  }
  setComposer(composerMode());
});

async function stopResearch() {
  if (!S.id) return;
  setComposer("stopping");
  try { S.view = await api(`/conversations/${S.id}/cancel`, { method: "POST" }); renderThread(); }
  catch (e) { toast(e.message); setComposer(composerMode()); }
}

function composerMode() {
  if (!S.view) return "new";
  const st = S.view.conversation.status;
  return st === "stopping" ? "stopping" : ACTIVE.has(st) ? "running" : "followup";
}

/* ---------- conversation ---------- */

function leaveHome() {
  document.querySelector(".main").classList.remove("home");
  document.querySelector(".main").appendChild($("composer-wrap"));
  cancelAnimationFrame(sphere.raf);
}

function showPending(text, label) {
  leaveHome();
  $("view").innerHTML = `<div class="thread">${userMsg(text)}${aiBlock(`<div class="thinking" aria-label="${esc(label)}"><i></i><i></i><i></i></div> <span class="muted">${esc(label)}</span>`)}</div>`;
}

function appendPending(text) {
  const th = $("view").querySelector(".thread");
  th.insertAdjacentHTML("beforeend", userMsg(text) + aiBlock(`<div class="thinking"><i></i><i></i><i></i></div>`, "pending"));
  scrollBottom();
}

async function openConversation(id) {
  stopTimers();
  leaveHome();
  const other = S.id !== id;
  if (other) { S.events = []; S.next = 0; S.index = null; S.tab = "progress"; disposeViewers(); }
  S.id = id;
  renderHistory();
  if (other || !$("view").querySelector(".thread")) {
    $("view").innerHTML = loadingHTML("Opening the research…");
    setComposer("followup");
  }
  try {
    const [v, p] = await Promise.all([api(`/conversations/${id}`), api(`/conversations/${id}/progress?after=0`).catch(() => null)]);
    if (S.id !== id) return;  // another research was opened meanwhile
    showConversation(v, p);
  } catch (e) {
    $("view").innerHTML = `<div class="thread"><div class="notice warn">This research could not be opened: ${esc(e.message)}.</div></div>`;
    setComposer("new");
  }
}

async function showConversation(v, pre = null) {
  S.view = v;
  S.id = v.conversation.id;
  refreshCrumb();
  renderHistory();
  if (pre) { S.events = pre.events; S.next = pre.next; S.view.steps = pre.steps; }
  else if (v.events_count) await fetchProgress(true);
  if (!ACTIVE.has(v.conversation.status) && v.files.includes("index.json") && !S.index) {
    try { S.index = await api(`/conversations/${S.id}/files/index.json`); } catch { S.index = null; }
  }
  const reused = v.conversation.scope && v.conversation.scope.reused_from;
  const ask = new URLSearchParams(location.search);  // ?watch[=speed]: play a finished research again (filming)
  const play = ACTIVE.has(v.conversation.status) ? "live"
    : (S.autoplay && reused) || ask.has("watch") ? (S.events.length ? "watch" : null) : null;
  S.autoplay = false;
  if (ask.has("watch") && +ask.get("watch")) { L.speed = Math.max(1, Math.min(4, +ask.get("watch"))); L.speedSet = true; }
  if (play) {
    await labStart(play);
    if (ask.get("lab") === "inline" && L.full) labSetFull(false);  // ?watch&lab=inline: the replay inside the chat
    if (ask.has("watch")) history.replaceState({}, "", location.pathname);
    setComposer(composerMode());
    return;
  }
  renderThread();
  setComposer(composerMode());
  scrollBottom(true);
}

function refreshCrumb() {
  const c = S.history.find((x) => x.id === S.id);
  $("crumb").textContent = chem(c ? c.title : S.view?.conversation.title || "");
  document.title = `${$("crumb").textContent || "AutoLab"} · AutoLab`;
}

async function fetchProgress(all = false, quiet = false) {
  const p = await api(`/conversations/${S.id}/progress?after=${all ? 0 : S.next}`, { quiet });
  if (all) S.events = p.events; else S.events.push(...p.events);
  S.next = p.next;
  S.view.steps = p.steps;
  return p;
}

function startPolling() {  // fallback when the WebSocket is not available
  clearInterval(S.timer);
  const id = S.id;
  S.timer = setInterval(async () => {
    if (S.id !== id) return clearInterval(S.timer);
    try {
      const before = S.next;
      const p = await fetchProgress(false, true);
      if (L.on) labEnqueue(p.events);
      if (p.status !== S.view.conversation.status) {
        S.view.conversation.status = p.status;
        setComposer(composerMode());
        loadHistory();
      }
      if (!ACTIVE.has(p.status)) {  // finished: the summary, the report and the 3D files are now stored
        clearInterval(S.timer);
        const v = await api(`/conversations/${id}`);
        S.view = v;
        if (v.files.includes("index.json")) { try { S.index = await api(`/conversations/${id}/files/index.json`); } catch { /* none */ } }
        if (!L.on) { renderThread(); scrollBottom(); }
        setComposer(composerMode());
      } else if (S.next !== before && !L.on) renderResearch();
    } catch { /* a missed poll is retried at the next tick */ }
  }, POLL_MS);
}

function scrollBottom(instant = false) {
  const v = $("view");
  requestAnimationFrame(() => v.scrollTo({ top: v.scrollHeight, behavior: instant ? "auto" : "smooth" }));
}

/* ---------- thread rendering ---------- */

const COPY_ICON = `<svg viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/></svg>`;
const userMsg = (t) => `<div class="msg user"><div class="bubble">${tx(t)}</div>
  <button class="copy-btn" type="button" data-copy="${esc(t)}" title="Copy the text" aria-label="Copy the text">${COPY_ICON}</button></div>`;

/* copy a sent request in one click: the exact text (plain digits), so that it can be sent again and be recognised */
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* no clipboard API (http, old browser) */ }
  const area = document.createElement("textarea");
  area.value = text;
  area.style.cssText = "position:fixed;left:-9999px;top:0";
  document.body.appendChild(area);
  area.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch { ok = false; }
  area.remove();
  return ok;
}
$("view").addEventListener("click", async (ev) => {
  const b = ev.target.closest("[data-copy]");
  if (!b) return;
  const ok = await copyText(b.dataset.copy);
  b.innerHTML = ok ? CHECK : COPY_ICON;
  b.classList.toggle("done", ok);
  toast(ok ? "Text copied" : "The text could not be copied");
  setTimeout(() => { b.innerHTML = COPY_ICON; b.classList.remove("done"); }, 1600);
});
const aiBlock = (html, cls = "") => `<div class="msg ai ${cls}"><div class="avatar">${AI_ICON}</div><div class="body">${html}</div></div>`;

function md(text) {
  const html = window.marked ? window.marked.parse(text || "", { gfm: true }) : `<p>${esc(text)}</p>`;
  return chemHTML(window.DOMPurify ? window.DOMPurify.sanitize(html) : html);
}

function renderThread() {
  const v = S.view;
  if (!v) return;
  const parts = [];
  let researchPlaced = false;
  const hasResearch = v.steps && v.steps.length;
  const lab = L.on && !L.hidden && L.convId === S.id;
  const inline = lab && (L.mode === "live" || !L.full);  // the lab inside the chat
  const hideFinal = lab && L.mode === "live";  // while a research runs, its results come at the end
  const place = () => {
    if (researchPlaced) return;
    parts.push(inline ? aiBlock(`<div id="lab-slot"></div>`, "lab-msg") : aiBlock(`<div id="research"></div>`));
    researchPlaced = true;
  };
  const shown = [];
  for (const m of v.messages) {
    if (m.role === "user") { parts.push(userMsg(m.content)); continue; }
    const before = parts.length;
    renderOne(m);
    if (parts.length > before) shown.push(m);
  }
  function renderOne(m) {
    if (m.kind === "scope") {
      parts.push(aiBlock(`${who("Muse Spark", "read the request", "think")}<div class="prose">${md(m.content)}</div>`));
      if (hasResearch && !(v.messages.some((x) => x.data && x.data.action === "reused"))) place();
    } else if (m.kind === "notice") {
      const newChat = m.data && m.data.action === "new_chat", reused = m.data && m.data.action === "reused";
      if (hideFinal && !reused && !newChat) return;
      parts.push(aiBlock(`<div class="notice${newChat ? " warn" : reused ? " reused" : ""}">${tx(m.content)}${newChat
        ? `<div class="actions"><button class="primary-btn" type="button" data-newchat="${m.id}">New chat</button></div>` : ""}</div>`));
      if (reused && hasResearch) place();
    } else if (m.kind === "summary") {
      if (hideFinal) return;
      parts.push(aiBlock(`<div class="prose summary"><p>${tx(m.content)}</p></div>`));
    } else if (m.kind === "report") {
      if (hideFinal) return;
      parts.push(aiBlock(`${who("Muse Spark", "wrote the report from the numbers computed by the code", "think")}${reportBlock(m)}`));
    } else {
      parts.push(aiBlock(`<div class="prose">${md(m.content)}</div>`));
    }
  }
  voiceMessages(shown);
  if ((hasResearch || inline) && !researchPlaced) place();
  $("view").innerHTML = `<div class="thread">${parts.join("")}</div>`;
  labPlace();
  renderResearch();
  bindReport();
  for (const b of $("view").querySelectorAll("[data-newchat]")) {
    b.onclick = () => {
      const last = [...S.view.messages].reverse().find((m) => m.role === "user");
      navigate("/");
      if (last) { $("prompt").value = last.content; autosize(); }
    };
  }
}

const who = (model, what, kind) => `<div class="who"><span class="model ${kind}">${tx(model)}</span><span>${tx(what)}</span></div>`;

/* ---------- research block: progress, candidates, visualizations, notes ---------- */

function aggregate() {
  const cands = new Map(), notes = [];
  const get = (id) => { if (!cands.has(id)) cands.set(id, { id }); return cands.get(id); };
  for (const e of S.events) {
    const d = e.data || {}, k = `${e.type}/${e.step}`, c = e.candidate_id ? get(e.candidate_id) : null;
    if (c && d.formula) c.formula = d.formula;
    if (k === "candidate/hull") c.e_hull = d.e_hull;
    else if (k === "candidate/bandgap") { c.gap = d.gap_optb88; c.gap_mbj = d.gap_mbj; }
    else if (k === "candidate/done") { c.status = d.status; c.rejected_at = d.rejected_at; c.reason = d.reason; }
    else if (k === "candidate/electrodes:done") { c.window = d.window; c.passivation = d.passivation; if (d.excluded) c.excluded = "electrodes"; }
    else if (k === "candidate/molecular_dynamics:done") {
      c.ratio = d.ratio; c.verdict = d.verdict; c.D = d.D_cm2_per_s;
      if (d.conduction === "excluded") c.excluded = "diffusion";
    } else if (k === "candidate/candidate_analyses:done") c.review = d;
    else if (k === "candidate/voltage") {
      c.voltage = d.voltage_V; c.capacity = d.capacity_mAh_g; c.energy = d.energy_density_Wh_kg; c.volume = d.volume_change_pct;
    }
    else if (k === "llm/proposal" && d.reply) notes.push({ kind: "proposal", data: d.reply });
    else if (k === "llm/analysis" && d.reply) notes.push({ kind: "analysis", data: d.reply });
    else if (k === "llm/md_selection" && d.reply) notes.push({ kind: "md", data: d.reply });
    else if (k === "loop/feedback" && (d.results || []).length) notes.push({ kind: "feedback", data: d });
    else if (k === "llm/summary" && d.text) notes.push({ kind: "summary", data: d });
  }
  // the stored result, once the research is finished, is the source of truth
  return { cands: [...cands.values()].filter((c) => c.formula || c.e_hull !== undefined || c.status), notes };
}

function stateLabel(s) {
  return { pending: "waiting", running: "in progress", done: "done", failed: "failed", skipped: "not needed", interrupted: "interrupted" }[s] || s;
}

function renderResearch() {
  const box = $("research");
  if (!box || !S.view) return;
  const st = S.view.conversation.status;
  const { cands, notes } = aggregate();
  const badge = { queued: "Starting", running: "In progress", stopping: "Stopping", done: "Complete", interrupted: "Interrupted", error: "Stopped on an error" }[st] || st;
  const tabs = [["progress", "Progress"], ["candidates", "Candidates", cands.length], ["viz", "Visualizations"], ["notes", "Scientific notes", notes.length]];
  box.innerHTML = `<section class="research">
    <div class="research-head"><span class="title">Research</span>
      <span class="elapsed">${esc(elapsed())}</span>
      ${!ACTIVE.has(st) && S.events.length ? `<button class="ghost-btn watch" type="button" id="watch-agent"><svg viewBox="0 0 24 24"><path d="M8 6l10 6-10 6z"/></svg><span>${L.on && L.convId === S.id ? (L.hidden ? "Resume watching" : "Open the lab") : "Watch the agent at work"}</span></button>` : ""}
      <span class="badge ${ACTIVE.has(st) ? (st === "stopping" ? "stopping" : "running") : st}">${esc(badge)}</span></div>
    <div class="tabs" role="tablist">${tabs.map(([k, l, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${S.tab === k}">${l}${n ? `<span class="count">${n}</span>` : ""}</button>`).join("")}</div>
    <div class="tab-panel" id="tab-panel"></div></section>`;
  const watch = $("watch-agent");
  if (watch) watch.onclick = () => (L.on && L.convId === S.id ? labResume() : labStart("watch"));
  box.querySelector(".tabs").onclick = (e) => {
    const b = e.target.closest("[data-tab]");
    if (b) { S.tab = b.dataset.tab; renderResearch(); }
  };
  const panel = $("tab-panel");
  disposeViewers();
  if (S.tab === "progress") panel.innerHTML = stepsHTML(S.view.steps || []);
  else if (S.tab === "candidates") { panel.innerHTML = candidatesHTML(cands); bindCandidateRows(panel); }
  else if (S.tab === "notes") panel.innerHTML = notesHTML(notes);
  else renderViz(panel, cands);
}

function elapsed() {
  const c = S.view.conversation;
  if (!c.created_at) return "";
  let s;
  if (!ACTIVE.has(c.status) && S.events.length > 1) {  // working time from the events; pauses over 30 min (stages rerun later) left out
    const ts = S.events.map((e) => Date.parse(e.timestamp)).filter((x) => !Number.isNaN(x));
    s = Math.round(ts.slice(1).reduce((sum, t, i) => sum + Math.min(Math.max(0, t - ts[i]), 1800e3), 0) / 1000);
  } else s = Math.max(0, Math.round(((ACTIVE.has(c.status) ? Date.now() : Date.parse(c.updated_at)) - Date.parse(c.created_at)) / 1000));
  return s < 60 ? `${s} s` : s < 3600 ? `${Math.floor(s / 60)} min ${s % 60 ? `${s % 60} s` : ""}` : `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`;
}

function stepsHTML(steps) {
  if (!steps.length) return `<p class="empty">The research has not started yet.</p>`;
  return `<ol class="steps">${steps.map((s) => `<li class="step ${s.state}">
      <span class="ic">${s.state === "done" ? CHECK : s.state === "failed" ? CROSS : s.state === "interrupted" ? PAUSE : ""}</span>
      <div><div class="lbl"><span class="name">${tx(s.label)}</span><span class="state">${esc(stateLabel(s.state))}</span></div>
        ${s.detail ? `<div class="detail">${tx(s.detail)}</div>` : ""}
        <details><summary>Why this step</summary><p>${tx(s.why)}</p></details></div></li>`).join("")}</ol>`;
}

const fmt = (x, d = 3) => (x === undefined || x === null ? "—" : Number(x).toFixed(d));
function statusChip(c) {
  if (c.excluded) return `<span class="chip bad">excluded (${esc(c.excluded)})</span>`;
  if (c.status === "passed") return `<span class="chip good">passed</span>`;
  if (c.status === "rejected") return `<span class="chip bad" title="${esc(c.reason)}">rejected: ${esc(c.rejected_at)}</span>`;
  if (c.status === "interrupted") return `<span class="chip warn">interrupted</span>`;
  if (c.status) return `<span class="chip warn">${esc(c.status)}</span>`;
  return `<span class="chip">in progress</span>`;
}

function candidatesHTML(cands) {
  if (!cands.length) return `<p class="empty">Candidates appear here as soon as they are built.</p>`;
  if (domainOf() === "cathode") {
    return `<div class="table-scroll"><table class="data"><thead><tr><th>Material</th><th>E<sub>hull</sub> (eV/atom)</th>
      <th>Voltage (V)</th><th>Capacity (mAh/g)</th><th>Energy density (Wh/kg)</th><th>Volume change (%)</th><th>Status</th></tr></thead><tbody>
      ${cands.map((c) => `<tr class="${hasStructure(c.id) ? "clickable" : ""}" data-id="${esc(c.id)}">
        <td class="formula">${tx(c.formula || c.id)}</td><td class="num">${fmt(c.e_hull)}</td><td class="num">${fmt(c.voltage, 2)}</td>
        <td class="num">${fmt(c.capacity, 0)}</td><td class="num">${fmt(c.energy, 0)}</td><td class="num">${fmt(c.volume, 1)}</td>
        <td>${statusChip(c)}</td></tr>`).join("")}</tbody></table></div>
      <p class="viewer-cap">${S.index ? "Click a material to see its crystal structure in 3D." : "3D structures become available when the research is finished."}
      Voltage: average over the whole charge, vs Li/Li⁺. Energy density = voltage × theoretical capacity, of the cathode material alone.</p>`;
  }
  return `<div class="table-scroll"><table class="data"><thead><tr><th>Material</th><th>E<sub>hull</sub> (eV/atom)</th><th>Band gap (eV)</th>
    <th>Window (V)</th><th>${ionOf(domainOf())} metal</th><th>D / D(parent)</th><th>Status</th></tr></thead><tbody>
    ${cands.map((c) => `<tr class="${hasStructure(c.id) ? "clickable" : ""}" data-id="${esc(c.id)}">
      <td class="formula">${tx(c.formula || c.id)}</td><td class="num">${fmt(c.e_hull)}</td><td class="num">${fmt(c.gap, 2)}</td>
      <td class="num">${c.window ? (c.window.stable ? `${fmt(c.window.v_low, 2)}–${fmt(c.window.v_high, 2)}` : "zero width") : "—"}</td>
      <td>${esc(c.passivation || "—")}</td>
      <td class="num">${c.ratio !== undefined ? `${fmt(c.ratio, 2)} <span class="muted">(${esc(c.verdict)})</span>` : "—"}</td>
      <td>${statusChip(c)}</td></tr>`).join("")}</tbody></table></div>
    <p class="viewer-cap">${S.index ? "Click a material to see its crystal structure in 3D." : "3D structures become available when the research is finished."}
    E<sub>hull</sub>: energy above the convex hull (≤ 0.05 kept). D / D(parent): ${ionName(domainOf())} diffusion relative to the parent crystal at 600 K.</p>`;
}

function hasStructure(id) { return !!(S.index && S.index.structures.find((s) => s.id === id)); }
function bindCandidateRows(panel) {
  for (const tr of panel.querySelectorAll("tr.clickable")) tr.onclick = () => openStructure(tr.dataset.id);
}

function notesHTML(notes) {
  if (!notes.length) return `<p class="empty">Explanations of the research appear here as it progresses.</p>`;
  const sub = (s) => `${tx(s.remove)} → ${tx(s.add)} ×${tx(s.count)}${s.li_vacancies ? `, −${s.li_vacancies} Li` : ""}`;
  return `<div class="notes">${notes.map((n) => {
    if (n.kind === "proposal") return `<div class="note"><h4>Hypothesis</h4><p>${tx(n.data.hypothesis)}</p>
      <ul>${(n.data.proposals || []).map((p) => `<li><span class="formula">${sub(p.substitution || {})}</span> — ${tx(p.rationale)}</li>`).join("")}</ul></div>`;
    if (n.kind === "feedback") return `<div class="note"><h4>Slow tests of round ${tx(n.data.iteration)} (sent back to the agent)</h4>
      <ul>${n.data.results.map((f) => `<li class="${f.outcome === "failed" ? "neg" : "pos"}">${tx(f.message)}</li>`).join("")}</ul></div>`;
    if (n.kind === "analysis") return `<div class="note"><h4>Interpretation</h4>${(n.data.failure_analysis || []).length ? `<p><b>Reading of the failures (hypotheses, not measurements):</b></p>
      <ul>${n.data.failure_analysis.map((x) => `<li><b>${tx(x.id)}</b>: ${tx(String(x.hypothesis || "").replace(/^\s*hypothesis\s*:\s*/i, ""))} <i>Correction:</i> ${tx(String(x.correction || "").replace(/^\s*correction\s*:\s*/i, ""))}</li>`).join("")}</ul>` : ""}<ul>${(n.data.lessons || []).map((l) => `<li>${tx(l)}</li>`).join("")}</ul>
      ${n.data.next_direction ? `<p><b>Next:</b> ${tx(n.data.next_direction)}</p>` : ""}</div>`;
    if (n.kind === "md") return `<div class="note"><h4>Why these candidates are simulated</h4><p>${tx(n.data.rationale)}</p></div>`;
    return `<div class="note"><h4>Summary</h4><p>${tx(n.data.text)}</p></div>`;
  }).join("")}</div>`;
}

/* ---------- charts (inline SVG: title, axes with units, threshold, explanation) ---------- */

function barChart({ title, rows, unit, threshold, better, caption, digits = 3 }) {
  if (!rows.length) return "";
  const W = 640, rowH = 22, L = 150, R = 60, T = 8, H = T + rows.length * rowH + 28;
  const vals = rows.map((r) => r.v).concat(threshold ?? []);
  const lo = Math.min(0, ...vals), hi = Math.max(...vals, 0) * 1.08 || 1;
  const X = (v) => L + ((v - lo) / (hi - lo)) * (W - L - R);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title)}">`;
  s += `<line class="axis" x1="${X(0)}" y1="${T}" x2="${X(0)}" y2="${H - 24}"/>`;
  rows.forEach((r, i) => {
    const y = T + i * rowH + 4, ok = better === "low" ? r.v <= threshold : r.v >= threshold;
    s += `<text class="lbl" x="${L - 8}" y="${y + 11}" text-anchor="end">${tx(r.label)}</text>`;
    s += `<rect class="${ok ? "bar-good" : "bar-bad"}" x="${Math.min(X(0), X(r.v))}" y="${y}" width="${Math.max(1.5, Math.abs(X(r.v) - X(0)))}" height="${rowH - 9}" rx="3"/>`;
    s += `<text x="${Math.max(X(0), X(r.v)) + 5}" y="${y + 11}">${Number(r.v).toFixed(digits)}</text>`;
  });
  if (threshold !== undefined) s += `<line class="threshold" x1="${X(threshold)}" y1="${T}" x2="${X(threshold)}" y2="${H - 24}"/><text x="${X(threshold) + 4}" y="${H - 26}">limit ${threshold}</text>`;
  s += `<text x="${W - R}" y="${H - 6}" text-anchor="end">${esc(unit)}</text></svg>`;
  return `<figure class="chart"><h4>${esc(title)}</h4>${s}<figcaption>${esc(caption)}</figcaption></figure>`;
}

function ratioChart(cands) {
  const rows = cands.filter((c) => c.ratio !== undefined && c.ratio !== null);
  if (!rows.length) return "";
  const W = 640, rowH = 24, L = 150, R = 30, T = 10, H = T + rows.length * rowH + 30;
  const hi = Math.max(2, ...rows.map((r) => r.ratio * 1.25));
  const X = (v) => L + (v / hi) * (W - L - R);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Lithium diffusion relative to the parent">`;
  s += `<line class="axis" x1="${L}" y1="${H - 26}" x2="${W - R}" y2="${H - 26}"/><line class="threshold" style="stroke:var(--muted)" x1="${X(1)}" y1="${T}" x2="${X(1)}" y2="${H - 26}"/>`;
  rows.forEach((r, i) => {
    const y = T + i * rowH + 10;
    s += `<text class="lbl" x="${L - 8}" y="${y + 4}" text-anchor="end">${tx(r.formula || r.id)}</text>`;
    s += `<circle cx="${X(r.ratio)}" cy="${y}" r="4.5" fill="${r.excluded ? "var(--bad)" : "var(--accent)"}" stroke="none"/>`;
    s += `<text x="${X(r.ratio) + 8}" y="${y + 4}">${r.ratio.toFixed(2)} · ${esc(r.verdict || "")}</text>`;
  });
  s += `<text x="${X(1)}" y="${H - 10}" text-anchor="middle">1 = same as parent</text><text x="${W - R}" y="${H - 10}" text-anchor="end">D / D(parent)</text></svg>`;
  return `<figure class="chart"><h4>Lithium diffusion relative to the parent crystal (600 K)</h4>${s}
    <figcaption>Molecular dynamics, two runs of 40 ps per structure. Around 1: tied with the parent within the uncertainty; a candidate clearly below, or whose framework falls apart, is excluded.</figcaption></figure>`;
}

function renderViz(panel, cands) {
  const named = (c) => c.formula || c.id;
  const eh = cands.filter((c) => c.e_hull !== undefined && c.e_hull !== null).map((c) => ({ label: named(c), v: c.e_hull }));
  const gp = cands.filter((c) => c.gap !== undefined && c.gap !== null).map((c) => ({ label: named(c), v: c.gap }));
  let html = `<div class="viz-grid">`;
  if (domainOf() === "cathode") {
    const vt = cands.filter((c) => c.voltage != null).map((c) => ({ label: named(c), v: c.voltage }));
    const en = cands.filter((c) => c.energy != null).map((c) => ({ label: named(c), v: c.energy }));
    html += barChart({ title: "Thermodynamic stability", rows: eh, unit: "energy above the hull (eV/atom)", threshold: 0.08, better: "low",
      caption: "Energy a crystal would release by decomposing into the stable known phases. At or below 0.08 eV/atom (dashed line) it is kept." }) || "";
    html += barChart({ title: "Average voltage", rows: vt, unit: "V vs Li/Li⁺", threshold: 3, better: "high", digits: 2,
      caption: "Average voltage over the whole charge. Kept between 3.0 V (dashed line) and 4.8 V." }) || "";
    html += barChart({ title: "Energy density", rows: en, unit: "Wh/kg (voltage × capacity)", digits: 0,
      caption: "Energy stored per kilogram of cathode material: the ranking criterion." }) || "";
    if (!eh.length) html += `<div class="unavailable">Charts appear as soon as the first structures are evaluated.</div>`;
    html += `<div id="viz-3d"></div><div id="viz-md"></div></div>`;
    panel.innerHTML = html;
    render3DSection($("viz-3d"));
    $("viz-md").innerHTML = "";
    return;
  }
  html += barChart({ title: "Thermodynamic stability", rows: eh, unit: "energy above the hull (eV/atom)", threshold: 0.05, better: "low",
    caption: "Energy a crystal would release by decomposing into known phases. At or below 0.05 eV/atom (dashed line) it is kept as possibly synthesizable." }) || "";
  html += barChart({ title: "Electronic band gap", rows: gp, unit: "band gap (eV)", threshold: 2, better: "high", digits: 2,
    caption: "An electrolyte must block electrons: candidates need a predicted gap of at least 2 eV (dashed line)." }) || "";
  html += ratioChart(cands);
  if (!eh.length && !gp.length) html += `<div class="unavailable">Charts appear as soon as the first structures are evaluated.</div>`;
  html += `<div id="viz-3d"></div><div id="viz-md"></div></div>`;
  panel.innerHTML = html;
  render3DSection($("viz-3d"));
  renderMDSection($("viz-md"));
}

/* ---------- 3D: crystal structures with a CPK legend ---------- */

const CPK = { Li: "#CC80FF", Na: "#AB5CF2", Mg: "#8AFF00", Al: "#BFA6A6", Si: "#F0C8A0", P: "#FF8000", S: "#FFFF30",
  Cl: "#1FF01F", O: "#FF0D0D", F: "#90E050", Br: "#A62929", I: "#940094", Se: "#FFA100", Ge: "#668F8F",
  As: "#BD80E3", Sb: "#9E63B5", Sn: "#668080", Fe: "#E06633", Mn: "#9C7AC7", Co: "#F090A0", N: "#3050F8", C: "#909090",
  Ni: "#50D050", Ti: "#BFC2C7", V: "#A6A6AB", Zr: "#94E0E0", Cr: "#8A99C7", Cu: "#C88033", Zn: "#7D80B0", Nb: "#73C2C9",
  Mo: "#54B5B5", W: "#2194D6", Ca: "#3DFF00", K: "#8F40D4", Ga: "#C28F8F", B: "#FFB5B5", Sc: "#E6E6E6", Y: "#94FFFF" };
const NAMES = { Li: "lithium", Na: "sodium", Mg: "magnesium", Al: "aluminium", Si: "silicon", P: "phosphorus", S: "sulfur",
  Cl: "chlorine", O: "oxygen", F: "fluorine", Br: "bromine", I: "iodine", Se: "selenium", Ge: "germanium", As: "arsenic",
  Sb: "antimony", Sn: "tin", Fe: "iron", Mn: "manganese", Co: "cobalt", N: "nitrogen", C: "carbon", Ni: "nickel",
  Ti: "titanium", V: "vanadium", Zr: "zirconium", Cr: "chromium", Cu: "copper", Zn: "zinc", Nb: "niobium", Mo: "molybdenum",
  W: "tungsten", Ca: "calcium", K: "potassium", Ga: "gallium", B: "boron", Sc: "scandium", Y: "yttrium" };

function legendHTML(elements, extra = "") {
  return `<div class="legend">${[...elements].map((el) => `<span><i style="background:${CPK[el] || "#999"}"></i>${esc(el)} · ${esc(NAMES[el] || el)}</span>`).join("")}${extra}</div>`;
}

function viewerBg() { return getComputedStyle(document.documentElement).getPropertyValue("--viewer-bg").trim(); }
function disposeViewers() {
  clearInterval(S.mdTimer); S.mdTimer = null;
  for (const v of S.viewers) { try { v.clear(); } catch { /* gone */ } }
  S.viewers = [];
}
function newViewer(el) {
  if (!window.$3Dmol) { el.innerHTML = `<div class="unavailable">The 3D viewer could not be loaded (network).</div>`; return null; }
  const v = window.$3Dmol.createViewer(el, { backgroundColor: viewerBg() });
  S.viewers.push(v);
  return v;
}

function drawCell(v, cell) {
  const [a, b, c] = cell;
  const P = (i, j, k) => ({ x: a[0] * i + b[0] * j + c[0] * k, y: a[1] * i + b[1] * j + c[1] * k, z: a[2] * i + b[2] * j + c[2] * k });
  const edges = [[0, 0, 0, 1, 0, 0], [0, 1, 0, 1, 0, 0], [0, 0, 1, 1, 0, 0], [0, 1, 1, 1, 0, 0], [0, 0, 0, 0, 1, 0], [1, 0, 0, 0, 1, 0],
    [0, 0, 1, 0, 1, 0], [1, 0, 1, 0, 1, 0], [0, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 1], [0, 1, 0, 0, 0, 1], [1, 1, 0, 0, 0, 1]];
  for (const [i, j, k, di, dj, dk] of edges) v.addLine({ start: P(i, j, k), end: P(i + di, j + dj, k + dk), color: "#8a94a6", dashed: false });
}

function xyz(symbols, positions) {
  return `${symbols.length}\n\n${symbols.map((s, i) => `${s} ${positions[i].map((x) => Number(x).toFixed(3)).join(" ")}`).join("\n")}\n`;
}

function drawCrystal(v, st, big = false) {
  v.addModel(xyz(st.symbols, st.positions), "xyz");
  v.setStyle({}, { sphere: { scale: big ? 0.34 : 0.3, colorscheme: "Jmol" }, stick: { radius: 0.1, colorscheme: "Jmol" } });
  if (st.highlight) v.setStyle({ elem: st.highlight }, { sphere: { scale: 0.48, colorscheme: "Jmol" }, stick: { radius: 0.1, colorscheme: "Jmol" } });
  drawCell(v, st.cell);
  v.zoomTo(); v.render();
}

function render3DSection(box) {
  if (!S.index || !S.index.structures.length) {
    box.innerHTML = `<div class="unavailable">Crystal structures in 3D become available when the research is finished.</div>`;
    return;
  }
  const opts = S.index.structures.map((s) => `<option value="${esc(s.id)}">${tx(s.formula)}</option>`).join("");
  box.innerHTML = `<figure class="chart"><h4>Crystal structure (relaxed)</h4>
    <div class="viz-controls"><label>Material <select id="st-pick">${opts}</select></label>
      <button class="ghost-btn" type="button" id="st-big">Open larger</button></div>
    <div class="viewer3d" id="st-view"></div><div id="st-legend"></div>
    <figcaption>Drag to rotate, scroll to zoom, right-drag to move. Colours follow the CPK convention; the substituted element is drawn larger; grey lines: unit cell.</figcaption></figure>`;
  const show = async () => {
    const id = $("st-pick").value, entry = S.index.structures.find((s) => s.id === id);
    $("st-view").innerHTML = `<div class="loading-inline"><span class="spinner small"></span> Loading the structure…</div>`;
    const st = await api(`/conversations/${S.id}/files/${entry.file}`);
    $("st-view").innerHTML = "";
    const v = newViewer($("st-view"));
    if (v) { v.clear(); drawCrystal(v, st); }
    $("st-legend").innerHTML = legendHTML(new Set(st.symbols), st.highlight ? `<span class="muted">substituted: ${esc(st.highlight)}</span>` : "");
  };
  $("st-pick").onchange = () => { disposeViewers(); show(); };
  $("st-big").onclick = () => openStructure($("st-pick").value);
  show().catch(() => { box.innerHTML = `<div class="unavailable">This structure is not available.</div>`; });
}

async function openStructure(id) {
  if (!S.index) return;
  const entry = S.index.structures.find((s) => s.id === id);
  if (!entry) return;
  $("viewer-title").textContent = chem(entry.formula);
  $("viewer-body").innerHTML = `<div class="viewer3d tall" id="big-view"><div class="loading-inline"><span class="spinner small"></span> Loading the structure…</div></div><div id="big-legend"></div><div id="big-info" class="stats"></div>`;
  openModal("viewer-modal");
  try {
    const st = await api(`/conversations/${S.id}/files/${entry.file}`);
    $("big-view").innerHTML = "";
    const v = newViewer($("big-view"));
    if (v) drawCrystal(v, st, true);
    $("big-legend").innerHTML = legendHTML(new Set(st.symbols), st.highlight ? `<span class="muted">substituted: ${esc(st.highlight)}</span>` : "");
    const [a, b, c] = st.cell.map((r) => Math.hypot(...r));
    $("big-info").innerHTML = `<span>Atoms in the cell <b>${st.symbols.length}</b></span><span>a, b, c <b>${a.toFixed(2)}, ${b.toFixed(2)}, ${c.toFixed(2)} Å</b></span>
      <span>E<sub>hull</sub> <b>${fmt(st.e_hull)} eV/atom</b></span>`;
  } catch { $("viewer-body").innerHTML = `<div class="unavailable">This structure is not available.</div>`; }
}

/* ---------- lithium diffusion: the recorded trajectories (never synthesized) ---------- */

function renderMDSection(box) {
  const cands = (S.index?.md || []).filter((e) => e.kind === "candidate");
  if (!cands.length) {
    box.innerHTML = `<div class="unavailable">${S.index ? "No molecular dynamics was run in this research." : "Diffusion animations become available when the research is finished."}</div>`;
    return;
  }
  const ids = [...new Set(cands.map((e) => e.id))];
  const ion = ionOf(domainOf()), ionWord = ionName(domainOf());
  box.innerHTML = `<figure class="chart"><h4>${ionWord[0].toUpperCase() + ionWord.slice(1)}-ion diffusion (molecular dynamics, 600 K)</h4>
    <div class="viz-controls"><label>Material <select id="md-pick">${ids.map((id) => `<option value="${esc(id)}">${tx(cands.find((e) => e.id === id).formula)}</option>`).join("")}</select></label>
      <label>Run <select id="md-seed"></select></label>
      <button class="ghost-btn" type="button" id="md-play">Pause</button>
      <input type="range" id="md-frame" min="0" max="399" value="0" aria-label="Time"></div>
    <div class="viewer-row"><div><div class="viewer3d" id="md-a"></div><p class="viewer-cap" id="md-a-cap"></p></div>
      <div><div class="viewer3d" id="md-b"></div><p class="viewer-cap" id="md-b-cap"></p></div></div>
    <p class="stats" id="md-time"></p>
    <div class="legend"><span><i style="background:#3b82f6"></i>${ion} within 1.5 Å of its start (vibrating)</span>
      <span><i style="background:#f59e0b"></i>${ion} 1.5–3 Å away</span><span><i style="background:#dc2626"></i>${ion} over 3 Å away (hopped)</span>
      <span class="muted">framework atoms in CPK colours, at their starting positions</span></div>
    <div id="md-curve"></div><p class="stats" id="md-stats"></p>
    <figcaption>The animation shows the ${ionWord} positions recorded during the simulation (one frame every 0.1 ps). The framework is drawn fixed: only its mean displacement was recorded (grey curves below).</figcaption></figure>`;
  const md = { a: null, b: null, frame: 0, playing: true };
  const seeds = () => {
    const id = $("md-pick").value;
    $("md-seed").innerHTML = cands.filter((e) => e.id === id).map((e) => `<option value="${e.seed}">${e.seed + 1}</option>`).join("");
  };
  const load = async () => {
    clearInterval(S.mdTimer);
    const id = $("md-pick").value, seed = +$("md-seed").value;
    const entry = S.index.md.find((e) => e.id === id && e.seed === seed);
    for (const k of ["md-a", "md-b"]) $(k).innerHTML = `<div class="loading-inline"><span class="spinner small"></span> Loading the simulation…</div>`;
    md.a = await api(`/conversations/${S.id}/files/${entry.file}`);
    const pe = S.index.md.find((e) => e.id === md.a.parent && e.seed === seed) || S.index.md.find((e) => e.id === md.a.parent);
    md.b = pe ? await api(`/conversations/${S.id}/files/${pe.file}`) : null;
    md.frame = 0;
    $("md-frame").max = md.a.frames.length - 1;
    for (const v of S.viewers) { try { v.clear(); } catch { /* */ } }
    S.viewers = [];
    $("md-a").innerHTML = ""; $("md-b").innerHTML = "";
    md.va = newViewer($("md-a")); md.vb = md.b ? newViewer($("md-b")) : null;
    if (!md.b) $("md-b").innerHTML = `<div class="unavailable">The parent crystal was not simulated in this research.</div>`;
    $("md-a-cap").textContent = chem(`${md.a.formula} (candidate)`);
    $("md-b-cap").textContent = md.b ? chem(`${md.b.formula} (parent crystal)`) : "";
    $("md-stats").innerHTML = `<span>D <b>${Number(md.a.D_cm2_per_s).toExponential(2)} ± ${Number(md.a.D_sem_cm2_per_s).toExponential(1)} cm²/s</b></span>
      ${md.a.ratio != null ? `<span>D / D(parent) <b>${md.a.ratio.toFixed(2)} ± ${md.a.ratio_err.toFixed(2)}</b></span>` : ""}
      <span>Verdict <b>${esc(md.a.verdict || "—")}</b></span>${md.a.conduction === "excluded" ? `<span class="chip bad">${esc(md.a.conduction_reason || "excluded")}</span>` : ""}`;
    $("md-curve").innerHTML = msdChart(md.a, md.b);
    draw(); play();
  };
  const frameOf = (data, f) => Math.min(f, data.frames.length - 1);
  const drawOne = (v, data, f) => {
    if (!v || !data) return;
    v.removeAllModels(); v.removeAllShapes();
    const syms = data.framework.symbols.slice(), pos = data.framework.positions.slice(), nF = syms.length;
    const ion = data.species || "Li";
    for (const p of data.frames[frameOf(data, f)]) { syms.push(ion); pos.push(p); }
    v.addModel(xyz(syms, pos), "xyz");
    v.setStyle({}, { sphere: { scale: 0.26, colorscheme: "Jmol" } });
    const disp = (data.displacement_A || [])[frameOf(data, f)] || [];
    v.setStyle({ elem: ion }, { sphere: { scale: 0.42, colorfunc: (atom) => { const d = disp[atom.index - nF] || 0; return d < 1.5 ? "#3b82f6" : d < 3 ? "#f59e0b" : "#dc2626"; } } });
    drawCell(v, data.cell);
    if (!v._zoomed) { v.zoomTo(); v._zoomed = true; }
    v.render();
  };
  const draw = () => {
    drawOne(md.va, md.a, md.frame); drawOne(md.vb, md.b, md.frame);
    const t = (md.frame * md.a.frame_fs) / 1000, hop = (d) => (d ? d.filter((x) => x > 3).length : 0);
    const da = (md.a.displacement_A || [])[md.frame], db = md.b && (md.b.displacement_A || [])[frameOf(md.b, md.frame)];
    $("md-time").innerHTML = `<span>t = <b>${t.toFixed(1)} ps</b></span><span>${tx(md.a.formula)}: <b>${hop(da)} / ${md.a.frames[0].length}</b> ${md.a.species || "Li"} hopped</span>` +
      (db ? `<span>${tx(md.b.formula)}: <b>${hop(db)} / ${md.b.frames[0].length}</b> ${md.b.species || "Li"} hopped</span>` : "");
    $("md-frame").value = md.frame;
    const cur = document.getElementById("msd-cursor");
    if (cur) { const x = cur.dataset.l * 1 + (t / cur.dataset.t) * cur.dataset.w; cur.setAttribute("x1", x); cur.setAttribute("x2", x); }
  };
  const play = () => {
    clearInterval(S.mdTimer);
    if (!md.playing) return;
    S.mdTimer = setInterval(() => { md.frame = (md.frame + 1) % md.a.frames.length; draw(); }, 90);
  };
  $("md-pick").onchange = () => { seeds(); load(); };
  $("md-seed").onchange = load;
  $("md-frame").oninput = () => { md.frame = +$("md-frame").value; draw(); };
  $("md-play").onclick = () => { md.playing = !md.playing; $("md-play").textContent = md.playing ? "Pause" : "Play"; play(); };
  seeds();
  load().catch(() => { box.innerHTML = `<div class="unavailable">This simulation is not available.</div>`; });
}

function msdChart(a, b) {
  const W = 640, H = 230, L = 52, B = 34, T = 14, R = 14;
  const t = a.curve.t_ps, tmax = t[t.length - 1] || 1;
  const series = [{ label: `Li in ${a.formula}`, y: a.curve.msd_li_A2, color: "var(--accent)", w: 2 }];
  if (b) series.push({ label: `Li in ${b.formula} (parent)`, y: b.curve.msd_li_A2, color: "var(--accent)", w: 1.6, dash: "5 4", t: b.curve.t_ps });
  for (const [el, y] of Object.entries(a.curve.msd_framework_A2 || {})) series.push({ label: `${el} (framework)`, y, color: "var(--muted)", w: 1 });
  const ymax = Math.max(0.5, ...series.flatMap((s) => s.y)) * 1.05;
  const X = (v) => L + (v / tmax) * (W - L - R), Y = (v) => H - B - (v / ymax) * (H - B - T);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Mean squared displacement against time">`;
  for (let k = 0; k <= 4; k++) { const v = (ymax * k) / 4; s += `<line class="grid" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v.toFixed(v < 10 ? 1 : 0)}</text>`; }
  for (let k = 0; k <= 4; k++) { const v = (tmax * k) / 4; s += `<text x="${X(v)}" y="${H - B + 15}" text-anchor="middle">${v.toFixed(0)}</text>`; }
  s += `<line class="axis" x1="${L}" y1="${T}" x2="${L}" y2="${H - B}"/><line class="axis" x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}"/>`;
  s += `<text x="${(L + W - R) / 2}" y="${H - 4}" text-anchor="middle">time (ps)</text><text x="12" y="${(T + H - B) / 2}" transform="rotate(-90 12 ${(T + H - B) / 2})" text-anchor="middle">mean squared displacement (Å²)</text>`;
  for (const g of series) {
    const tt = g.t || t;
    s += `<polyline fill="none" style="stroke:${g.color}" stroke-width="${g.w}" ${g.dash ? `stroke-dasharray="${g.dash}"` : ""} points="${g.y.map((v, i) => `${X(tt[i]).toFixed(1)},${Y(v).toFixed(1)}`).join(" ")}"/>`;
  }
  s += series.map((g, i) => `<text x="${L + 10 + (i % 3) * 190}" y="${T + 12 + Math.floor(i / 3) * 13}" style="fill:${g.color}">— ${tx(g.label)}</text>`).join("");
  s += `<line id="msd-cursor" data-l="${L}" data-w="${W - L - R}" data-t="${tmax}" x1="${L}" x2="${L}" y1="${T}" y2="${H - B}" style="stroke:var(--bad)" stroke-width="1"/>`;
  return `${s}</svg><p class="viewer-cap">The slope of the ${ionName(domainOf())} curve gives the diffusion coefficient D; a flat framework curve means the crystal stays intact.</p>`;
}

/* ---------- final report in the chat, PDF export ---------- */

function reportBlock(m) {
  return `<div class="report" data-report="${m.id}"><div class="report-bar"><span class="title">Final scientific report</span>
      ${m.data && m.data.champion && hasStructure(m.data.champion) ? `<button class="ghost-btn" type="button" data-champion="${esc(m.data.champion)}">Champion in 3D</button>` : ""}
      <button class="ghost-btn" type="button" data-pdf="${m.id}">Export PDF</button></div>
    <nav class="report-nav" aria-label="Report sections"></nav><div class="prose">${md(m.content)}</div></div>`;
}

function bindReport() {
  for (const rep of $("view").querySelectorAll(".report")) {
    const heads = [...rep.querySelectorAll(".prose h3")];
    heads.forEach((h, i) => { h.id = `r${rep.dataset.report}-${i}`; });
    rep.querySelector(".report-nav").innerHTML = heads.map((h) => `<a href="#${h.id}">${esc(h.textContent.replace(/:.*/, ""))}</a>`).join("");
    rep.querySelector(".report-nav").onclick = (e) => {
      const a = e.target.closest("a");
      if (a) { e.preventDefault(); document.getElementById(a.getAttribute("href").slice(1))?.scrollIntoView({ behavior: "smooth" }); }
    };
    const champ = rep.querySelector("[data-champion]");
    if (champ) champ.onclick = () => openStructure(champ.dataset.champion);
    rep.querySelector("[data-pdf]").onclick = () => exportPDF(rep);
  }
}

async function exportPDF(rep) {
  const c = S.view.conversation;
  let st = null, formula = "";
  const champ = rep.querySelector("[data-champion]");
  if (champ) {
    try {
      const entry = S.index.structures.find((s) => s.id === champ.dataset.champion);
      st = await api(`/conversations/${S.id}/files/${entry.file}`);
      formula = entry.formula;
    } catch { st = null; }
  }
  await printReport({ title: c.title, goal: c.goal, date: c.updated_at, html: rep.querySelector(".prose").innerHTML,
    structure: st, formula });
}

async function printReport({ title, goal, date, html, structure, formula }) {
  const root = $("print-root");
  let img = "";
  if (structure && window.$3Dmol) {  // a still image of the champion's structure for the paper version
    try {
      const holder = document.createElement("div");
      holder.style.cssText = "position:fixed;left:-2000px;top:0;width:600px;height:420px";
      document.body.appendChild(holder);
      const v = window.$3Dmol.createViewer(holder, { backgroundColor: "white" });
      drawCrystal(v, structure, true);
      img = `<img alt="Crystal structure of ${esc(chem(formula))}" src="${v.pngURI()}">`;
      holder.remove();
    } catch { img = ""; }
  }
  root.innerHTML = `<h1>${tx(title)}</h1><p class="meta">AutoLab research report · ${esc(new Date(date).toLocaleString())}<br>Goal: ${tx(goal)}</p>
    ${img}${html}`;
  document.body.classList.add("printing");
  const done = () => { document.body.classList.remove("printing"); root.innerHTML = ""; window.removeEventListener("afterprint", done); };
  window.addEventListener("afterprint", done);
  setTimeout(() => window.print(), 60);
}

/* ---------- results: the champion of every research, by domain ----------
   One card per champion (the first finalist of a research's final report, numbers as stored): what it is, its crystal
   structure in 3D, its properties with units, why it was chosen and what limits the confidence; its final report as a
   PDF and the research it came from, to talk with the agent again. */

const champs = { data: null, at: 0, observer: null };

/* ---------- settings: the rules of each domain, read from config.py (read only) ---------- */

const rulesCache = { data: null };

async function showSettings(domain, edit = false) {
  stopTimers();
  S.id = null; S.view = null; S.events = []; S.index = null;
  disposeViewers();
  const main = document.querySelector(".main");
  main.classList.remove("home");
  main.classList.add("results-page");
  main.appendChild($("composer-wrap"));
  $("crumb").textContent = edit ? "Edit the rules" : "Settings";
  document.title = `${edit ? "Edit the rules" : "Settings"} · AutoLab`;
  renderHistory();
  if (!rulesCache.data) {
    $("view").innerHTML = loadingHTML("Reading the rules of every domain…");
    try { rulesCache.data = await api("/settings"); }
    catch (e) {
      $("view").innerHTML = `<div class="thread"><div class="notice warn">The rules could not be loaded: ${esc(e.message)}.</div></div>`;
      return;
    }
  }
  if (!location.pathname.startsWith("/settings")) return;  // the reader went elsewhere meanwhile
  const { domains } = rulesCache.data;
  const current = domains.find((d) => d.key === domain) || domains[0];
  const unit = (r) => (r.unit ? ` <span class="muted">${tx(r.unit)}</span>` : "");
  const cell = (r) => {
    if (!edit) return `${tx(String(r.value))}${unit(r)}`;
    const num = typeof r.value === "number";
    return `<input class="rule-input" data-name="${esc(r.name)}" data-default="${esc(String(r.value))}" value="${esc(String(r.value))}"
      ${num ? 'type="number" step="any"' : 'type="text"'} aria-label="${esc(r.label)}">${unit(r)}`;
  };
  $("view").innerHTML = `<div class="results settings-page">
      <header class="results-head"><h1>${edit ? "Edit the rules" : "Settings"}</h1>
        <div class="settings-tools">${edit
          ? `<button class="ghost-btn" type="button" id="rules-restore">Restore defaults</button>
             <button class="ghost-btn" type="button" id="rules-back">Back</button>
             <span class="muted">Preview: changes are not applied to researches yet.</span>`
          : `<button class="ghost-btn" type="button" id="theme-open">Appearance</button>
             <button class="edit-rules-btn" type="button" id="rules-edit">Edit the rules</button>`}</div></header>
      <nav class="domain-tabs" role="tablist">${domains.map((d) => `<button type="button" role="tab" data-domain="${esc(d.key)}"
        aria-selected="${d.key === current.key}"><b>${esc(d.label)}</b><span>${d.groups.reduce((n, g) => n + g.rules.length, 0)} rules</span></button>`).join("")}</nav>
      ${current.groups.map((g) => `<section class="rules-group"><h2>${esc(g.title)}</h2>
        <div class="table-scroll"><table class="data rules${edit ? " editing" : ""}"><thead><tr><th>Rule</th><th>Value</th></tr></thead><tbody>
        ${g.rules.map((r) => `<tr><td>${tx(r.label)}</td><td class="num">${cell(r)}</td></tr>`).join("")}
        </tbody></table></div></section>`).join("")}
    </div>`;
  $("view").querySelector(".domain-tabs").onclick = (e) => {
    const b = e.target.closest("[data-domain]");
    if (b) navigate(`/settings/${b.dataset.domain}${edit ? "/edit" : ""}`);
  };
  if (edit) {
    $("rules-restore").onclick = () => { for (const i of $("view").querySelectorAll(".rule-input")) i.value = i.dataset.default; };
    $("rules-back").onclick = () => navigate(`/settings/${current.key}`);
  } else {
    $("rules-edit").onclick = () => navigate(`/settings/${current.key}/edit`);
    $("theme-open").onclick = () => { applyTheme(themeChoice()); openModal("settings"); };
  }
  $("view").scrollTo({ top: 0 });
}

/* ---------- benchmark & tests: the truth tests and benchmarks of each domain ---------- */

const benchCache = { data: null };

async function showBenchmarks(domain) {
  stopTimers();
  S.id = null; S.view = null; S.events = []; S.index = null;
  disposeViewers();
  const main = document.querySelector(".main");
  main.classList.remove("home");
  main.classList.add("results-page");
  main.appendChild($("composer-wrap"));
  $("crumb").textContent = "Benchmark & Tests";
  document.title = "Benchmark & Tests · AutoLab";
  renderHistory();
  if (!benchCache.data) {
    $("view").innerHTML = loadingHTML("Reading the tests of every domain…");
    try { benchCache.data = await api("/benchmarks"); }
    catch (e) {
      $("view").innerHTML = `<div class="thread"><div class="notice warn">The tests could not be loaded: ${esc(e.message)}.</div></div>`;
      return;
    }
  }
  if (!location.pathname.startsWith("/benchmarks")) return;  // the reader went elsewhere meanwhile
  const { domains } = benchCache.data;
  const current = domains.find((d) => d.key === domain) || domains[0];
  const verdict = (v) => `<span class="verdict ${esc(v)}">${esc(v)}</span>`;
  const sub = (t) => (t.table ? `<tr class="subrow"><td colspan="4"><table class="data mini"><thead><tr>${t.table.head.map((h) => `<th>${tx(h)}</th>`).join("")}</tr></thead>
      <tbody>${t.table.rows.map((r) => `<tr>${r.map((c, i) => `<td${i ? ' class="num"' : ""}>${tx(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></td></tr>` : "");
  $("view").innerHTML = `<div class="results bench-page">
      <header class="results-head"><h1>Benchmark &amp; Tests</h1></header>
      <nav class="domain-tabs" role="tablist">${domains.map((d) => `<button type="button" role="tab" data-domain="${esc(d.key)}"
        aria-selected="${d.key === current.key}"><b>${esc(d.label)}</b><span>${d.counts.passed} passed · ${d.counts.failed} failed · ${d.counts.measured} measured</span></button>`).join("")}</nav>
      <div class="table-scroll"><table class="data bench"><thead><tr><th>Test</th><th>Criterion</th><th>Result</th><th>Verdict</th></tr></thead><tbody>
        ${current.tests.map((t) => `<tr><td>${tx(t.test)}</td><td class="muted">${tx(t.criterion)}</td><td>${tx(t.result)}</td><td>${verdict(t.verdict)}</td></tr>${sub(t)}`).join("")}
      </tbody></table></div>
    </div>`;
  $("view").querySelector(".domain-tabs").onclick = (e) => {
    const b = e.target.closest("[data-domain]");
    if (b) navigate(`/benchmarks/${b.dataset.domain}`);
  };
  $("view").scrollTo({ top: 0 });
}

async function showResults(domain) {
  stopTimers();
  S.id = null; S.view = null; S.events = []; S.index = null;
  disposeViewers();
  const main = document.querySelector(".main");
  main.classList.remove("home");
  main.classList.add("results-page");
  main.appendChild($("composer-wrap"));
  $("crumb").textContent = "Results";
  document.title = "Results · AutoLab";
  renderHistory();
  if (!champs.data || Date.now() - champs.at > 60000) {
    $("view").innerHTML = loadingHTML("Gathering the champions of every research…");
    try { champs.data = await api("/champions"); champs.at = Date.now(); }
    catch (e) {
      $("view").innerHTML = `<div class="thread"><div class="notice warn">The results could not be loaded: ${esc(e.message)}.</div></div>`;
      return;
    }
  }
  if (!location.pathname.startsWith("/results")) return;  // the reader went elsewhere meanwhile
  const { domains, champions } = champs.data;
  const current = domains.find((d) => d.key === domain) || domains.find((d) => d.count) || domains[0];
  const mine = champions.filter((c) => c.domain === current.key);
  $("view").innerHTML = `<div class="results">
      <header class="results-head"><h1>Results</h1></header>
      <nav class="domain-tabs" role="tablist">${domains.map((d) => `<button type="button" role="tab" data-domain="${esc(d.key)}"
        aria-selected="${d.key === current.key}"><b>${esc(d.label)}</b><span>${d.count} champion${d.count === 1 ? "" : "s"}</span></button>`).join("")}</nav>
      <p class="domain-about">${tx(current.about || "")}</p>
      ${mine.length ? mine.map((c, i) => champCard(c, current, i)).join("") : `<div class="unavailable">No finished research in this domain yet.</div>`}
    </div>`;
  $("view").querySelector(".domain-tabs").onclick = (e) => {
    const b = e.target.closest("[data-domain]");
    if (b) navigate(`/results/${b.dataset.domain}`);
  };
  for (const card of $("view").querySelectorAll(".champ")) bindChamp(card, mine[+card.dataset.i]);
  $("view").scrollTo({ top: 0 });
}

const subText2 = (s, parent) => {
  if (!s) return "";
  const n = s.count === "all" ? "every" : s.count;
  return `${n} ${s.remove} replaced by ${s.add}${s.li_vacancies ? ` and ${s.li_vacancies} Li removed for charge balance` : ""} in the ${parent} cell`;
};

function champRows(c) {
  const r = c.champion, v = (x, d) => (x === undefined || x === null ? null : Number(x).toFixed(d));
  const pm = (x, e, d) => (v(x, d) === null ? null : `${v(x, d)}${e !== undefined && e !== null ? ` ± ${v(e, d)}` : ""}`);
  const rows = [["Energy above the convex hull", pm(r.e_hull_eV_per_atom, r.e_hull_error_eV_per_atom, 3), "eV/atom",
    "energy released by decomposing into known phases; ± the UMA-vs-DFT error on known compounds of its system"]];
  if (c.domain === "cathode") {
    rows.push(
      ["Average voltage", v(r.voltage_V, 2), "V vs Li/Li⁺", "average over the whole charge", v(r.parent_voltage_V, 2)],
      ["Theoretical capacity", v(r.capacity_mAh_g, 0), "mAh/g", "from the lithium that can leave", v(r.parent_capacity_mAh_g, 0)],
      ["Energy density", v(r.energy_density_Wh_kg, 0), "Wh/kg", "voltage × capacity, cathode material alone", v(r.parent_energy_density_Wh_kg, 0)],
      ["Volume change on charge", v(r.volume_change_pct, 1), "%", "shrinkage of the cell when lithium leaves", v(r.parent_volume_change_pct, 1)],
      ["Lithium removed on charge", r.li_removed != null ? `${r.li_removed} of ${r.li_total}` : null, "per cell", "what charge neutrality allows"],
      ["Against its parent", (r.vs_parent || {}).verdict || null, "", "decided by the code: differences within the model's voltage error are not claimed"]);
  } else if (c.domain === "sodium") {
    const w = r.window_V;
    rows.push(
      ["Electronic band gap (optB88 / mBJ)", v(r.gap_optb88_eV, 2) && `${v(r.gap_optb88_eV, 2)} / ${v(r.gap_mbj_eV, 2)}`, "eV", "an electrolyte must block electrons (≥ 1.8 eV in this domain)"],
      ["Electrochemical window", w ? (w.stable ? `${v(w.v_low, 2)}–${v(w.v_high, 2)}` : "zero width") : null, "V vs Na/Na⁺", "voltage range where it neither oxidises nor reduces"],
      ["Contact with sodium metal", r.against_na_metal || null, "", "a metallic product would let electrons through"],
      ["Na diffusion at 600 K vs parent", r.D_ratio_to_parent != null ? `${v(r.D_ratio_to_parent, 2)} ± ${v(r.D_ratio_error, 2)} (${r.diffusion_verdict})` : r.diffusion_verdict || null, "D / D(parent)", "molecular dynamics with UMA"]);
  } else {
    const w = r.window_V;
    rows.push(
      ["Electronic band gap (optB88 / mBJ)", v(r.gap_optb88_eV, 2) && `${v(r.gap_optb88_eV, 2)} / ${v(r.gap_mbj_eV, 2)}`, "eV", "an electrolyte must block electrons (≥ 2 eV)"],
      ["Electrochemical window", w ? (w.stable ? `${v(w.v_low, 2)}–${v(w.v_high, 2)}` : "zero width") : null, "V vs Li/Li⁺", "voltage range where it neither oxidises nor reduces"],
      ["Contact with lithium metal", r.against_li_metal || null, "", "a metallic product would let electrons through"],
      ["Reaction with a LiFePO₄ cathode", v(r.reaction_with_LiFePO4_eV_per_atom, 3), "eV/atom", "closer to 0 is better"],
      ["Li diffusion at 600 K vs parent", r.D_ratio_to_parent != null ? `${v(r.D_ratio_to_parent, 2)} ± ${v(r.D_ratio_error, 2)} (${r.diffusion_verdict})` : r.diffusion_verdict || null, "D / D(parent)", "molecular dynamics with UMA"],
      ["Ionic conductivity at 300 K", r.ionic_conductivity_300K_mS_cm != null ? `${Number(r.ionic_conductivity_300K_mS_cm).toPrecision(2)} (${Number(r.ionic_conductivity_range_mS_cm[0]).toPrecision(2)}–${Number(r.ionic_conductivity_range_mS_cm[1]).toPrecision(2)})` : null, "mS/cm", "extrapolated estimate with its range"],
      ["Conductivity against its parent", r.ionic_conductivity_vs_parent || null, "", "ranges compared: overlap = tied"],
      ["Activation energy", v(r.activation_energy_eV, 2), "eV", "Arrhenius fit of the diffusion"]);
  }
  rows.push(["Literature", r.novelty ? `${r.novelty === "related" ? "close family already studied" : r.novelty === "published" ? "already published" : "no publication found in this search"}` : null, "", "web search, a known material checked first as a control"]);
  return rows.filter((x) => x[1] !== null && x[1] !== undefined && x[1] !== "");
}

function champCard(c, dom, i) {
  const r = c.champion;
  const what = `${dom.kind.split(" · ")[0]} derived from ${r.parent || "a known crystal"} by substitution: ${subText2(r.substitution, r.parent || "parent")}.`;
  const date = c.research.created_at ? new Date(c.research.created_at).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" }) : "";
  return `<article class="champ" data-i="${i}">
    <header class="champ-head"><div><span class="kind-badge">${esc(dom.kind)}</span><h2 class="formula">${tx(r.formula)}</h2>
        <p class="champ-sub">${r.space_group ? `space group ${tx(r.space_group)} · ` : ""}${r.atoms_in_cell ? `${r.atoms_in_cell} atoms in the cell · ` : ""}champion of ${c.finalists} finalists</p></div>
      <div class="champ-actions"><button class="ghost-btn" type="button" data-pdf>Final report (PDF)</button>
        <button class="primary-btn" type="button" data-open>Open the research</button></div></header>
    <div class="champ-body">
      <figure class="champ-3d"><div class="viewer3d" data-viewer>${c.structure_file ? `<div class="loading-inline">Structure shown when visible…</div>` : `<div class="unavailable">3D structure not stored for this research</div>`}</div>
        <div class="champ-legend"></div>
        <figcaption>${r.a_A ? `Cell a, b, c = ${Number(r.a_A).toFixed(2)}, ${Number(r.b_A).toFixed(2)}, ${Number(r.c_A).toFixed(2)} Å${r.volume_A3 ? ` · V = ${Number(r.volume_A3).toFixed(0)} Å³` : ""}. ` : ""}Relaxed with UMA; the substituted element is drawn larger. Drag to rotate.</figcaption></figure>
      <div class="champ-info">
        <h4>What it is</h4><p>${tx(what)}</p>
        <h4>Properties</h4>
        <table class="props"><tbody>${champRows(c).map(([k, val, u, why, par]) => `<tr><th title="${esc(why)}">${tx(k)}</th><td><b>${tx(val)}</b> <span class="u">${tx(u)}</span>${par ? `<span class="par">parent ${tx(par)}</span>` : ""}</td></tr>`).join("")}</tbody></table>
        ${c.reasons.length ? `<h4>Why it is the champion</h4><ul>${c.reasons.map((x) => `<li>${tx(x)}</li>`).join("")}</ul>` : ""}
        ${c.uncertainties.length ? `<h4>What limits the confidence</h4><ul class="muted-list">${c.uncertainties.map((x) => `<li>${tx(x)}</li>`).join("")}</ul>` : ""}
        <p class="champ-origin">Found by the research <a href="/c/${esc(c.research.id)}" data-nav-c="${esc(c.research.id)}">“${tx(c.research.title)}”</a>${date ? ` · ${esc(date)}` : ""}${c.also_found_by.length
          ? `; also found by ${c.also_found_by.map((x) => `<a href="/c/${esc(x.id)}" data-nav-c="${esc(x.id)}">“${tx(x.title)}”</a>`).join(", ")}` : ""}.</p>
        <p class="champ-goal">Request: <i>${tx(c.research.goal)}</i></p>
      </div></div></article>`;
}

function bindChamp(card, c) {
  card.querySelector("[data-open]").onclick = () => navigate(`/c/${c.research.id}`);
  card.querySelector("[data-pdf]").onclick = (e) => champPDF(c, e.currentTarget);
  for (const a of card.querySelectorAll("[data-nav-c]")) a.onclick = (e) => { e.preventDefault(); navigate(`/c/${a.dataset.navC}`); };
  if (!c.structure_file) return;
  const box = card.querySelector("[data-viewer]");
  const load = async () => {
    try {
      const st = await api(`/conversations/${c.research.id}/files/${c.structure_file}`);
      if (!box.isConnected) return;
      box.innerHTML = "";
      const v = newViewer(box);
      if (v) { drawCrystal(v, st, true); spinSlow(v, box); }
      card.querySelector(".champ-legend").innerHTML = legendHTML(new Set(st.symbols), st.highlight ? `<span class="muted">substituted: ${esc(st.highlight)}</span>` : "");
      c._structure = st;
    } catch { box.innerHTML = `<div class="unavailable">This structure is not available.</div>`; }
  };
  if (!("IntersectionObserver" in window)) { load(); return; }  // the 3D is built when the card comes into view
  const io = new IntersectionObserver((entries) => { if (entries.some((x) => x.isIntersecting)) { io.disconnect(); load(); } });
  io.observe(box);
}

function spinSlow(v, box) {
  let last = 0;
  const step = (t) => {
    if (!box.isConnected) return;
    if (t - last > 50) { v.rotate(0.25, "y"); v.render(); last = t; }
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

async function champPDF(c, btn) {
  btn.disabled = true;
  const label = btn.textContent;
  btn.textContent = "Preparing the PDF…";
  try {
    const view = await api(`/conversations/${c.research.id}`);
    const rep = [...view.messages].reverse().find((m) => m.kind === "report");
    if (!rep) { toast("This research has no final report."); return; }
    let st = c._structure;
    if (!st && c.structure_file) { try { st = await api(`/conversations/${c.research.id}/files/${c.structure_file}`); } catch { st = null; } }
    await printReport({ title: view.conversation.title, goal: view.conversation.goal, date: view.conversation.updated_at,
      html: md(rep.content), structure: st, formula: c.champion.formula });
  } catch (e) { toast(e.message); }
  finally { btn.disabled = false; btn.textContent = label; }
}


/* ---------- live lab: the agent at work ----------
   The events of a research are played one by one as cards: what is being done, by which model or tool, with its
   numbers and its 3D structure; a card leaves when the next action starts, the progress list ticks as steps finish,
   and the decisions are written in the lab notebook. While a research runs, events arrive over a WebSocket (polling
   as a fallback). Results taken from the saved computations are played at a readable pace and marked "reused".
   Nothing shown here is invented: every number comes from an event; an animation between two recorded structures
   is labelled as such. */

const PROVIDER_MODEL = { meta: "Muse Spark", baseten: "Muse Spark Open", fireworks: "Muse Glimmer" };
const ICON_EXPAND = `<svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>`;
const ICON_REDUCE = `<svg viewBox="0 0 24 24"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></svg>`;
const ICON_PLAY = `<svg viewBox="0 0 24 24"><path d="M8 6l10 6-10 6z"/></svg>`;
const ICON_STOP = `<svg viewBox="0 0 24 24"><rect x="7" y="7" width="10" height="10" rx="1.5"/></svg>`;
const ICON_RESTART = `<svg viewBox="0 0 24 24"><path d="M4 12a8 8 0 1 0 2.6-5.9M4 4v4.5h4.5"/></svg>`;
const LAB_BG = "#0a1222";
const L = { on: false, mode: null, el: null, queue: [], seen: new Set(), played: 0, speed: 1, paused: false,
  group: null, card: null, timer: null, ws: null, steps: [], round: 0, rounds: 0, reused: false, t0: 0,
  formulas: {}, parents: {}, stageGroup: {}, clock: null, stepsAsked: 0 };

const ease = (u) => (u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2);
const lerp = (a, b, k) => a + (b - a) * k;
const lerpRows = (A, B, k) => A.map((r, i) => r.map((x, j) => lerp(x, (B[i] || r)[j], k)));
const modelOf = (p) => PROVIDER_MODEL[p] || "Muse Spark";
const fname = (id) => L.formulas[id] || id;
const domainOf = () => (S.view && S.view.conversation && S.view.conversation.domain) || "electrolyte";
const ionOf = (domain) => (domain === "sodium" ? "Na" : "Li");  // the conducting ion of a domain
const ionName = (domain) => (domain === "sodium" ? "sodium" : "lithium");
const subText = (s) => (s ? `${s.remove} → ${s.add} ×${s.count}${s.li_vacancies ? `, −${s.li_vacancies} Li` : ""}` : "");
function hexMix(a, b, k) {
  const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [p(a), p(b)];
  return "#" + x.map((v, i) => Math.round(lerp(v, y[i], k)).toString(16).padStart(2, "0")).join("");
}

/* playback */

async function labStart(mode) {
  labStop();
  if (L.speedSet !== true) L.speed = mode === "watch" ? 2 : 1;  // a finished research is shown faster by default
  Object.assign(L, { on: true, mode, queue: [], seen: new Set(), played: 0, paused: false, group: null, card: null,
    round: 0, rounds: 0, formulas: {}, parents: {}, stageGroup: {}, t0: Date.now(), stepsAsked: 0,
    full: mode === "watch", hidden: false, convId: S.id });  // live: in the chat, a button opens it full screen
  L.reused = !!(S.view && S.view.conversation.scope && S.view.conversation.scope.reused_from);
  L.domain = domainOf();
  L.steps = (S.view.steps || []).map((s) => ({ ...s, state: "pending", detail: null }));
  if (!S.index && S.view.files && S.view.files.includes("index.json")) {
    try { S.index = await api(`/conversations/${S.id}/files/index.json`); } catch { S.index = null; }
  }
  L.el = labShell();
  labEnqueue(S.events);
  renderThread();
  labSteps();
  connectLive();
  L.clock = setInterval(labClock, 1000);
  L.timer = setTimeout(labTick, 700);
  if (!L.full) scrollBottom();  // in the chat: the lab is the last block
}

function labStop() {
  clearTimeout(L.timer); clearInterval(L.clock);
  if (L.card) labDispose(L.card);
  L.card = null; L.on = false; L.hidden = false;
  if (L.ws) { try { L.ws.close(); } catch { /* closed */ } L.ws = null; }
  if (L.el) L.el.remove();
  document.body.classList.remove("lab-open");
}

/* full screen (landscape: progress | current action | lab notebook) or inside the chat; the same element moves, so
   nothing shown is lost */
function labPlace() {
  const show = L.on && !L.hidden && L.convId === S.id && L.el;
  document.body.classList.toggle("lab-open", !!(show && L.full));
  if (!L.el) return;
  if (!show) { L.el.remove(); return; }
  L.el.classList.toggle("full", L.full);
  const fb = L.el.querySelector("[data-full]");
  if (fb) {
    fb.innerHTML = L.full ? ICON_REDUCE : ICON_EXPAND;
    fb.title = L.full ? "Reduce (Esc)" : "Full screen";
    fb.setAttribute("aria-label", fb.title);
  }
  const host = L.full ? document.body : $("lab-slot");
  if (host && L.el.parentElement !== host) host.appendChild(L.el);
  requestAnimationFrame(() => {
    const v = L.card && L.card.viewer;
    if (v) { try { v.resize(); v.render(); } catch { /* gone */ } }
  });
}

function labSetFull(full) {
  L.full = full;
  renderThread();  // a reduced replay takes the place of the research card
  if (!full) requestAnimationFrame(() => { if (L.el && L.el.isConnected) L.el.scrollIntoView({ block: "start" }); });
}

function labPauseUI() {
  const b = L.el && L.el.querySelector("[data-pause]");
  if (!b) return;
  b.classList.toggle("on", L.paused);
  b.innerHTML = L.paused ? ICON_PLAY : PAUSE;
  b.title = L.paused ? "Resume" : "Pause";
}

/* leave the lab of a replay: kept where it stopped if it was paused (Watch resumes it), else ended */
function labQuit() {
  if (L.mode === "watch" && L.paused) {
    L.hidden = true;
    renderThread();
  } else labFinish();
}

function labResume() {
  if (!L.on) return labStart("watch");
  const wasHidden = L.hidden;
  L.hidden = false; L.full = true; L.paused = false;
  labPauseUI();
  renderThread();
  if (wasHidden && L.card && L.card.viewer) spin(L.card, L.card.viewer);  // animations stop while the lab is hidden
}

function labEnqueue(events) {
  for (const e of events) {
    if (L.seen.has(e.seq)) continue;
    L.seen.add(e.seq);
    L.queue.push(e);
    if (e.candidate_id && e.data && e.data.formula) L.formulas[e.candidate_id] = e.data.formula;
  }
}

function labTick() {
  if (!L.on) return;
  if (L.paused) { L.timer = setTimeout(labTick, 300); return; }
  const e = L.queue.shift();
  if (!e) {
    if (S.view && ACTIVE.has(S.view.conversation.status)) { labWorking(); L.timer = setTimeout(labTick, 700); }
    else labFinish();
    return;
  }
  let ms = 300;
  try { ms = labPlay(e); } catch (err) { console.error("lab card", e.type, e.step, err); }
  L.played++;
  labAskSteps();
  const backlog = L.mode === "live" ? Math.max(1, Math.min(6, L.queue.length / 6)) : 1;
  L.timer = setTimeout(labTick, ms / L.speed / backlog);
}

async function labFinish() {
  labStop();
  if (S.view && !ACTIVE.has(S.view.conversation.status)) {
    try {
      S.view = await api(`/conversations/${S.id}`);
      if (S.view.files.includes("index.json") && !S.index) S.index = await api(`/conversations/${S.id}/files/index.json`);
    } catch { /* the stored view is kept */ }
  }
  renderThread();
  setComposer(composerMode());
  const fin = $("view").querySelector("#research");
  if (fin) fin.closest(".msg").scrollIntoView({ behavior: "smooth", block: "start" });
}

function labAskSteps() {
  if (!L.ws || L.ws.readyState !== 1) return;
  const now = Date.now();
  if (now - L.stepsAsked < 350 && L.queue.length) return;
  L.stepsAsked = now;
  L.ws.send(JSON.stringify({ steps: L.played }));
}

/* the WebSocket: events pushed by the web server as soon as the service has them */

function connectLive() {
  if (L.ws) { try { L.ws.close(); } catch { /* closed */ } }
  let ws;
  try { ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/conversations/${S.id}`); }
  catch { if (ACTIVE.has(S.view.conversation.status)) startPolling(); return; }
  const id = S.id;
  L.ws = ws;
  ws.onopen = () => { L.stepsAsked = 0; labAskSteps(); };
  ws.onmessage = async (m) => {
    if (S.id !== id) return;
    let msg;
    try { msg = JSON.parse(m.data); } catch { return; }
    if (msg.type === "events") {
      const have = new Set(S.events.map((e) => e.seq));
      const fresh = msg.events.filter((e) => !have.has(e.seq));
      S.events.push(...fresh);
      S.next = msg.next;
      if (msg.steps) S.view.steps = msg.steps;
      if (L.on) labEnqueue(fresh);
      if (msg.status !== S.view.conversation.status) {
        S.view.conversation.status = msg.status;
        setComposer(composerMode());
        loadHistory();
      }
    } else if (msg.type === "steps" && msg.steps && L.on) {
      L.steps = msg.steps;
      labSteps();
    }
  };
  ws.onclose = () => {
    if (L.ws === ws) L.ws = null;
    if (S.id === id && S.view && ACTIVE.has(S.view.conversation.status)) startPolling();  // fallback
  };
}

/* the frame: header, progress list, the stage with the current card, the lab notebook */

function labShell() {
  const el = document.createElement("section");
  el.className = "lab";
  el.innerHTML = `<header class="lab-head">
      <div class="orb" aria-hidden="true">${AI_ICON}<i></i><i></i></div>
      <div class="lab-title"><b>AutoLab agent at work</b><span class="lab-sub" id="lab-sub">starting…</span></div>
      ${L.reused ? `<span class="reuse big" title="This exact request was already researched: its saved computations are shown again, nothing is recomputed">reused results · accelerated</span>` : ""}
      <div class="lab-ctl" role="group" aria-label="Playback">
        ${[1, 2, 4].map((k) => `<button type="button" data-speed="${k}"${L.speed === k ? ' class="on"' : ""}>${k}×</button>`).join("")}
        <button type="button" data-pause title="Pause" aria-label="Pause">${PAUSE}</button>
        ${L.mode === "watch" ? `<button type="button" data-stop title="Stop: end the playback and show the results">${ICON_STOP}<span>Stop</span></button>
        <button type="button" data-restart title="Play again from the start">${ICON_RESTART}</button>`
          : `<button type="button" data-skip title="Skip to the latest step">Latest</button>`}
        <button type="button" data-full title="Full screen" aria-label="Full screen">${ICON_EXPAND}</button>
        ${L.mode === "watch" ? `<button type="button" data-quit title="Leave the lab (a paused playback is kept: Resume watching continues it)" aria-label="Leave">${CROSS}</button>` : ""}</div></header>
    <div class="lab-body">
      <aside class="lab-steps"><h5>Progress</h5><ol></ol><div class="lab-bar"><i></i></div></aside>
      <div class="lab-stage">
        <div class="lab-actor"></div>
        <div class="lab-slot"></div>
      </div>
      <aside class="lab-log"><h5>Lab notebook</h5><ul></ul></aside></div>`;
  el.querySelector(".lab-ctl").onclick = (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.speed) {
      L.speed = +b.dataset.speed;
      L.speedSet = true;
      for (const x of el.querySelectorAll("[data-speed]")) x.classList.toggle("on", x === b);
    } else if (b.hasAttribute("data-pause")) {
      L.paused = !L.paused;
      labPauseUI();
    } else if (b.hasAttribute("data-skip")) {  // live: catch up with the research
      L.queue = [];
      if (!ACTIVE.has(S.view.conversation.status)) labFinish();
    } else if (b.hasAttribute("data-stop")) labFinish();
    else if (b.hasAttribute("data-restart")) labStart("watch");
    else if (b.hasAttribute("data-full")) labSetFull(!L.full);
    else if (b.hasAttribute("data-quit")) labQuit();
  };
  return el;
}

function labClock() {
  const sub = L.el && L.el.querySelector("#lab-sub");
  if (!sub) return;
  const s = Math.round((Date.now() - L.t0) / 1000);
  const round = L.round ? `Round ${L.round}${L.rounds ? ` of ${L.rounds}` : ""} · ` : "";
  const left = L.queue.length && L.mode !== "live" ? ` · ${L.queue.length} actions to show` : "";
  sub.textContent = `${round}${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}${left}`;
}

function labSteps() {
  if (!L.el) return;
  const ol = L.el.querySelector(".lab-steps ol");
  const before = new Map([...ol.querySelectorAll("li")].map((li) => [li.dataset.key, li.dataset.state]));
  ol.innerHTML = L.steps.map((s) => `<li class="${s.state}${before.get(s.key) && before.get(s.key) !== "done" && s.state === "done" ? " just" : ""}"
      data-key="${esc(s.key)}" data-state="${esc(s.state)}"><span class="ic">${s.state === "done" ? CHECK : s.state === "failed" ? CROSS : ""}</span>
      <span>${tx(s.label)}</span></li>`).join("");
  const done = L.steps.filter((s) => s.state === "done" || s.state === "skipped").length;
  L.el.querySelector(".lab-bar i").style.width = `${L.steps.length ? (100 * done) / L.steps.length : 0}%`;
}

/* a tool works on what Muse Spark proposed or chose: the proposal first, then the tool that runs it (the code launches
   the tools; Muse Spark does not call them itself) */
const TOOLS = new Set(["UMA", "pymatgen", "Materials Project", "GapModel", "UMA + Materials Project"]);
function labActor(who, what, kind = "compute", origin = null) {
  const a = L.el.querySelector(".lab-actor");
  a.dataset.kind = kind;
  const by = origin || (TOOLS.has(who) ? "Muse Spark's candidate" : null);
  a.innerHTML = (by ? `<span class="model think">${tx(by)}</span><span class="arrow">→</span><span class="model ${kind} tool">${tx(who)}</span>`
    : `<span class="model ${kind}">${tx(who)}</span>`) + `<span class="what">${tx(what)}</span><span class="dots"><i></i><i></i><i></i></span>`;
  L.el.querySelector(".orb").dataset.kind = kind;
}

function labLog(text, tone = "") {
  const ul = L.el.querySelector(".lab-log ul");
  const li = document.createElement("li");
  li.className = tone;
  li.innerHTML = `<span class="r">${L.round ? `R${L.round}` : "—"}</span>${tx(text)}`;
  ul.prepend(li);
  while (ul.children.length > 14) ul.lastChild.remove();  // 6 shown in the chat, all in full screen
  say(text);
}

/* cards */

function labCard(group) {
  if (L.card && L.card.group === group) return L.card;
  const old = L.card;
  if (old) {
    old.el.classList.add("leaving");
    setTimeout(() => { labDispose(old); old.el.remove(); }, 420);
  }
  const el = document.createElement("article");
  el.className = "lab-card entering";
  L.el.querySelector(".lab-slot").appendChild(el);
  setTimeout(() => el.classList.remove("entering"), 30);
  L.card = { el, group, cleanup: [], raf: 0, viewer: null, isNew: true };
  L.group = group;
  return L.card;
}

function labDispose(card) {
  cancelAnimationFrame(card.raf);
  for (const f of card.cleanup) { try { f(); } catch { /* gone */ } }
  card.cleanup = [];
}

function later(card, ms, fn) {
  const t = setTimeout(() => { if (card.el.isConnected) fn(); }, ms / L.speed);
  card.cleanup.push(() => clearTimeout(t));
}

function cardHead(card, title, sub = "", e = null) {
  card.el.innerHTML = `<div class="lc-head"><div><h4>${tx(title)}</h4>${sub ? `<p>${tx(sub)}</p>` : ""}</div>
    ${(L.reused || (e && e.data && e.data.cached)) ? `<span class="reuse" title="Taken from the saved results: nothing was recomputed">reused</span>` : ""}</div>
    <div class="lc-body"></div>`;
  return card.el.querySelector(".lc-body");
}

function cardAdd(card, html, cls = "") {
  const body = card.el.querySelector(".lc-body") || card.el;
  const div = document.createElement("div");
  div.className = `lc-item ${cls}`;
  div.innerHTML = html;
  body.appendChild(div);
  animateIn(div);
  return div;
}

function animateIn(root) {
  requestAnimationFrame(() => {
    for (const f of root.querySelectorAll("[data-w]")) f.style.width = `${f.dataset.w}%`;
    for (const n of root.querySelectorAll("[data-count]")) countUp(n, +n.dataset.count, +(n.dataset.digits || 2));
  });
}

function countUp(el, to, digits, ms = 1100) {
  const t0 = performance.now(), from = 0;
  setTimeout(() => { if (el.isConnected) el.textContent = to.toFixed(digits); }, ms / L.speed + 60);
  const step = () => {
    if (!el.isConnected) return;
    const u = Math.min(1, (performance.now() - t0) / (ms / L.speed));
    el.textContent = lerp(from, to, ease(u)).toFixed(digits);
    if (u < 1) requestAnimationFrame(step);
  };
  step();
}

function typeInto(el, text, ms) {
  const t0 = performance.now(), n = text.length;
  setTimeout(() => { if (el.isConnected) { el.textContent = chem(text); el.classList.remove("typing"); } }, ms / L.speed + 80);
  const step = () => {
    if (!el.isConnected) return;
    const k = Math.min(n, Math.ceil((n * (performance.now() - t0)) / (ms / L.speed)));
    el.textContent = chem(text.slice(0, k));
    el.classList.toggle("typing", k < n);
    if (k < n) requestAnimationFrame(step);
  };
  step();
}

function gauge({ value, min = 0, max, threshold, better, unit, digits = 3, label }) {
  const pct = (x) => Math.max(0, Math.min(100, ((x - min) / (max - min)) * 100));
  const ok = threshold === undefined ? true : better === "low" ? value <= threshold : value >= threshold;
  return `<div class="gauge ${ok ? "ok" : "bad"}"><div class="g-lbl">${tx(label)}</div>
    <div class="g-track"><div class="g-fill" data-w="${pct(value)}"></div>
      <div class="g-thr" style="left:${pct(threshold)}%"><span>limit ${threshold} ${tx(unit)}</span></div></div>
    <div class="g-val"><b data-count="${value}" data-digits="${digits}">0</b> ${tx(unit)} <span class="verdict">${ok ? "within the limit" : "outside the limit"}</span></div></div>`;
}

function strip(card, active) {
  const names = L.domain === "cathode"
    ? [["build", "Build"], ["known", "Novelty"], ["relax", "Relax"], ["hull", "Stability"], ["charge", "Charge"], ["verdict", "Verdict"]]
    : [["build", "Build"], ["known", "Novelty"], ["relax", "Relax"], ["hull", "Stability"], ["gap", "Band gap"], ["verdict", "Verdict"]];
  let s = card.el.querySelector(".lc-strip");
  if (!s) {
    s = document.createElement("div");
    s.className = "lc-strip";
    card.el.querySelector(".lc-head").after(s);
  }
  const at = names.findIndex(([k]) => k === active);
  s.innerHTML = names.map(([k, l], i) => `<span class="${i < at ? "done" : i === at ? "now" : ""}">${l}</span>`).join("");
}

/* 3D in the cards (3Dmol, dark background) */

function labViewer(card, box) {
  if (!window.$3Dmol || !box) { if (box) box.innerHTML = `<div class="unavailable">3D viewer unavailable</div>`; return null; }
  const v = window.$3Dmol.createViewer(box, { backgroundColor: LAB_BG });
  card.viewer = v;
  card.cleanup.push(() => { try { v.clear(); } catch { /* gone */ } });
  return v;
}

function drawLab(v, st, pos, cell, subT = 1) {
  v.removeAllModels(); v.removeAllShapes();
  v.addModel(xyz(st.symbols, pos), "xyz");
  v.setStyle({}, { sphere: { scale: 0.3, colorscheme: "Jmol" }, stick: { radius: 0.08, colorscheme: "Jmol" } });
  if (st.added) {
    const from = CPK[st.removed] || "#9aa4b2", to = CPK[st.added] || "#9aa4b2";
    const scale = 0.34 + 0.22 * Math.sin(Math.PI * Math.min(1, subT));
    v.setStyle({ elem: st.added }, { sphere: { scale, color: subT >= 1 ? to : hexMix(from, to, subT) },
      stick: { radius: 0.08, colorscheme: "Jmol" } });
  }
  drawCell(v, cell);
  if (!v._zoomed) { v.zoomTo(); v.zoom(1.15); v._zoomed = true; }
  v.render();
}

function spin(card, v) {
  let last = 0;
  const step = (t) => {
    if (!card.el.isConnected) return;
    if (t - last > 40) { v.rotate(0.45, "y"); v.render(); last = t; }
    card.raf = requestAnimationFrame(step);
  };
  card.raf = requestAnimationFrame(step);
}

function latticeHTML(lat) {
  return `<div class="lat">${["a", "b", "c"].map((k) => `<span>${k} <b data-lat="${k}">${lat[k].toFixed(3)}</b> Å</span>`).join("")}
    <span>V <b data-lat="volume">${lat.volume.toFixed(1)}</b> Å³</span></div>`;
}

function setLattice(card, A, B, k) {
  for (const n of card.el.querySelectorAll("[data-lat]")) {
    const key = n.dataset.lat;
    n.textContent = lerp(A[key], B[key], k).toFixed(key === "volume" ? 1 : 3);
  }
}

function substitutionScene(card, st) {
  const box = card.el.querySelector(".lab-3d");
  const v = card.viewer || labViewer(card, box);
  if (!v) return;
  const t0 = performance.now(), dur = 1500 / L.speed;
  const step = () => {
    if (!card.el.isConnected) return;
    const u = Math.max(0, Math.min(1, (performance.now() - t0) / dur));
    drawLab(v, st, st.start.positions, st.start.cell, u);
    v.rotate(0.4, "y");
    if (u < 1) card.raf = requestAnimationFrame(step); else spin(card, v);
  };
  card.raf = requestAnimationFrame(step);
}

function relaxScene(card, st, ms) {
  const box = card.el.querySelector(".lab-3d");
  const v = card.viewer || labViewer(card, box);
  if (!v) return;
  cancelAnimationFrame(card.raf);
  const frames = st.trajectory && st.trajectory.length >= 2 ? st.trajectory : null;
  const A = st.start, B = st.end, t0 = performance.now(), dur = ms / L.speed;
  let last = 0;
  const step = () => {
    if (!card.el.isConnected) return;
    const t = performance.now(), u = Math.max(0, Math.min(1, (t - t0) / dur)), k = ease(u);
    if (t - last > 33 || u >= 1) {
      let pos, cell;
      if (frames) {
        const f = k * (frames.length - 1), i = Math.floor(f), w = f - i, F = frames[i], G = frames[Math.min(i + 1, frames.length - 1)];
        pos = lerpRows(F.positions, G.positions, w); cell = lerpRows(F.cell, G.cell, w);
      } else { pos = lerpRows(A.positions, B.positions, k); cell = lerpRows(A.cell, B.cell, k); }
      drawLab(v, st, pos, cell, 1);
      v.rotate(0.35, "y");
      setLattice(card, A.lattice, B.lattice, k);
      last = t;
    }
    if (u < 1) card.raf = requestAnimationFrame(step); else spin(card, v);
  };
  card.raf = requestAnimationFrame(step);
}

async function mdScene(card, box, entry) {
  const v = labViewer(card, box);
  if (!v) return;
  let data;
  try { data = await api(`/conversations/${S.id}/files/${entry.file}`); } catch { box.innerHTML = `<div class="unavailable">trajectory unavailable</div>`; return; }
  if (!card.el.isConnected) return;
  let f = 0;
  const nF = data.framework.symbols.length;
  const frame = () => {
    if (!card.el.isConnected) return;
    v.removeAllModels(); v.removeAllShapes();
    const syms = data.framework.symbols.slice(), pos = data.framework.positions.slice();
    const ion = data.species || "Li";
    for (const p of data.frames[f]) { syms.push(ion); pos.push(p); }
    v.addModel(xyz(syms, pos), "xyz");
    v.setStyle({}, { sphere: { scale: 0.24, colorscheme: "Jmol" } });
    const disp = (data.displacement_A || [])[f] || [];
    v.setStyle({ elem: ion }, { sphere: { scale: 0.4, colorfunc: (a) => { const d = disp[a.index - nF] || 0; return d < 1.5 ? "#3b82f6" : d < 3 ? "#f59e0b" : "#ef4444"; } } });
    drawCell(v, data.cell);
    if (!v._zoomed) { v.zoomTo(); v._zoomed = true; }
    v.render();
    const t = (f * data.frame_fs) / 1000, hop = disp.filter((x) => x > 3).length;
    const cap = card.el.querySelector(".md-cap");
    if (cap) cap.innerHTML = `${tx(data.formula)} · t = <b>${t.toFixed(1)} ps</b> · <b>${hop}</b> of ${data.frames[0].length} ${ion} hopped more than 3 Å`;
    f = (f + 1) % data.frames.length;
  };
  const timer = setInterval(frame, 80);
  card.cleanup.push(() => clearInterval(timer));
  frame();
}

function chargeScene(card, st, ms) {
  const box = card.el.querySelector(".lab-3d");
  const v = card.viewer || labViewer(card, box);
  if (!v) return;
  cancelAnimationFrame(card.raf);
  const gone = new Set(st.removed), keep = st.symbols.map((_, i) => i).filter((i) => !gone.has(i));
  const A = st.lithiated, B = st.delithiated, t0 = performance.now(), dur = ms / L.speed;
  const symK = keep.map((i) => st.symbols[i]), posAK = keep.map((i) => A.positions[i]);
  let last = 0;
  const step = () => {
    if (!card.el.isConnected) return;
    const t = performance.now(), u = Math.max(0, Math.min(1, (t - t0) / dur));
    if (t - last > 33 || u >= 1) {
      v.removeAllModels(); v.removeAllShapes();
      if (u < 0.45) {  // the Li that leave drift out of the cell and fade
        const f = u / 0.45, out = A.cell[2].map((x) => (x / Math.hypot(...A.cell[2])) * 5 * f);
        const pos = A.positions.map((p, i) => (gone.has(i) ? p.map((x, j) => x + out[j]) : p));
        v.addModel(xyz(st.symbols, pos), "xyz");
        v.setStyle({}, { sphere: { scale: 0.3, colorscheme: "Jmol" }, stick: { radius: 0.08, colorscheme: "Jmol" } });
        v.setStyle({ elem: "Li" }, { sphere: { scale: 0.32, colorfunc: (a) => (gone.has(a.index) ? hexMix(CPK.Li, LAB_BG, f) : CPK.Li) } });
        drawCell(v, A.cell);
      } else {  // the charged cell relaxes
        const k = ease((u - 0.45) / 0.55);
        v.addModel(xyz(symK, lerpRows(posAK, B.positions, k)), "xyz");
        v.setStyle({}, { sphere: { scale: 0.3, colorscheme: "Jmol" }, stick: { radius: 0.08, colorscheme: "Jmol" } });
        drawCell(v, lerpRows(A.cell, B.cell, k));
        setLattice(card, A.lattice, B.lattice, k);
      }
      if (!v._zoomed) { v.zoomTo(); v.zoom(1.15); v._zoomed = true; }
      v.rotate(0.35, "y");
      v.render();
      last = t;
    }
    if (u < 1) card.raf = requestAnimationFrame(step); else spin(card, v);
  };
  card.raf = requestAnimationFrame(step);
}

function voltBar(w, ion = "Li") {
  const X = (v) => Math.max(0, Math.min(100, (v / 5) * 100));
  const seg = w && w.stable ? `<i class="win" style="left:${X(w.v_low)}%;width:${Math.max(0.6, X(w.v_high) - X(w.v_low))}%"></i>` : `<i class="win none"></i>`;
  const cathode = ion === "Li" ? `<em class="fe" style="left:${X(3.45)}%">LiFePO₄</em>` : "";  // no cathode interface for Na
  return `<div class="volt">${seg}<em class="li" style="left:0%">${ion}</em>${cathode}</div>`;
}

function aheadOf(pred) { return L.queue.find(pred) || S.events.find(pred); }

/* what each event shows */

// the stage titles of the sodium domain (the stages are the electrolyte ones, with Na+ as the mobile ion)
const SODIUM_TITLES = { electrodes: "Electrodes: stability window and contact with sodium metal",
  molecular_dynamics: "Sodium-ion diffusion: molecular dynamics at 600 K" };
const stageTitle = (name, title) => (L.domain === "sodium" && SODIUM_TITLES[name]) || title;

const STAGES = {
  electrodes: { title: "Electrodes: stability window, lithium metal, cathode", actor: ["pymatgen", "computes the phase diagrams against the electrodes", "compute", "Muse Spark's candidates"],
    done: (d) => `${d.computed ?? 0} computed${(d.excluded || []).length ? ` · excluded: ${d.excluded.map(fname).join(", ")}` : ""}` },
  candidate_analyses: { title: "Independent reviews", actor: ["Muse Spark Open", "reviewing each candidate separately", "think"],
    done: (d) => (d.skipped ? `not needed: ${d.skipped}` : `${d.analysed ?? 0} reviewed${d.reused ? `, ${d.reused} reused` : ""}`) },
  md_selection: { title: "Choosing what to simulate", actor: ["Muse Spark", "deciding which candidate deserves molecular dynamics", "think"],
    done: (d) => d.reason || `selected: ${(d.selected || []).map(fname).join(", ") || "none"}${d.chosen_by ? ` (chosen by ${PROVIDER_MODEL[d.chosen_by] || d.chosen_by})` : ""}` },
  molecular_dynamics: { title: "Lithium-ion diffusion: molecular dynamics at 600 K", actor: ["UMA", "runs molecular dynamics at 600 K", "compute", "Muse Spark's choice"],
    done: (d) => `${Object.keys(d.verdicts || {}).length} simulated${(d.excluded || []).length ? ` · excluded for conduction: ${d.excluded.map(fname).join(", ")}` : ""}` },
  conductivity: { title: "Ionic conductivity at 300 K", actor: ["AutoLab", "Arrhenius fit 500–700 K and Nernst–Einstein relation", "compute"],
    done: (d) => `${d.computed ?? 0} structures · parents: ${Object.entries(d.parents || {}).map(([k, v]) => `${L.parents[k] || k} ${v} mS/cm`).join(", ")}` },
  ranking: { title: "Ranking by explicit rules", actor: ["AutoLab", "level against the parent at 300 K, then a stated convention", "plan"], done: null },
  novelty: { title: "Literature check", actor: ["Muse Spark", "searching the web; a known material is checked first as a control", "think"], done: null },
  report: { title: "Final scientific report", actor: ["Muse Spark", "writing the report from the numbers computed by the code", "think"],
    done: (d) => `champion: ${fname(d.champion)} · ${d.completeness}` },
};

function stageGroup(name, d) { return `stage:${name}:${d && d.iteration != null ? d.iteration : "final"}`; }

function stageCard(name, d, e) {
  const g = stageGroup(name, d);
  const meta = STAGES[name] || { title: name.replace(/_/g, " "), actor: ["AutoLab", name.replace(/_/g, " "), "compute"] };
  const card = labCard(g);
  L.stageGroup[name] = g;
  if (card.isNew) {
    card.isNew = false;
    cardHead(card, stageTitle(name, meta.title), d && d.iteration != null ? `round ${d.iteration}: this round's candidates` : "the whole pool of candidates", e);
  }
  labActor(...meta.actor);
  return card;
}

function playStage(e) {
  const d = e.data || {}, [name, part] = e.step.split(":");
  const card = stageCard(name, d, e);
  if (part === "calibration") {
    cardAdd(card, `<span class="tag">calibration</span> ${tx(d.electrolyte)} | ${tx(d.cathode)}: UMA <b>${fmt(d.uma)}</b> vs DFT <b>${fmt(d.mp)}</b> eV/atom
      ${d.ok ? `<span class="ok">trusted (within ${d.tolerance})</span>` : `<span class="no">not trusted</span>`}`);
    return 1600;
  }
  if (part === "plan") {
    const ids = [];
    for (const x of [...L.queue, ...S.events]) {
      if (x.step === "molecular_dynamics:done" && x.type === "candidate" && ((x.data.iteration ?? "final") === (d.iteration ?? "final")) && !ids.includes(x.candidate_id)) ids.push(x.candidate_id);
    }
    const entry = (S.index && S.index.md || []).find((m) => m.kind === "candidate" && ids.includes(m.id));
    const it = cardAdd(card, `<div class="md-plan"><div><span class="tag">UMA on Modal ${tx(d.gpu || "")}</span>
        <b>${d.runs}</b> new runs of 40 ps (${d.total_runs} with the parents) · about <b>${Math.max(1, Math.round((d.wall_s || 0) / 60))}</b> min</div>
        <div class="md-view">${entry ? `<div class="lab-3d" id="md-${e.seq}"></div><p class="md-cap"></p>` :
          `<div class="md-anim"><i></i><i></i><i></i><i></i><i></i><i></i></div><p class="md-cap">${ionName(L.domain)} ions hopping at 600 K: the simulation follows every atom</p>`}</div></div>`);
    if (entry) mdScene(card, it.querySelector(".lab-3d"), entry);
    labLog(`Molecular dynamics launched: ${ids.map(fname).join(", ") || "candidates"} next to their parent crystals`);
    return 3800;
  }
  if (d.status === "start" || !d.status) return 900;
  const meta = STAGES[name];
  if (name === "ranking") {
    cardAdd(card, `<div class="podium">${(d.finalists || []).map((id, i) => `<div class="pod p${i + 1}"><span class="n">${i + 1}</span>
        <b>${tx(fname(id))}</b><span>${tx((d.levels || [])[i] && d.levels[i] !== "not_fitted" ? `${d.levels[i]} with its parent at 300 K` : "")}</span></div>`).join("")}</div>
      ${(d.levels || []).length && new Set(d.levels).size === 1 && d.levels[0] !== "not_fitted" ? `<p class="muted">Same level for the three: their order is a stated convention (lowest E<sub>hull</sub> per substitution, then activation energy, then window), not a significant difference.</p>` : ""}`);
    labLog(`Finalists: ${(d.finalists || []).map(fname).join(", ")}`, "good");
    return 4200;
  }
  if (name === "novelty") {
    cardAdd(card, `${d.control_ok ? `<span class="ok">control passed: ${L.domain === "cathode" ? "LiNi₀.₅Mn₁.₅O₄" : "LGPS"} found as published</span>` : `<span class="no">control not passed</span>`}
      <ul class="lc-list">${Object.entries(d.levels || {}).map(([id, lv]) => `<li><b>${tx(fname(id))}</b> <span class="chip">${tx(lv)}</span></li>`).join("")}</ul>`);
    return 3200;
  }
  if (d.status === "error") { cardAdd(card, `<span class="no">${tx(d.error || "error")}</span>`); return 1800; }
  if (meta && meta.done) cardAdd(card, `<span class="tag">done</span> ${tx(meta.done(d))}`);
  if (name === "molecular_dynamics" && (d.excluded || []).length) labLog(`Excluded after diffusion: ${d.excluded.map(fname).join(", ")}`, "bad");
  if (name === "electrodes" && (d.excluded || []).length) labLog(`Excluded at the electrodes: ${d.excluded.map(fname).join(", ")}`, "bad");
  return 1700;
}

function reasoningBox(card, e, ms) {
  const text = String(e.data.reasoning_summary || "").trim();
  if (!text) return 0;
  const box = cardAdd(card, `<div class="think-box"><span class="tag think">reasoning</span><p></p></div>`);
  typeInto(box.querySelector("p"), text.length > 700 ? text.slice(0, 700) + "…" : text, ms);
  return ms;
}

function playLLM(e) {
  const d = e.data || {}, r = d.reply || {}, who = modelOf(d.provider);
  if (e.step === "proposal") {
    const card = labCard(`proposal:${e.seq}`);
    cardHead(card, `Proposing new candidates${L.round ? ` · round ${L.round}` : ""}`, "substitutions in known crystals, each with its hypothesis", e);
    labActor(who, "reasoning about the next substitutions", "think");
    const t = reasoningBox(card, e, 2600);
    later(card, t + 200, () => cardAdd(card, `<div class="hypo"><span class="tag">hypothesis</span>${tx(r.hypothesis || "")}</div>`));
    (r.proposals || []).forEach((p, i) => later(card, t + 900 + i * 750, () => cardAdd(card,
      `<div class="prop"><span class="sub">${tx(L.parents[p.parent] || p.parent)} · ${tx(subText(p.substitution))}</span><span>${tx(p.rationale || "")}</span></div>`, "pop")));
    labLog(`${who} proposed ${(r.proposals || []).length} substitutions: ${r.hypothesis || ""}`);
    return t + 1500 + (r.proposals || []).length * 750 + 1500;
  }
  if (e.step === "analysis") {
    const card = labCard(`analysis:${e.seq}`);
    cardHead(card, `Learning from round ${L.round || ""}`, "the code measured; the causes below are the model's hypotheses", e);
    labActor(who, "interpreting the failures and correcting its strategy", "think");
    const t = reasoningBox(card, e, 2400);
    const fa = r.failure_analysis || [];
    fa.forEach((x, i) => later(card, t + 300 + i * 1100, () => cardAdd(card, `<div class="fa"><b>${tx(fname(x.id))}</b>
      <p><span class="tag bad">hypothesis</span>${tx(String(x.hypothesis || "").replace(/^\s*hypothesis\s*:\s*/i, ""))}</p>
      <p><span class="tag good">correction</span>${tx(String(x.correction || "").replace(/^\s*correction\s*:\s*/i, ""))}</p></div>`, "pop")));
    const tn = t + 400 + fa.length * 1100;
    if (r.next_direction) {
      later(card, tn, () => cardAdd(card, `<div class="hypo"><span class="tag">next direction</span>${tx(r.next_direction)}</div>`));
      labLog(`${who}: ${r.next_direction}`, "accent");
    }
    return tn + 2600;
  }
  if (e.step === "md_selection") {
    const card = L.stageGroup.md_selection && L.card && L.card.group === L.stageGroup.md_selection ? L.card : labCard(`llm:${e.seq}`);
    if (card.isNew) { card.isNew = false; cardHead(card, "Choosing what to simulate", "", e); }
    labActor(who, "deciding which candidate deserves molecular dynamics", "think");
    const t = reasoningBox(card, e, 2000);
    later(card, t + 200, () => cardAdd(card, `<div class="hypo"><span class="tag">decision</span>${(r.selected || []).length
      ? `simulate <b>${tx((r.selected || []).map((x) => fname(x.id || x)).join(", "))}</b> — ` : ""}${tx(r.rationale || "")}</div>`));
    return t + 2600;
  }
  if (e.step === "summary") {
    const card = labCard(`summary:${e.seq}`);
    cardHead(card, "Plain-language summary", "for readers who are not specialists", e);
    labActor(modelOf(d.provider), "summarizing in plain language", "think");
    const box = cardAdd(card, `<p class="plain"></p>`);
    typeInto(box.querySelector("p"), String(d.text || ""), 3800);
    return 5200;
  }
  if (e.step === "report") {
    const card = L.stageGroup.report && L.card && L.card.group === L.stageGroup.report ? L.card : labCard(`llm:${e.seq}`);
    if (card.isNew) { card.isNew = false; cardHead(card, "Final scientific report", "", e); }
    labActor(who, "writing the report from the numbers computed by the code", "think");
    return reasoningBox(card, e, 2600) + 1800;
  }
  const card = labCard(`llm:${e.seq}`);
  cardHead(card, e.step.replace(/_/g, " "), "", e);
  labActor(who, e.step.replace(/_/g, " "), "think");
  return reasoningBox(card, e, 2400) + 1200;
}

function candidateCard(e) {
  const card = labCard(`cand:${e.candidate_id}`);
  if (card.isNew) {
    card.isNew = false;
    const gen = S.events.find((x) => x.candidate_id === e.candidate_id && x.step === "generate");
    const formula = (gen && gen.data.formula) || fname(e.candidate_id);
    card.el.classList.add("cand");
    card.el.innerHTML = `<div class="lc-head"><div><h4 class="big">${tx(formula)}</h4><p class="sub-line"></p></div>
        ${L.reused ? `<span class="reuse" title="Taken from the saved results: nothing was recomputed">reused</span>` : ""}</div>
      <div class="cand-grid"><div class="cand-3d"><div class="lab-3d"></div><div class="cap3d"></div></div><div class="lc-body"></div></div>`;
  }
  return card;
}

function playCandidate(e) {
  const d = e.data || {}, id = e.candidate_id;
  if (e.step === "electrodes:done") {
    const card = stageCard("electrodes", d, e);
    cardAdd(card, `<div class="erow"><b>${tx(d.formula || fname(id))}</b>${voltBar(d.window, ionOf(L.domain))}
      <span class="${d.passivation === "non_passivating" ? "no" : "ok"}">${tx(d.passivation || "")}</span>
      <span class="muted">${d.window && d.window.stable ? `${fmt(d.window.v_low, 2)}–${fmt(d.window.v_high, 2)} V` : "zero width"}${d.interface_reaction_energy != null ? ` · LiFePO₄ ${fmt(d.interface_reaction_energy, 3)} eV/atom` : ""}</span></div>`, "row");
    if (d.excluded) labLog(`${d.formula}: reacts with ${ionName(L.domain)} metal (${d.passivation}) — excluded`, "bad");
    return d.iteration != null ? 1500 : 650;
  }
  if (e.step === "candidate_analyses:done") {
    const card = stageCard("candidate_analyses", d, e);
    labActor(modelOf(d.provider), `reviewing ${d.formula || fname(id)}`, "think");
    cardAdd(card, `<div class="review"><b>${tx(d.formula || fname(id))}</b> <span class="chip">${tx(`${L.domain === "cathode" ? "follow-up" : "MD"} priority: ${d.md_priority || "—"}`)}</span>
      <p>${tx(String(d.summary || "").slice(0, 220))}</p>
      ${(d.strengths || [])[0] ? `<p class="pos">+ ${tx(String(d.strengths[0]).slice(0, 160))}</p>` : ""}
      ${(d.risks || [])[0] ? `<p class="neg">− ${tx(String(d.risks[0]).slice(0, 160))}</p>` : ""}</div>`, "row");
    return 2300;
  }
  if (e.step === "molecular_dynamics:done") {
    const card = stageCard("molecular_dynamics", d, e);
    const r = d.ratio, X = (v) => Math.max(0, Math.min(100, (v / 2.5) * 100));
    cardAdd(card, `<div class="mrow"><b>${tx(d.formula || fname(id))}</b>
      <div class="ratio">${r != null ? `<em style="left:${X(1)}%"></em><i class="${d.conduction === "excluded" ? "bad" : ""}" style="left:${X(r)}%"></i>` : ""}</div>
      <span>D/D(parent) <b>${r != null ? r.toFixed(2) : "—"}</b> · <span class="chip">${tx(d.verdict || "—")}</span>
      ${d.conduction === "excluded" ? `<span class="no">excluded</span>` : ""}</span></div>`, "row");
    labLog(`${d.formula || fname(id)}: diffusion ${d.verdict || "—"} with its parent (D/D(parent) ${r != null ? r.toFixed(2) : "—"})${d.conduction === "excluded" ? " — excluded" : ""}`, d.conduction === "excluded" ? "bad" : "");
    return d.iteration != null ? 2400 : 900;
  }
  const card = candidateCard(e);
  if (e.step === "generate") {
    strip(card, "build");
    labActor("pymatgen", "builds the crystal structures and checks charge neutrality", "compute");
    card.el.querySelector(".sub-line").textContent = "";
    cardAdd(card, d.accepted ? `<span class="ok">charge-balanced ✓</span> ${d.arrangements > 1 ? `<b>${d.arrangements}</b> atomic arrangements built (random placements of the substituted sites)` : "one atomic arrangement (every site of the element replaced)"}`
      : `<span class="no">rejected before any simulation:</span> ${tx(d.reason || "")}`);
    const rel = aheadOf((x) => x.candidate_id === id && x.step === "relax" && x.data && x.data.structure);
    if (rel) {
      const st = rel.data.structure;
      card.el.querySelector(".sub-line").innerHTML = `${tx(st.removed && st.added ? `${st.removed} → ${st.added}` : "")}${st.li_vacancies ? ` · −${st.li_vacancies} Li (vacancies)` : ""}`;
      card.el.querySelector(".cap3d").innerHTML = `${legendHTML(new Set(st.symbols))}<p>${st.added ? `the substituted ${tx(st.added)} atoms flash as they replace ${tx(st.removed)}` : ""}</p>`;
      substitutionScene(card, st);
    } else card.el.querySelector(".cand-3d").classList.add("empty");
    if (!d.accepted) labLog(`${d.formula}: not charge-balanced — rejected before any simulation`, "bad");
    return 2400;
  }
  if (e.step === "known_check") {
    strip(card, "known");
    labActor("Materials Project", "checks whether the composition is already known", "data");
    cardAdd(card, (d.known || []).length ? `<span class="no">already known:</span> ${tx(d.known.map((k) => k.material_id || k).join(", "))} — not recomputed`
      : d.error ? `<span class="no">database unreachable:</span> computed anyway` : `<span class="ok">new composition</span> — not in Materials Project`);
    return 1200;
  }
  if (e.step === "relax") {
    strip(card, "relax");
    labActor("UMA", `relaxes ${d.arrangements} arrangements: atoms and cell move to their lowest energy`, "compute");
    const st = d.structure, ms = 3600;
    if (st) {
      const extra = card.el.querySelector(".cap3d p");
      if (extra) extra.textContent = st.trajectory && st.trajectory.length >= 2 ? `relaxation path recorded by UMA (${st.steps} steps)` : "start → relaxed structure (in-between frames interpolated)";
      cardAdd(card, `<div class="relax">${latticeHTML(st.start.lattice)}<p class="muted">cell before relaxation: a ${st.start.lattice.a.toFixed(3)}, b ${st.start.lattice.b.toFixed(3)}, c ${st.start.lattice.c.toFixed(3)} Å</p></div>`);
      relaxScene(card, st, ms);
    }
    const ep = d.energies_per_atom || [];
    if (ep.length) {
      const lo = Math.min(...ep), hi = Math.max(...ep) - lo || 1;
      const best = ep.indexOf(lo);
      cardAdd(card, `<div class="bars" title="energy of each relaxed arrangement, above the lowest">${ep.map((x, i) => `<i class="${i === best ? "best" : ""}" style="height:${8 + (92 * (x - lo)) / hi}%;animation-delay:${(i * 0.12) / L.speed}s"></i>`).join("")}</div>
        <p class="muted">${d.converged} of ${d.arrangements} converged · spread <b>${d.spread_meV}</b> meV/atom · kept: the lowest, <b>${lo.toFixed(4)}</b> eV/atom</p>`);
    }
    return ms + 1500;
  }
  if (e.step === "hull") {
    strip(card, "hull");
    labActor("UMA + Materials Project", `compute the convex hull against ${d.references} known phases, all relaxed with UMA`, "compute");
    cardAdd(card, gauge({ label: "energy above the convex hull", value: d.e_hull, min: Math.min(0, d.e_hull), max: Math.max(0.1, d.e_hull * 1.25), threshold: 0.05, better: "low", unit: "eV/atom" })
      + `<p class="muted">would decompose into ${tx((d.decomposition || []).map((x) => x.formula).join(" + "))} · per substitution <b>${fmt(d.e_hull_per_substitution)}</b> eV</p>`);
    return 2700;
  }
  if (e.step === "bandgap") {
    strip(card, "gap");
    labActor("GapModel", "predicts the electronic band gap", "compute");
    cardAdd(card, gauge({ label: "band gap (optB88)", value: d.gap_optb88, max: 6, threshold: 2, better: "high", unit: "eV", digits: 2 })
      + `<p class="muted">mBJ estimate <b>${fmt(d.gap_mbj, 2)}</b> eV${d.low_confidence ? " · low confidence" : ""}</p>`);
    return 2300;
  }
  if (e.step === "voltage") {
    strip(card, "charge");
    const k = d.li_removed, n = d.li_total;
    labActor("UMA", k ? `charges the crystal: ${k} of ${n} Li removed, the charged cell relaxed` : "charges the crystal: no Li can be removed", "compute");
    if (!k) { cardAdd(card, `<span class="no">no lithium can leave</span> — no element can be oxidised further`); return 1800; }
    if (d.error) { cardAdd(card, `<span class="no">${tx(d.error)}</span>`); return 1800; }
    const p = d.parent || {}, lim = d.limits || {};
    if (d.structure) {
      const cap = card.el.querySelector(".cap3d p");
      if (cap) cap.textContent = `${k} Li leave the crystal (fading), then the charged cell relaxes (in-between frames interpolated)`;
      chargeScene(card, d.structure, 3600);
      cardAdd(card, `<div class="relax">${latticeHTML(d.structure.lithiated.lattice)}<p class="muted">charged cell ${tx(d.delithiated_formula || "")}: V ${fmt(d.delithiated_volume_A3, 1)} Å³</p></div>`);
    }
    const band = (v) => Math.max(0, Math.min(100, ((v - 2) / 3.5) * 100));
    later(card, 1200, () => cardAdd(card, `<div class="gauge ${d.voltage_V >= lim.voltage[0] && d.voltage_V <= lim.voltage[1] ? "ok" : "bad"}">
        <div class="g-lbl">average voltage vs Li/Li⁺ (whole charge)</div>
        <div class="g-track vband"><i class="win" style="left:${band(lim.voltage[0])}%;width:${band(lim.voltage[1]) - band(lim.voltage[0])}%"></i>
          ${p.voltage_V != null ? `<em class="pmark" style="left:${band(p.voltage_V)}%" title="parent"></em>` : ""}
          <b class="vmark" style="left:${band(d.voltage_V)}%"></b></div>
        <div class="g-val"><b data-count="${d.voltage_V}" data-digits="2">0</b> V <span class="verdict">window ${lim.voltage[0]}–${lim.voltage[1]} V</span>
          ${p.voltage_V != null ? `<span class="muted"> · parent ${tx(d.parent_formula || "")} ${fmt(p.voltage_V, 2)} V</span>` : ""}</div></div>`));
    later(card, 2300, () => cardAdd(card, `<div class="stats-row">
        <span>capacity <b data-count="${d.capacity_mAh_g}" data-digits="0">0</b> mAh/g ${p.capacity_mAh_g != null ? `<em>parent ${fmt(p.capacity_mAh_g, 0)}</em>` : ""}</span>
        <span>energy density <b data-count="${d.energy_density_Wh_kg}" data-digits="0">0</b> Wh/kg ${p.energy_density_Wh_kg != null ? `<em>parent ${fmt(p.energy_density_Wh_kg, 0)}</em>` : ""}</span></div>`));
    later(card, 3200, () => cardAdd(card, gauge({ label: "volume change on charge", value: Math.abs(d.volume_change_pct), max: Math.max(15, Math.abs(d.volume_change_pct) * 1.3),
      threshold: lim.volume_change_max, better: "low", unit: "%", digits: 1 }) + (p.volume_change_pct != null ? `<p class="muted">parent ${fmt(p.volume_change_pct, 1)} %</p>` : "")));
    labLog(`${fname(id)}: ${fmt(d.voltage_V, 2)} V, ${fmt(d.capacity_mAh_g, 0)} mAh/g, ${fmt(d.energy_density_Wh_kg, 0)} Wh/kg${p.voltage_V != null ? ` (parent ${fmt(p.voltage_V, 2)} V, ${fmt(p.energy_density_Wh_kg, 0)} Wh/kg)` : ""}`, "accent");
    return 5600;
  }
  if (e.step === "ss_check") {
    cardAdd(card, d.ss_bonds ? `<span class="no">S–S bonds present</span> (a warning: the potential is less reliable there)` : `<span class="ok">no S–S bond</span>`);
    return 600;
  }
  if (e.step === "done") {
    strip(card, "verdict");
    const ok = d.status === "passed";
    cardAdd(card, `<div class="stamp ${ok ? "ok" : "bad"}">${ok ? "PASSED" : `REJECTED · ${tx(d.rejected_at || "")}`}</div>${d.reason ? `<p class="muted">${tx(d.reason)}</p>` : ""}`);
    labLog(ok ? `${fname(id)} passed the fast filters (stability, band gap)` : `${fname(id)} rejected at ${d.rejected_at}: ${d.reason || ""}`, ok ? "good" : "bad");
    return 1900;
  }
  return 400;
}

function playLoop(e) {
  const d = e.data || {};
  if (e.step === "scope") {
    const card = labCard("scope");
    cardHead(card, "Research goal understood", d.title || "", e);
    labActor("Muse Spark", "reading the request and setting its constraints", "think");
    cardAdd(card, `<div class="chips">${(d.constraints || []).map((c) => `<span class="chip accent">${tx(c)}</span>`).join("")}</div>
      <p class="muted">intent: ${tx(d.intent || "")} · domain: ${tx(d.domain || "")}</p>`);
    return 2600;
  }
  if (e.step === "start") {
    L.rounds = d.n_iterations || 0;
    for (const p of d.parents || []) L.parents[p.id] = p.formula;
    const card = labCard("plan");
    cardHead(card, "Research plan", `${d.n_iterations} rounds, up to ${d.max_candidates} candidates each`, e);
    labActor("AutoLab", "planning the campaign", "plan");
    const th = d.thresholds || {};
    L.domain = d.domain || L.domain;
    const cathode = L.domain === "cathode";
    const team = cathode ? [["Muse Spark", "proposes, decides, interprets failures, writes the report", "think"],
      ["Muse Spark Open", "reviews each candidate independently", "think"], ["Muse Glimmer", "summarizes in plain language", "think"],
      ["UMA", "relaxes the lithiated and the charged crystals", "compute"], ["pymatgen", "builds the substitutions, checks charge neutrality", "compute"],
      ["Materials Project", "known phases for the convex hull", "data"]]
      : [["Muse Spark", "proposes, decides, interprets failures, writes the report", "think"],
      ["Muse Spark Open", "reviews each candidate independently", "think"], ["Muse Glimmer", "summarizes in plain language", "think"],
      ["UMA", "relaxes crystals and runs molecular dynamics", "compute"], ["GapModel", "predicts band gaps", "compute"],
      ["Materials Project", "known phases and DFT references", "data"]];
    cardAdd(card, `<div class="plan-box"><div><span class="tag">parent crystals</span>${(d.parents || []).map((p) => `<span class="chip">${tx(p.formula)} · ${esc(p.id)}</span>`).join(" ")}</div>
      <div><span class="tag">filters</span>${cathode
        ? `no cobalt · E<sub>hull</sub> ≤ ${th.CATHODE_EHULL_MAX} eV/atom · voltage ${th.CATHODE_VOLTAGE_MIN}–${th.CATHODE_VOLTAGE_MAX} V · capacity ≥ ${th.CATHODE_CAPACITY_MIN} mAh/g · volume change ≤ ${th.CATHODE_VOLUME_CHANGE_MAX} %`
        : L.domain === "sodium"
        ? `E<sub>hull</sub> ≤ ${th.SODIUM_EHULL_MAX ?? 0.05} eV/atom · band gap ≥ ${th.SODIUM_BANDGAP_MIN ?? 1.8} eV · contact with sodium metal · Na diffusion at 600 K`
        : `E<sub>hull</sub> ≤ ${th.EHULL_SYNTHESIZABLE ?? 0.05} eV/atom · band gap ≥ ${th.BANDGAP_MIN ?? 2} eV · Li diffusion at ${th.MD_SCREEN_TEMPERATURE_K ?? 600} K`}</div>
      ${(d.prior || []).length ? `<div><span class="tag">memory</span>${d.prior.length} candidates from earlier researches, reused, never recomputed</div>` : ""}</div>`);
    team.forEach(([m, role, k], i) => later(card, 500 + i * 320, () => cardAdd(card, `<span class="model ${k}">${tx(m)}</span> ${tx(role)}`, "team pop")));
    return 4600;
  }
  if (e.step === "iteration") {
    L.round = d.iteration;
    const card = labCard(`round:${d.iteration}`);
    card.el.classList.add("banner");
    card.el.innerHTML = `<div class="round-n">Round ${d.iteration}${L.rounds ? `<small> of ${L.rounds}</small>` : ""}</div>
      <p>${d.iteration > 1 ? "The failures of the last round are back with the agent: it now proposes corrected candidates." : "The agent proposes its first candidates."}</p>`;
    labActor("AutoLab", `round ${d.iteration}`, "plan");
    labLog(`Round ${d.iteration} started`, "accent");
    return 2400;
  }
  if (e.step === "feedback") {
    const card = labCard(`feedback:${e.seq}`);
    cardHead(card, `Slow tests of round ${d.iteration}: results sent back to Muse Spark`, "measured numbers only; the explanation comes next", e);
    labActor("AutoLab", "sending the measured failures back to the agent", "plan");
    const res = d.results || [];
    res.forEach((f, i) => later(card, 300 + i * 900, () => cardAdd(card, `<p class="${f.outcome === "failed" ? "neg" : "pos"}">${tx(f.message)}</p>`, "pop")));
    labLog(`${res.filter((f) => f.outcome === "failed").length} failures and ${res.filter((f) => f.outcome !== "failed").length} successes sent back to Muse Spark`, "accent");
    return 900 + res.length * 900 + 1800;
  }
  if (e.step === "stop") {
    const card = labCard("stop");
    card.el.classList.add("banner", "final");
    card.el.innerHTML = `<div class="round-n">Research complete</div><p>${tx(d.reason || "")}</p><p class="muted">The research card, the summary and the final report follow.</p>`;
    labActor("AutoLab", "research complete", "plan");
    labLog("Research complete: final ranking ready", "good");
    return 2600;
  }
  return 250;
}

function labPlay(e) {
  if (e.type === "candidate") return playCandidate(e);
  if (e.type === "llm") return playLLM(e);
  if (e.type === "stage") return playStage(e);
  if (e.type === "loop") return playLoop(e);
  return 250;
}

const STEP_ACTOR = { voltage: ["UMA", "charges the crystal: removes lithium and relaxes the charged cell", "compute"],
  goal: ["Muse Spark", "reading the request", "think"], propose: ["Muse Spark", "reasoning about new substitutions", "think"],
  build: ["UMA", "relaxes the crystal structures", "compute"], stability: ["UMA + Materials Project", "compute the convex hull", "compute"],
  bandgap: ["GapModel", "predicts band gaps", "compute"], learn: ["Muse Spark", "interpreting the results", "think"],
  electrodes: ["pymatgen", "computes the phase diagrams against the electrodes", "compute", "Muse Spark's candidates"],
  review: ["Muse Spark Open", "reviewing each candidate", "think"],
  md_choice: ["Muse Spark", "choosing what to simulate", "think"],
  md: ["UMA", "runs molecular dynamics at 600 K on Modal H100", "compute", "Muse Spark's choice"],
  conductivity: ["AutoLab", "Arrhenius extrapolation to 300 K", "compute"], ranking: ["AutoLab", "ranking the candidates", "plan"],
  literature: ["Muse Spark", "searching the literature", "think"], report: ["Muse Spark", "writing the final report", "think"] };

function labWorking() {
  const run = (S.view.steps || []).find((s) => s.state === "running");
  const [who, what, kind, origin] = (run && STEP_ACTOR[run.key]) || ["AutoLab", "working", "compute"];
  labActor(who, what, kind, origin);
  if (L.group === "working") return;
  const card = labCard("working");
  card.el.classList.add("banner", "working");
  card.el.innerHTML = `<div class="pulse"><i></i><i></i><i></i></div><p><b>${tx(run ? run.label : "Working")}</b></p>
    <p class="muted">${TOOLS.has(who) ? `${tx(who)} is computing on ${tx(origin || "Muse Spark's candidate")}` : `${tx(who)} is working`}; the next result appears as soon as it is ready.</p>`;
}


/* ---------- start ---------- */

window.addEventListener("popstate", route);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (themeChoice() === "system") applyTheme("system"); });
applyTheme(themeChoice());
loadHistory().then(route);
setInterval(() => { if (S.history.some((c) => ACTIVE.has(c.status))) loadHistory(); }, 15000);
