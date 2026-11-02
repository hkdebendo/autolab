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

async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    method: opts.method || "GET",
    headers: opts.body ? { "Content-Type": "application/json" } : undefined,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
  return data;
}

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
  const m = location.pathname.match(/^\/c\/([\w-]+)/);
  if (m) openConversation(m[1]);
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
  try { S.history = await api("/conversations"); } catch (e) { S.history = S.history || []; }
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
  if (!S.history.length) { nav.innerHTML = `<p class="h-empty">Your researches will appear here.</p>`; return; }
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
});
$("settings-btn").onclick = () => { applyTheme(themeChoice()); openModal("settings"); };
$("theme-choice").addEventListener("change", (e) => applyTheme(e.target.value));
$("theme-btn").onclick = () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");

/* ---------- tutorial: five cards (interface.md 5) ---------- */

const TUT = [
  { title: "Understand the research goal",
    text: "AutoLab reads your goal in natural language, identifies the constraints and the properties you care about, checks that it is within the research areas it supports, and plans the investigation.",
    points: ["Free-text request, no form to fill", "Constraints and target properties extracted", "Honest answer when a request is not supported yet"],
    art: `<svg viewBox="0 0 200 120"><rect x="18" y="22" width="112" height="44" rx="12"/><path d="M40 40h68M40 52h44"/><circle cx="160" cy="70" r="22"/><circle cx="160" cy="70" r="11"/><circle cx="160" cy="70" r="2.5" fill="currentColor"/><path d="M130 66l12 4"/></svg>` },
  { title: "Generate candidate materials",
    text: "AutoLab proposes new compositions by chemical substitution in known crystals, builds several atomic arrangements for each and keeps only charge-balanced, not-yet-known compositions.",
    points: ["Substitutions in known lithium thiophosphates", "Charge neutrality checked before any simulation", "Compositions already in Materials Project are not recomputed"],
    art: `<svg viewBox="0 0 200 120"><g>${[0, 1, 2, 3, 4].map((i) => [0, 1, 2].map((j) => `<circle cx="${40 + i * 30}" cy="${30 + j * 30}" r="${(i + j) % 3 === 1 ? 8 : 5}" ${(i === 2 && j === 1) ? 'fill="currentColor"' : ""}/>`).join("")).join("")}</g><path d="M40 30h120M40 60h120M40 90h120M40 30v60M70 30v60M100 30v60M130 30v60M160 30v60" opacity=".35"/></svg>` },
  { title: "Evaluate stability and electronic properties",
    text: "Promising structures are relaxed with a machine-learned interatomic potential. Their energy above the convex hull tells whether they would decompose, and their band gap whether they would conduct electrons.",
    points: ["Energy above the hull: at most 0.05 eV/atom", "Band gap: at least 2 eV for an electrolyte", "Every energy from the same method, never mixed"],
    art: `<svg viewBox="0 0 200 120"><path d="M20 100h170M20 100V14"/><path d="M28 30 L70 80 L120 72 L176 34"/><circle cx="70" cy="80" r="4" fill="currentColor"/><circle cx="120" cy="72" r="4" fill="currentColor"/><circle cx="96" cy="58" r="4"/><path d="M96 62v13" stroke-dasharray="3 3"/></svg>` },
  { title: "Simulate ion transport and interfaces",
    text: "For the most promising materials, AutoLab checks the electrochemical window and the reaction with lithium metal and with a cathode, then simulates lithium-ion motion by molecular dynamics and compares it with the parent crystal.",
    points: ["Window and contact with lithium metal", "Lithium diffusion at 600 K, two independent runs", "Ionic conductivity at room temperature is not computed yet"],
    art: `<svg viewBox="0 0 200 120"><rect x="20" y="16" width="160" height="88" rx="10"/><path d="M36 84 C60 30, 90 100, 112 56 S 150 30, 166 40" stroke-dasharray="4 4"/><circle cx="36" cy="84" r="5" fill="currentColor"/><circle cx="166" cy="40" r="5" fill="currentColor"/></svg>` },
  { title: "Compare, rank and explore",
    text: "AutoLab ranks the candidates with explicit criteria, checks the literature, and writes a report on three finalists with a detailed analysis of the best compromise. Everything is saved: you can reopen it and ask follow-up questions.",
    points: ["Three finalists, one champion, with their limits", "Literature check with sources", "Saved research, follow-up questions"],
    art: `<svg viewBox="0 0 200 120"><rect x="76" y="34" width="48" height="70" rx="4"/><rect x="24" y="56" width="48" height="48" rx="4"/><rect x="128" y="68" width="48" height="36" rx="4"/><path d="M100 14l5 10 11 1.5-8 7.5 2 11-10-5.5-10 5.5 2-11-8-7.5 11-1.5z" fill="currentColor"/></svg>` },
];
let tutIndex = 0;
function renderTutorial() {
  const c = TUT[tutIndex];
  $("tut-art").innerHTML = c.art;
  $("tut-step").textContent = `Step ${tutIndex + 1} of ${TUT.length}`;
  $("tut-title").textContent = c.title;
  $("tut-text").textContent = c.text;
  $("tut-points").innerHTML = c.points.map((p) => `<li>${esc(p)}</li>`).join("");
  $("tut-dots").innerHTML = TUT.map((_, i) => `<i class="${i === tutIndex ? "on" : ""}"></i>`).join("");
  $("tut-prev").disabled = tutIndex === 0;
  $("tut-next").textContent = tutIndex === TUT.length - 1 ? "Done" : "Next";
}
$("tutorial-btn").onclick = () => { tutIndex = 0; renderTutorial(); openModal("tutorial"); };
$("tut-prev").onclick = () => { if (tutIndex > 0) { tutIndex--; renderTutorial(); } };
$("tut-next").onclick = () => { if (tutIndex < TUT.length - 1) { tutIndex++; renderTutorial(); } else closeModal("tutorial"); };

/* ---------- home ---------- */

const EXAMPLES = [  // the first one is the recorded research of Nov 1, word for word: sending it reuses that research
  "Find new sulfide solid electrolytes for lithium-metal batteries, derived from Li7P3S11 or beta-Li3PS4, that conduct lithium at least as fast as their parent and stay stable against lithium metal. Learn from the candidates that fail.",
  "Find new sulfide solid electrolytes for lithium-metal batteries that stay stable against lithium metal.",
  "Explore halide substitutions in Li7P3S11 to improve lithium-ion diffusion.",
  "Which substitutions in beta-Li3PS4 keep it stable and electronically insulating?",
];

function showHome() {
  stopTimers();
  S.id = null; S.view = null; S.events = []; S.next = 0; S.index = null;
  disposeViewers();
  document.querySelector(".main").classList.add("home");
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
  ex.innerHTML = EXAMPLES.map((t, i) => `<button type="button" data-i="${i}">${tx(t)}</button>`).join("");
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
  if (S.id !== id) { S.events = []; S.next = 0; S.index = null; S.tab = "progress"; disposeViewers(); }
  S.id = id;
  renderHistory();
  try {
    const v = await api(`/conversations/${id}`);
    showConversation(v);
  } catch (e) {
    $("view").innerHTML = `<div class="thread"><div class="notice warn">This research could not be opened: ${esc(e.message)}.</div></div>`;
    setComposer("new");
  }
}

async function showConversation(v) {
  S.view = v;
  S.id = v.conversation.id;
  refreshCrumb();
  renderHistory();
  if (v.events_count) await fetchProgress(true);
  if (!ACTIVE.has(v.conversation.status) && v.files.includes("index.json") && !S.index) {
    try { S.index = await api(`/conversations/${S.id}/files/index.json`); } catch { S.index = null; }
  }
  const reused = v.conversation.scope && v.conversation.scope.reused_from;
  const ask = new URLSearchParams(location.search);  // ?watch[=speed]: play a finished research again (filming)
  const play = ACTIVE.has(v.conversation.status) ? "live"
    : (S.autoplay && reused) || ask.has("watch") ? (S.events.length ? "watch" : null) : null;
  S.autoplay = false;
  if (ask.has("watch")) {
    if (+ask.get("watch")) { L.speed = Math.max(1, Math.min(4, +ask.get("watch"))); L.speedSet = true; }
    history.replaceState({}, "", location.pathname);
  }
  if (play) { await labStart(play); setComposer(composerMode()); return; }
  renderThread();
  setComposer(composerMode());
  scrollBottom(true);
}

function refreshCrumb() {
  const c = S.history.find((x) => x.id === S.id);
  $("crumb").textContent = chem(c ? c.title : S.view?.conversation.title || "");
  document.title = `${$("crumb").textContent || "AutoLab"} · AutoLab`;
}

async function fetchProgress(all = false) {
  const p = await api(`/conversations/${S.id}/progress?after=${all ? 0 : S.next}`);
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
      const p = await fetchProgress();
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

const userMsg = (t) => `<div class="msg user"><div class="bubble">${tx(t)}</div></div>`;
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
  const lab = L.on;
  const place = () => {
    if (researchPlaced) return;
    parts.push(lab ? aiBlock(`<div id="lab-slot"></div>`, "lab-msg") : aiBlock(`<div id="research"></div>`));
    researchPlaced = true;
  };
  for (const m of v.messages) {
    if (m.role === "user") { parts.push(userMsg(m.content)); continue; }
    if (m.kind === "scope") {
      parts.push(aiBlock(`${who("Muse Spark", "read the request", "think")}<div class="prose">${md(m.content)}</div>`));
      if (hasResearch && !(v.messages.some((x) => x.data && x.data.action === "reused"))) place();
    } else if (m.kind === "notice") {
      const newChat = m.data && m.data.action === "new_chat", reused = m.data && m.data.action === "reused";
      if (lab && !reused && !newChat) continue;
      parts.push(aiBlock(`<div class="notice${newChat ? " warn" : reused ? " reused" : ""}">${tx(m.content)}${newChat
        ? `<div class="actions"><button class="primary-btn" type="button" data-newchat="${m.id}">New chat</button></div>` : ""}</div>`));
      if (reused && hasResearch) place();
    } else if (m.kind === "summary") {
      if (lab) continue;
      parts.push(aiBlock(`<div class="prose summary"><p>${tx(m.content)}</p></div>`));
    } else if (m.kind === "report") {
      if (lab) continue;
      parts.push(aiBlock(`${who("Muse Spark", "wrote the report from the numbers computed by the code", "think")}${reportBlock(m)}`));
    } else {
      parts.push(aiBlock(`<div class="prose">${md(m.content)}</div>`));
    }
  }
  if ((hasResearch || lab) && !researchPlaced) place();
  $("view").innerHTML = `<div class="thread">${parts.join("")}</div>`;
  if (lab && L.el) $("lab-slot").appendChild(L.el);
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
      ${!ACTIVE.has(st) && S.events.length ? `<button class="ghost-btn watch" type="button" id="watch-agent"><svg viewBox="0 0 24 24"><path d="M8 6l10 6-10 6z"/></svg><span>Watch the agent at work</span></button>` : ""}
      <span class="badge ${ACTIVE.has(st) ? (st === "stopping" ? "stopping" : "running") : st}">${esc(badge)}</span></div>
    <div class="tabs" role="tablist">${tabs.map(([k, l, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${S.tab === k}">${l}${n ? `<span class="count">${n}</span>` : ""}</button>`).join("")}</div>
    <div class="tab-panel" id="tab-panel"></div></section>`;
  const watch = $("watch-agent");
  if (watch) watch.onclick = () => labStart("watch");
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
  return `<div class="table-scroll"><table class="data"><thead><tr><th>Material</th><th>E<sub>hull</sub> (eV/atom)</th><th>Band gap (eV)</th>
    <th>Window (V)</th><th>Li metal</th><th>D / D(parent)</th><th>Status</th></tr></thead><tbody>
    ${cands.map((c) => `<tr class="${hasStructure(c.id) ? "clickable" : ""}" data-id="${esc(c.id)}">
      <td class="formula">${tx(c.formula || c.id)}</td><td class="num">${fmt(c.e_hull)}</td><td class="num">${fmt(c.gap, 2)}</td>
      <td class="num">${c.window ? (c.window.stable ? `${fmt(c.window.v_low, 2)}–${fmt(c.window.v_high, 2)}` : "zero width") : "—"}</td>
      <td>${esc(c.passivation || "—")}</td>
      <td class="num">${c.ratio !== undefined ? `${fmt(c.ratio, 2)} <span class="muted">(${esc(c.verdict)})</span>` : "—"}</td>
      <td>${statusChip(c)}</td></tr>`).join("")}</tbody></table></div>
    <p class="viewer-cap">${S.index ? "Click a material to see its crystal structure in 3D." : "3D structures become available when the research is finished."}
    E<sub>hull</sub>: energy above the convex hull (≤ 0.05 kept). D / D(parent): lithium diffusion relative to the parent crystal at 600 K.</p>`;
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
  As: "#BD80E3", Sb: "#9E63B5", Sn: "#668080", Fe: "#E06633", Mn: "#9C7AC7", Co: "#F090A0", N: "#3050F8", C: "#909090" };
const NAMES = { Li: "lithium", Na: "sodium", Mg: "magnesium", Al: "aluminium", Si: "silicon", P: "phosphorus", S: "sulfur",
  Cl: "chlorine", O: "oxygen", F: "fluorine", Br: "bromine", I: "iodine", Se: "selenium", Ge: "germanium", As: "arsenic",
  Sb: "antimony", Sn: "tin", Fe: "iron", Mn: "manganese", Co: "cobalt", N: "nitrogen", C: "carbon" };

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
    const st = await api(`/conversations/${S.id}/files/${entry.file}`);
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
  $("viewer-body").innerHTML = `<div class="viewer3d tall" id="big-view"></div><div id="big-legend"></div><div id="big-info" class="stats"></div>`;
  openModal("viewer-modal");
  try {
    const st = await api(`/conversations/${S.id}/files/${entry.file}`);
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
    box.innerHTML = `<div class="unavailable">${S.index ? "No molecular dynamics was run in this research." : "Lithium-diffusion animations become available when the research is finished."}</div>`;
    return;
  }
  const ids = [...new Set(cands.map((e) => e.id))];
  box.innerHTML = `<figure class="chart"><h4>Lithium-ion diffusion (molecular dynamics, 600 K)</h4>
    <div class="viz-controls"><label>Material <select id="md-pick">${ids.map((id) => `<option value="${esc(id)}">${tx(cands.find((e) => e.id === id).formula)}</option>`).join("")}</select></label>
      <label>Run <select id="md-seed"></select></label>
      <button class="ghost-btn" type="button" id="md-play">Pause</button>
      <input type="range" id="md-frame" min="0" max="399" value="0" aria-label="Time"></div>
    <div class="viewer-row"><div><div class="viewer3d" id="md-a"></div><p class="viewer-cap" id="md-a-cap"></p></div>
      <div><div class="viewer3d" id="md-b"></div><p class="viewer-cap" id="md-b-cap"></p></div></div>
    <p class="stats" id="md-time"></p>
    <div class="legend"><span><i style="background:#3b82f6"></i>Li within 1.5 Å of its start (vibrating)</span>
      <span><i style="background:#f59e0b"></i>Li 1.5–3 Å away</span><span><i style="background:#dc2626"></i>Li over 3 Å away (hopped)</span>
      <span class="muted">framework atoms in CPK colours, at their starting positions</span></div>
    <div id="md-curve"></div><p class="stats" id="md-stats"></p>
    <figcaption>The animation shows the lithium positions recorded during the simulation (one frame every 0.1 ps). The framework is drawn fixed: only its mean displacement was recorded (grey curves below).</figcaption></figure>`;
  const md = { a: null, b: null, frame: 0, playing: true };
  const seeds = () => {
    const id = $("md-pick").value;
    $("md-seed").innerHTML = cands.filter((e) => e.id === id).map((e) => `<option value="${e.seed}">${e.seed + 1}</option>`).join("");
  };
  const load = async () => {
    clearInterval(S.mdTimer);
    const id = $("md-pick").value, seed = +$("md-seed").value;
    const entry = S.index.md.find((e) => e.id === id && e.seed === seed);
    md.a = await api(`/conversations/${S.id}/files/${entry.file}`);
    const pe = S.index.md.find((e) => e.id === md.a.parent && e.seed === seed) || S.index.md.find((e) => e.id === md.a.parent);
    md.b = pe ? await api(`/conversations/${S.id}/files/${pe.file}`) : null;
    md.frame = 0;
    $("md-frame").max = md.a.frames.length - 1;
    for (const v of S.viewers) { try { v.clear(); } catch { /* */ } }
    S.viewers = [];
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
    for (const p of data.frames[frameOf(data, f)]) { syms.push("Li"); pos.push(p); }
    v.addModel(xyz(syms, pos), "xyz");
    v.setStyle({}, { sphere: { scale: 0.26, colorscheme: "Jmol" } });
    const disp = (data.displacement_A || [])[frameOf(data, f)] || [];
    v.setStyle({ elem: "Li" }, { sphere: { scale: 0.42, colorfunc: (atom) => { const d = disp[atom.index - nF] || 0; return d < 1.5 ? "#3b82f6" : d < 3 ? "#f59e0b" : "#dc2626"; } } });
    drawCell(v, data.cell);
    if (!v._zoomed) { v.zoomTo(); v._zoomed = true; }
    v.render();
  };
  const draw = () => {
    drawOne(md.va, md.a, md.frame); drawOne(md.vb, md.b, md.frame);
    const t = (md.frame * md.a.frame_fs) / 1000, hop = (d) => (d ? d.filter((x) => x > 3).length : 0);
    const da = (md.a.displacement_A || [])[md.frame], db = md.b && (md.b.displacement_A || [])[frameOf(md.b, md.frame)];
    $("md-time").innerHTML = `<span>t = <b>${t.toFixed(1)} ps</b></span><span>${tx(md.a.formula)}: <b>${hop(da)} / ${md.a.frames[0].length}</b> Li hopped</span>` +
      (db ? `<span>${tx(md.b.formula)}: <b>${hop(db)} / ${md.b.frames[0].length}</b> Li hopped</span>` : "");
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
  return `${s}</svg><p class="viewer-cap">The slope of the lithium curve gives the diffusion coefficient D; a flat framework curve means the crystal stays intact.</p>`;
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
  const root = $("print-root");
  const c = S.view.conversation;
  let img = "";
  const champ = rep.querySelector("[data-champion]");
  if (champ && window.$3Dmol) {  // a still image of the champion's structure for the paper version
    try {
      const entry = S.index.structures.find((s) => s.id === champ.dataset.champion);
      const st = await api(`/conversations/${S.id}/files/${entry.file}`);
      const holder = document.createElement("div");
      holder.style.cssText = "position:fixed;left:-2000px;top:0;width:600px;height:420px";
      document.body.appendChild(holder);
      const v = window.$3Dmol.createViewer(holder, { backgroundColor: "white" });
      drawCrystal(v, st, true);
      img = `<img alt="Crystal structure of ${esc(entry.formula)}" src="${v.pngURI()}">`;
      holder.remove();
    } catch { img = ""; }
  }
  root.innerHTML = `<h1>${tx(c.title)}</h1><p class="meta">AutoLab research report · ${esc(new Date(c.updated_at).toLocaleString())}<br>Goal: ${esc(c.goal)}</p>
    ${img}${rep.querySelector(".prose").innerHTML}`;
  document.body.classList.add("printing");
  const done = () => { document.body.classList.remove("printing"); root.innerHTML = ""; window.removeEventListener("afterprint", done); };
  window.addEventListener("afterprint", done);
  setTimeout(() => window.print(), 60);
}

/* ---------- live lab: the agent at work ----------
   The events of a research are played one by one as cards: what is being done, by which model or tool, with its
   numbers and its 3D structure; a card leaves when the next action starts, the progress list ticks as steps finish,
   and the decisions are written in the lab notebook. While a research runs, events arrive over a WebSocket (polling
   as a fallback). Results taken from the saved computations are played at a readable pace and marked "reused".
   Nothing shown here is invented: every number comes from an event; an animation between two recorded structures
   is labelled as such. */

const PROVIDER_MODEL = { meta: "Muse Spark", baseten: "Muse Spark Open", fireworks: "Muse Glimmer" };
const LAB_BG = "#0a1222";
const L = { on: false, mode: null, el: null, queue: [], seen: new Set(), played: 0, speed: 1, paused: false,
  group: null, card: null, timer: null, ws: null, steps: [], round: 0, rounds: 0, reused: false, t0: 0,
  formulas: {}, parents: {}, stageGroup: {}, clock: null, stepsAsked: 0 };

const ease = (u) => (u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2);
const lerp = (a, b, k) => a + (b - a) * k;
const lerpRows = (A, B, k) => A.map((r, i) => r.map((x, j) => lerp(x, (B[i] || r)[j], k)));
const modelOf = (p) => PROVIDER_MODEL[p] || "Muse Spark";
const fname = (id) => L.formulas[id] || id;
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
    round: 0, rounds: 0, formulas: {}, parents: {}, stageGroup: {}, t0: Date.now(), stepsAsked: 0 });
  L.reused = !!(S.view && S.view.conversation.scope && S.view.conversation.scope.reused_from);
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
  scrollBottom();
}

function labStop() {
  clearTimeout(L.timer); clearInterval(L.clock);
  if (L.card) labDispose(L.card);
  L.card = null; L.on = false;
  if (L.ws) { try { L.ws.close(); } catch { /* closed */ } L.ws = null; }
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
        <button type="button" data-pause aria-label="Pause">${PAUSE}</button>
        <button type="button" data-skip>Results</button></div></header>
    <div class="lab-body">
      <aside class="lab-steps"><h5>Progress</h5><ol></ol><div class="lab-bar"><i></i></div></aside>
      <div class="lab-stage">
        <div class="lab-actor"></div>
        <div class="lab-slot"></div>
        <div class="lab-log"><h5>Lab notebook</h5><ul></ul></div>
      </div></div>`;
  el.querySelector(".lab-ctl").onclick = (ev) => {
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.speed) {
      L.speed = +b.dataset.speed;
      L.speedSet = true;
      for (const x of el.querySelectorAll("[data-speed]")) x.classList.toggle("on", x === b);
    } else if (b.hasAttribute("data-pause")) {
      L.paused = !L.paused;
      b.classList.toggle("on", L.paused);
      b.innerHTML = L.paused ? `<svg viewBox="0 0 24 24"><path d="M8 6l10 6-10 6z"/></svg>` : PAUSE;
    } else if (b.hasAttribute("data-skip")) {
      L.queue = [];
      if (!ACTIVE.has(S.view.conversation.status)) labFinish();
    }
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

function labActor(who, what, kind = "compute") {
  const a = L.el.querySelector(".lab-actor");
  a.dataset.kind = kind;
  a.innerHTML = `<span class="model ${kind}">${tx(who)}</span><span class="what">${tx(what)}</span><span class="dots"><i></i><i></i><i></i></span>`;
  L.el.querySelector(".orb").dataset.kind = kind;
}

function labLog(text, tone = "") {
  const ul = L.el.querySelector(".lab-log ul");
  const li = document.createElement("li");
  li.className = tone;
  li.innerHTML = `<span class="r">${L.round ? `R${L.round}` : "—"}</span>${tx(text)}`;
  ul.prepend(li);
  while (ul.children.length > 6) ul.lastChild.remove();
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
  const ok = better === "low" ? value <= threshold : value >= threshold;
  return `<div class="gauge ${ok ? "ok" : "bad"}"><div class="g-lbl">${tx(label)}</div>
    <div class="g-track"><div class="g-fill" data-w="${pct(value)}"></div>
      <div class="g-thr" style="left:${pct(threshold)}%"><span>limit ${threshold} ${tx(unit)}</span></div></div>
    <div class="g-val"><b data-count="${value}" data-digits="${digits}">0</b> ${tx(unit)} <span class="verdict">${ok ? "within the limit" : "outside the limit"}</span></div></div>`;
}

function strip(card, active) {
  const names = [["build", "Build"], ["known", "Novelty"], ["relax", "Relax"], ["hull", "Stability"], ["gap", "Band gap"], ["verdict", "Verdict"]];
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
    for (const p of data.frames[f]) { syms.push("Li"); pos.push(p); }
    v.addModel(xyz(syms, pos), "xyz");
    v.setStyle({}, { sphere: { scale: 0.24, colorscheme: "Jmol" } });
    const disp = (data.displacement_A || [])[f] || [];
    v.setStyle({ elem: "Li" }, { sphere: { scale: 0.4, colorfunc: (a) => { const d = disp[a.index - nF] || 0; return d < 1.5 ? "#3b82f6" : d < 3 ? "#f59e0b" : "#ef4444"; } } });
    drawCell(v, data.cell);
    if (!v._zoomed) { v.zoomTo(); v._zoomed = true; }
    v.render();
    const t = (f * data.frame_fs) / 1000, hop = disp.filter((x) => x > 3).length;
    const cap = card.el.querySelector(".md-cap");
    if (cap) cap.innerHTML = `${tx(data.formula)} · t = <b>${t.toFixed(1)} ps</b> · <b>${hop}</b> of ${data.frames[0].length} Li hopped more than 3 Å`;
    f = (f + 1) % data.frames.length;
  };
  const timer = setInterval(frame, 80);
  card.cleanup.push(() => clearInterval(timer));
  frame();
}

function voltBar(w) {
  const X = (v) => Math.max(0, Math.min(100, (v / 5) * 100));
  const seg = w && w.stable ? `<i class="win" style="left:${X(w.v_low)}%;width:${Math.max(0.6, X(w.v_high) - X(w.v_low))}%"></i>` : `<i class="win none"></i>`;
  return `<div class="volt">${seg}<em class="li" style="left:0%">Li</em><em class="fe" style="left:${X(3.45)}%">LiFePO₄</em></div>`;
}

function aheadOf(pred) { return L.queue.find(pred) || S.events.find(pred); }

/* what each event shows */

const STAGES = {
  electrodes: { title: "Electrodes: stability window, lithium metal, cathode", actor: ["pymatgen", "grand-potential phase diagrams against the electrodes", "compute"],
    done: (d) => `${d.computed ?? 0} computed${(d.excluded || []).length ? ` · excluded: ${d.excluded.map(fname).join(", ")}` : ""}` },
  candidate_analyses: { title: "Independent reviews", actor: ["Muse Spark Open", "reviewing each candidate separately", "think"],
    done: (d) => (d.skipped ? `not needed: ${d.skipped}` : `${d.analysed ?? 0} reviewed${d.reused ? `, ${d.reused} reused` : ""}`) },
  md_selection: { title: "Choosing what to simulate", actor: ["Muse Spark", "deciding which candidate deserves molecular dynamics", "think"],
    done: (d) => d.reason || `selected: ${(d.selected || []).map(fname).join(", ") || "none"}${d.chosen_by ? ` (chosen by ${PROVIDER_MODEL[d.chosen_by] || d.chosen_by})` : ""}` },
  molecular_dynamics: { title: "Lithium-ion diffusion: molecular dynamics at 600 K", actor: ["UMA", "molecular dynamics at 600 K", "compute"],
    done: (d) => `${Object.keys(d.verdicts || {}).length} simulated${(d.excluded || []).length ? ` · excluded for conduction: ${d.excluded.map(fname).join(", ")}` : ""}` },
  conductivity: { title: "Ionic conductivity at 300 K", actor: ["AutoLab", "Arrhenius fit 500–700 K and Nernst–Einstein relation", "compute"],
    done: (d) => `${d.computed ?? 0} structures · parents: ${Object.entries(d.parents || {}).map(([k, v]) => `${L.parents[k] || k} ${v} mS/cm`).join(", ")}` },
  ranking: { title: "Ranking by explicit rules", actor: ["AutoLab", "level against the parent at 300 K, then a stated convention", "plan"], done: null },
  novelty: { title: "Literature check", actor: ["Muse Spark", "searching the web; a known electrolyte is checked first as a control", "think"], done: null },
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
    cardHead(card, meta.title, d && d.iteration != null ? `round ${d.iteration}: this round's candidates` : "the whole pool of candidates", e);
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
          `<div class="md-anim"><i></i><i></i><i></i><i></i><i></i><i></i></div><p class="md-cap">lithium ions hopping at 600 K: the simulation follows every atom</p>`}</div></div>`);
    if (entry) mdScene(card, it.querySelector(".lab-3d"), entry);
    labLog(`Molecular dynamics launched: ${ids.map(fname).join(", ") || "candidates"} next to their parent crystals`);
    return 3800;
  }
  if (d.status === "start" || !d.status) return 900;
  const meta = STAGES[name];
  if (name === "ranking") {
    cardAdd(card, `<div class="podium">${(d.finalists || []).map((id, i) => `<div class="pod p${i + 1}"><span class="n">${i + 1}</span>
        <b>${tx(fname(id))}</b><span>${tx((d.levels || [])[i] ? `${d.levels[i]} with its parent at 300 K` : "")}</span></div>`).join("")}</div>
      ${(d.levels || []).length && new Set(d.levels).size === 1 ? `<p class="muted">Same level for the three: their order is a stated convention (lowest E<sub>hull</sub> per substitution, then activation energy, then window), not a significant difference.</p>` : ""}`);
    labLog(`Finalists: ${(d.finalists || []).map(fname).join(", ")}`, "good");
    return 4200;
  }
  if (name === "novelty") {
    cardAdd(card, `${d.control_ok ? `<span class="ok">control passed: LGPS found as known</span>` : `<span class="no">control not passed</span>`}
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
    cardAdd(card, `<div class="erow"><b>${tx(d.formula || fname(id))}</b>${voltBar(d.window)}
      <span class="${d.passivation === "non_passivating" ? "no" : "ok"}">${tx(d.passivation || "")}</span>
      <span class="muted">${d.window && d.window.stable ? `${fmt(d.window.v_low, 2)}–${fmt(d.window.v_high, 2)} V` : "zero width"}${d.interface_reaction_energy != null ? ` · LiFePO₄ ${fmt(d.interface_reaction_energy, 3)} eV/atom` : ""}</span></div>`, "row");
    if (d.excluded) labLog(`${d.formula}: reacts with lithium metal (${d.passivation}) — excluded`, "bad");
    return d.iteration != null ? 1500 : 650;
  }
  if (e.step === "candidate_analyses:done") {
    const card = stageCard("candidate_analyses", d, e);
    labActor(modelOf(d.provider), `reviewing ${d.formula || fname(id)}`, "think");
    cardAdd(card, `<div class="review"><b>${tx(d.formula || fname(id))}</b> <span class="chip">${tx(`MD priority: ${d.md_priority || "—"}`)}</span>
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
    labActor("pymatgen", "building charge-balanced crystal structures", "compute");
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
    labActor("Materials Project", "checking whether this composition is already known", "data");
    cardAdd(card, (d.known || []).length ? `<span class="no">already known:</span> ${tx(d.known.map((k) => k.material_id || k).join(", "))} — not recomputed`
      : d.error ? `<span class="no">database unreachable:</span> computed anyway` : `<span class="ok">new composition</span> — not in Materials Project`);
    return 1200;
  }
  if (e.step === "relax") {
    strip(card, "relax");
    labActor("UMA", `relaxing ${d.arrangements} arrangements: atoms and cell move to their lowest energy`, "compute");
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
    labActor("UMA + Materials Project", `convex hull against ${d.references} known phases, all relaxed with UMA`, "compute");
    cardAdd(card, gauge({ label: "energy above the convex hull", value: d.e_hull, min: Math.min(0, d.e_hull), max: Math.max(0.1, d.e_hull * 1.25), threshold: 0.05, better: "low", unit: "eV/atom" })
      + `<p class="muted">would decompose into ${tx((d.decomposition || []).map((x) => x.formula).join(" + "))} · per substitution <b>${fmt(d.e_hull_per_substitution)}</b> eV</p>`);
    return 2700;
  }
  if (e.step === "bandgap") {
    strip(card, "gap");
    labActor("GapModel", "predicting the electronic band gap", "compute");
    cardAdd(card, gauge({ label: "band gap (optB88)", value: d.gap_optb88, max: 6, threshold: 2, better: "high", unit: "eV", digits: 2 })
      + `<p class="muted">mBJ estimate <b>${fmt(d.gap_mbj, 2)}</b> eV${d.low_confidence ? " · low confidence" : ""}</p>`);
    return 2300;
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
    const team = [["Muse Spark", "proposes, decides, interprets failures, writes the report", "think"],
      ["Muse Spark Open", "reviews each candidate independently", "think"], ["Muse Glimmer", "summarizes in plain language", "think"],
      ["UMA", "relaxes crystals and runs molecular dynamics", "compute"], ["GapModel", "predicts band gaps", "compute"],
      ["Materials Project", "known phases and DFT references", "data"]];
    cardAdd(card, `<div class="plan-box"><div><span class="tag">parent crystals</span>${(d.parents || []).map((p) => `<span class="chip">${tx(p.formula)} · ${esc(p.id)}</span>`).join(" ")}</div>
      <div><span class="tag">filters</span>E<sub>hull</sub> ≤ ${th.EHULL_SYNTHESIZABLE ?? 0.05} eV/atom · band gap ≥ ${th.BANDGAP_MIN ?? 2} eV · Li diffusion at ${th.MD_SCREEN_TEMPERATURE_K ?? 600} K</div>
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

const STEP_ACTOR = { goal: ["Muse Spark", "reading the request", "think"], propose: ["Muse Spark", "reasoning about new substitutions", "think"],
  build: ["UMA", "relaxing crystal structures", "compute"], stability: ["UMA + Materials Project", "computing the convex hull", "compute"],
  bandgap: ["GapModel", "predicting band gaps", "compute"], learn: ["Muse Spark", "interpreting the results", "think"],
  electrodes: ["pymatgen", "phase diagrams against the electrodes", "compute"], review: ["Muse Spark Open", "reviewing each candidate", "think"],
  md_choice: ["Muse Spark", "choosing what to simulate", "think"], md: ["UMA", "molecular dynamics at 600 K on Modal H100", "compute"],
  conductivity: ["AutoLab", "Arrhenius extrapolation to 300 K", "compute"], ranking: ["AutoLab", "ranking the candidates", "plan"],
  literature: ["Muse Spark", "searching the literature", "think"], report: ["Muse Spark", "writing the final report", "think"] };

function labWorking() {
  const run = (S.view.steps || []).find((s) => s.state === "running");
  const [who, what, kind] = (run && STEP_ACTOR[run.key]) || ["AutoLab", "working", "compute"];
  labActor(who, what, kind);
  if (L.group === "working") return;
  const card = labCard("working");
  card.el.classList.add("banner", "working");
  card.el.innerHTML = `<div class="pulse"><i></i><i></i><i></i></div><p><b>${tx(run ? run.label : "Working")}</b></p>
    <p class="muted">${tx(who)} is computing now; the next result appears as soon as it is ready.</p>`;
}


/* ---------- start ---------- */

window.addEventListener("popstate", route);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (themeChoice() === "system") applyTheme("system"); });
applyTheme(themeChoice());
loadHistory().then(route);
setInterval(() => { if (S.history.some((c) => ACTIVE.has(c.status))) loadHistory(); }, 15000);
