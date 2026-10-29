/* AutoLab web interface (interface.md): a conversation-first research assistant.
   Everything shown comes from the AutoLab service: steps from real events, numbers from stored results. No model or
   provider names, no costs, no "replay" mode are shown. */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const ACTIVE = new Set(["queued", "running", "stopping"]);
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
      <span class="status-dot ${st}" title="${esc(c.status)}"></span><span class="t">${esc(c.title)}</span>
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

const EXAMPLES = [
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
  ex.innerHTML = EXAMPLES.map((t) => `<button type="button">${esc(t)}</button>`).join("");
  ex.onclick = (e) => { const b = e.target.closest("button"); if (b) { $("prompt").value = b.textContent; autosize(); $("prompt").focus(); } };
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
  renderThread();
  setComposer(composerMode());
  scrollBottom(true);
  if (ACTIVE.has(v.conversation.status)) startPolling();
}

function refreshCrumb() {
  const c = S.history.find((x) => x.id === S.id);
  $("crumb").textContent = c ? c.title : S.view?.conversation.title || "";
  document.title = `${$("crumb").textContent || "AutoLab"} · AutoLab`;
}

async function fetchProgress(all = false) {
  const p = await api(`/conversations/${S.id}/progress?after=${all ? 0 : S.next}`);
  if (all) S.events = p.events; else S.events.push(...p.events);
  S.next = p.next;
  S.view.steps = p.steps;
  return p;
}

function startPolling() {
  clearInterval(S.timer);
  const id = S.id;
  S.timer = setInterval(async () => {
    if (S.id !== id) return clearInterval(S.timer);
    try {
      const before = S.next;
      const p = await fetchProgress();
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
        renderThread();
        setComposer(composerMode());
        scrollBottom();
      } else if (S.next !== before) renderResearch();
    } catch { /* a missed poll is retried at the next tick */ }
  }, POLL_MS);
}

function scrollBottom(instant = false) {
  const v = $("view");
  requestAnimationFrame(() => v.scrollTo({ top: v.scrollHeight, behavior: instant ? "auto" : "smooth" }));
}

/* ---------- thread rendering ---------- */

const userMsg = (t) => `<div class="msg user"><div class="bubble">${esc(t)}</div></div>`;
const aiBlock = (html, cls = "") => `<div class="msg ai ${cls}"><div class="avatar">${AI_ICON}</div><div class="body">${html}</div></div>`;

function md(text) {
  const html = window.marked ? window.marked.parse(text || "", { gfm: true }) : `<p>${esc(text)}</p>`;
  return window.DOMPurify ? window.DOMPurify.sanitize(html) : html;
}

function renderThread() {
  const v = S.view;
  if (!v) return;
  const parts = [];
  let researchPlaced = false;
  const hasResearch = v.steps && v.steps.length;
  for (const m of v.messages) {
    if (m.role === "user") { parts.push(userMsg(m.content)); continue; }
    if (m.kind === "scope") {
      parts.push(aiBlock(`<div class="prose">${md(m.content)}</div>`));
      if (hasResearch && !researchPlaced) { parts.push(aiBlock(`<div id="research"></div>`)); researchPlaced = true; }
    } else if (m.kind === "notice") {
      const newChat = m.data && m.data.action === "new_chat";
      parts.push(aiBlock(`<div class="notice${newChat ? " warn" : ""}">${esc(m.content)}${newChat
        ? `<div class="actions"><button class="primary-btn" type="button" data-newchat="${m.id}">New chat</button></div>` : ""}</div>`));
    } else if (m.kind === "summary") {
      parts.push(aiBlock(`<div class="prose"><p>${esc(m.content)}</p></div>`));
    } else if (m.kind === "report") {
      parts.push(aiBlock(reportBlock(m)));
    } else {
      parts.push(aiBlock(`<div class="prose">${md(m.content)}</div>`));
    }
  }
  if (hasResearch && !researchPlaced) parts.push(aiBlock(`<div id="research"></div>`));
  $("view").innerHTML = `<div class="thread">${parts.join("")}</div>`;
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
      <span class="badge ${ACTIVE.has(st) ? (st === "stopping" ? "stopping" : "running") : st}">${esc(badge)}</span></div>
    <div class="tabs" role="tablist">${tabs.map(([k, l, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${S.tab === k}">${l}${n ? `<span class="count">${n}</span>` : ""}</button>`).join("")}</div>
    <div class="tab-panel" id="tab-panel"></div></section>`;
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
  const end = ACTIVE.has(c.status) ? Date.now() : Date.parse(c.updated_at);
  const s = Math.max(0, Math.round((end - Date.parse(c.created_at)) / 1000));
  return s < 60 ? `${s} s` : s < 3600 ? `${Math.floor(s / 60)} min ${s % 60 ? `${s % 60} s` : ""}` : `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`;
}

function stepsHTML(steps) {
  if (!steps.length) return `<p class="empty">The research has not started yet.</p>`;
  return `<ol class="steps">${steps.map((s) => `<li class="step ${s.state}">
      <span class="ic">${s.state === "done" ? CHECK : s.state === "failed" ? CROSS : s.state === "interrupted" ? PAUSE : ""}</span>
      <div><div class="lbl"><span class="name">${esc(s.label)}</span><span class="state">${esc(stateLabel(s.state))}</span></div>
        ${s.detail ? `<div class="detail">${esc(s.detail)}</div>` : ""}
        <details><summary>Why this step</summary><p>${esc(s.why)}</p></details></div></li>`).join("")}</ol>`;
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
      <td class="formula">${esc(c.formula || c.id)}</td><td class="num">${fmt(c.e_hull)}</td><td class="num">${fmt(c.gap, 2)}</td>
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
  const sub = (s) => `${esc(s.remove)} → ${esc(s.add)} ×${esc(s.count)}${s.li_vacancies ? `, −${s.li_vacancies} Li` : ""}`;
  return `<div class="notes">${notes.map((n) => {
    if (n.kind === "proposal") return `<div class="note"><h4>Hypothesis</h4><p>${esc(n.data.hypothesis)}</p>
      <ul>${(n.data.proposals || []).map((p) => `<li><span class="formula">${sub(p.substitution || {})}</span> — ${esc(p.rationale)}</li>`).join("")}</ul></div>`;
    if (n.kind === "analysis") return `<div class="note"><h4>Interpretation</h4><ul>${(n.data.lessons || []).map((l) => `<li>${esc(l)}</li>`).join("")}</ul>
      ${n.data.next_direction ? `<p><b>Next:</b> ${esc(n.data.next_direction)}</p>` : ""}</div>`;
    if (n.kind === "md") return `<div class="note"><h4>Why these candidates are simulated</h4><p>${esc(n.data.rationale)}</p></div>`;
    return `<div class="note"><h4>Summary</h4><p>${esc(n.data.text)}</p></div>`;
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
    s += `<text class="lbl" x="${L - 8}" y="${y + 11}" text-anchor="end">${esc(r.label)}</text>`;
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
    s += `<text class="lbl" x="${L - 8}" y="${y + 4}" text-anchor="end">${esc(r.formula || r.id)}</text>`;
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
  const opts = S.index.structures.map((s) => `<option value="${esc(s.id)}">${esc(s.formula)}</option>`).join("");
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
  $("viewer-title").textContent = entry.formula;
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
    <div class="viz-controls"><label>Material <select id="md-pick">${ids.map((id) => `<option value="${esc(id)}">${esc(cands.find((e) => e.id === id).formula)}</option>`).join("")}</select></label>
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
    $("md-a-cap").textContent = `${md.a.formula} (candidate)`;
    $("md-b-cap").textContent = md.b ? `${md.b.formula} (parent crystal)` : "";
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
    $("md-time").innerHTML = `<span>t = <b>${t.toFixed(1)} ps</b></span><span>${esc(md.a.formula)}: <b>${hop(da)} / ${md.a.frames[0].length}</b> Li hopped</span>` +
      (db ? `<span>${esc(md.b.formula)}: <b>${hop(db)} / ${md.b.frames[0].length}</b> Li hopped</span>` : "");
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
  s += series.map((g, i) => `<text x="${L + 10 + (i % 3) * 190}" y="${T + 12 + Math.floor(i / 3) * 13}" style="fill:${g.color}">— ${esc(g.label)}</text>`).join("");
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
  root.innerHTML = `<h1>${esc(c.title)}</h1><p class="meta">AutoLab research report · ${esc(new Date(c.updated_at).toLocaleString())}<br>Goal: ${esc(c.goal)}</p>
    ${img}${rep.querySelector(".prose").innerHTML}`;
  document.body.classList.add("printing");
  const done = () => { document.body.classList.remove("printing"); root.innerHTML = ""; window.removeEventListener("afterprint", done); };
  window.addEventListener("afterprint", done);
  setTimeout(() => window.print(), 60);
}

/* ---------- start ---------- */

window.addEventListener("popstate", route);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (themeChoice() === "system") applyTheme("system"); });
applyTheme(themeChoice());
loadHistory().then(route);
setInterval(() => { if (S.history.some((c) => ACTIVE.has(c.status))) loadHistory(); }, 15000);
