const els = {
  score: document.getElementById("score"),
  clock: document.getElementById("clock"),
  status: document.getElementById("status"),
  playBtn: document.getElementById("playBtn"),
  refreshBtn: document.getElementById("refreshBtn"),
  speed: document.getElementById("speed"),
  homeTeam: document.getElementById("homeTeam"),
  awayTeam: document.getElementById("awayTeam"),
  lang: document.getElementById("lang"),
  persona: document.getElementById("persona"),
  teamFilter: document.getElementById("teamFilter"),
  homeName: document.querySelector(".home-name"),
  awayName: document.querySelector(".away-name"),
  homeNameLegend: document.getElementById("homeNameLegend"),
  awayNameLegend: document.getElementById("awayNameLegend"),
  ball: document.getElementById("ball"),
  pitchEvents: document.getElementById("pitchEvents"),
  players: document.getElementById("players"),
  trail: document.getElementById("trail"),
  arrows: document.getElementById("arrows"),
  goalFlash: document.getElementById("goalFlash"),
  goalPop: document.getElementById("goalPop"),
  halfHome: document.getElementById("halfHome"),
  halfAway: document.getElementById("halfAway"),
  possessionTag: document.getElementById("possessionTag"),
  haPoss: document.getElementById("haPoss"),
  awPoss: document.getElementById("awPoss"),
  posHome: document.getElementById("posHome"),
  haShots: document.getElementById("haShots"),
  awShots: document.getElementById("awShots"),
  haXg: document.getElementById("haXg"),
  awXg: document.getElementById("awXg"),
  haPass: document.getElementById("haPass"),
  awPass: document.getElementById("awPass"),
  haTilt: document.getElementById("haTilt"),
  awTilt: document.getElementById("awTilt"),
  momHome: document.getElementById("momHome"),
  momAway: document.getElementById("momAway"),
  patterns: document.getElementById("patterns"),
  commentary: document.getElementById("commentary"),
  insights: document.getElementById("insights"),
  insightCount: document.getElementById("insightCount"),
  highlights: document.getElementById("highlights"),
  hlCount: document.getElementById("hlCount"),
};

const LANG_LABELS = { en: "EN", es: "ES", fr: "FR", pt: "PT", ar: "AR", zu: "ZU" };
const state = {
  ws: null,
  playing: false,
  lang: "en",
  persona: "broadcast-hype",
  teamFilter: "all",
  home: "MUN",
  away: "MCI",
  homeColor: "#DA020E",
  awayColor: "#6CABDD",
  insightCount: 0,
  lastEventCount: 0,
  insights: [],
  highlights: [],
  matchDone: false,
  lastGoalId: null,
  trail: [],
};

const PERSONAS = {};

async function loadPersonas() {
  try {
    const res = await fetch("/api/personas");
    const data = await res.json();
    els.persona.innerHTML = "";
    data.personas.forEach((p) => {
      PERSONAS[p.id] = p;
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name;
      opt.title = p.description;
      els.persona.appendChild(opt);
    });
    els.persona.value = state.persona;
  } catch (e) { /* keep default */ }
}

async function loadTeams() {
  try {
    const res = await fetch("/api/teams");
    const data = await res.json();
    const fill = (sel, selected) => {
      sel.innerHTML = "";
      data.teams.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.textContent = t.name;
        opt.style.color = t.color;
        sel.appendChild(opt);
      });
      sel.value = selected;
    };
    fill(els.homeTeam, state.home);
    fill(els.awayTeam, state.away);
  } catch (e) { /* keep default */ }
}

const PITCH = { x0: 4, y0: 4, w: 112, h: 76 };
const mapX = (x) => PITCH.x0 + (x / 100) * PITCH.w;
const mapY = (y) => PITCH.y0 + (y / 100) * PITCH.h;

function setStatus(msg) { els.status.textContent = msg; }

function connect() {
  const speed = els.speed.value;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${location.host}/ws/live?speed=${speed}&persona=${state.persona}&home=${state.home}&away=${state.away}`;
  state.ws = new WebSocket(url);

  state.ws.onopen = () => setStatus("Connected — streaming synthetic match events…");
  state.ws.onclose = () => { state.playing = false; els.playBtn.textContent = "▶ Play live"; els.playBtn.classList.remove("playing"); };
  state.ws.onerror = () => setStatus("Connection error. Is the server running?");
  state.ws.onmessage = (msg) => {
    const frame = JSON.parse(msg.data);
    if (frame.type === "match_init") onInit(frame);
    else if (frame.type === "tick") onTick(frame.state);
    else if (frame.type === "insight") onInsight(frame.insight);
    else if (frame.type === "end") onEnd(frame);
    else if (frame.type === "status") setStatus(frame.message);
    else if (frame.type === "error") setStatus("Error: " + frame.message);
  };
}

function onInit(frame) {
  const { home, away } = frame.match;
  state.homeColor = home.color;
  state.awayColor = away.color;
  document.documentElement.style.setProperty("--home", home.color);
  document.documentElement.style.setProperty("--away", away.color);
  els.homeName.textContent = home.short;
  els.awayName.textContent = away.short;
  els.homeNameLegend.textContent = home.name;
  els.awayNameLegend.textContent = away.name;
  if (els.halfHome) els.halfHome.textContent = home.short;
  if (els.halfAway) els.halfAway.textContent = away.short;
  state.lastGoalId = null;
  clearTrail();
  setStatus(`Match: ${home.name} vs ${away.name} · ${frame.match.venue} · model: ${frame.llm}`);
}

const SVG_NS = "http://www.w3.org/2000/svg";
const playerEls = new Map();

function textColorFor(hex) {
  const c = (hex || "#333333").replace("#", "");
  const full = c.length === 3 ? c.split("").map((x) => x + x).join("") : c;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.6 ? "#0b1220" : "#ffffff";
}

function renderPlayers(players, ev) {
  if (!players || !players.length) return;
  const activeKey = ev && ev.player_id != null && ev.team_id ? `${ev.team_id}-${ev.player_id}` : null;
  players.forEach((p) => {
    const key = `${p.team_id}-${p.id}`;
    let el = playerEls.get(key);
    if (!el) {
      const color = p.team_id === "HOME" ? state.homeColor : state.awayColor;
      const g = document.createElementNS(SVG_NS, "g");
      g.setAttribute("class", "player");
      const circle = document.createElementNS(SVG_NS, "circle");
      circle.setAttribute("r", "2");
      circle.setAttribute("class", "player-body");
      circle.setAttribute("fill", color);
      const txt = document.createElementNS(SVG_NS, "text");
      txt.setAttribute("class", "player-num");
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("dominant-baseline", "central");
      txt.setAttribute("fill", textColorFor(color));
      txt.textContent = p.number;
      g.appendChild(circle);
      g.appendChild(txt);
      els.players.appendChild(g);
      playerEls.set(key, g);
      el = g;
    }
    el.style.transform = `translate(${mapX(p.x)} ${mapY(p.y)})`;
    el.classList.toggle("active", key === activeKey);
  });
}

function clearPlayers() {
  playerEls.clear();
  if (els.players) els.players.innerHTML = "";
}

function addTrailPoint(x, y) {
  state.trail.push([x, y]);
  while (state.trail.length > 16) state.trail.shift();
  if (!els.trail) return;
  els.trail.innerHTML = "";
  const n = state.trail.length;
  state.trail.forEach(([px, py], i) => {
    const t = (i + 1) / n;
    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("cx", mapX(px));
    dot.setAttribute("cy", mapY(py));
    dot.setAttribute("r", (0.5 + 1.9 * t).toFixed(2));
    dot.setAttribute("fill", "#ffffff");
    dot.setAttribute("opacity", (0.05 + 0.3 * t).toFixed(2));
    els.trail.appendChild(dot);
  });
}

function clearTrail() {
  state.trail = [];
  if (els.trail) els.trail.innerHTML = "";
}

const ARROW_TYPES = ["pass", "carry", "shot", "goal", "save", "corner"];

function addActionArrow(ev) {
  if (!els.arrows || !ev || !ARROW_TYPES.includes(ev.type)) return;
  const ex = ev.end_x != null ? ev.end_x : ev.x;
  const ey = ev.end_y != null ? ev.end_y : ev.y;
  const x1 = mapX(ev.x);
  const y1 = mapY(ev.y);
  const x2 = mapX(ex);
  const y2 = mapY(ey);
  const len = Math.hypot(x2 - x1, y2 - y1);
  if (len < 2) return;
  const color = ev.team_id === "HOME" ? state.homeColor : state.awayColor;
  const line = document.createElementNS(SVG_NS, "line");
  line.setAttribute("x1", x1.toFixed(1));
  line.setAttribute("y1", y1.toFixed(1));
  line.setAttribute("x2", x2.toFixed(1));
  line.setAttribute("y2", y2.toFixed(1));
  line.setAttribute("stroke", color);
  line.setAttribute("stroke-width", (ev.type === "goal" ? 1.1 : 0.7).toFixed(2));
  line.setAttribute("marker-end", ev.team_id === "HOME" ? "url(#arrowHome)" : "url(#arrowAway)");
  line.setAttribute("class", "action-arrow");
  els.arrows.appendChild(line);
  setTimeout(() => { line.style.opacity = "0"; }, 380);
  setTimeout(() => line.remove(), 1500);
  while (els.arrows.childElementCount > 40) els.arrows.removeChild(els.arrows.firstChild);
}

function clearArrows() {
  if (els.arrows) els.arrows.innerHTML = "";
}

function celebrateGoal(ev) {
  if (!ev || ev.type !== "goal" || ev.id === state.lastGoalId) return;
  state.lastGoalId = ev.id;
  const teamName = ev.team_id === "HOME" ? els.homeNameLegend.textContent : els.awayNameLegend.textContent;
  if (els.goalPop) {
    els.goalPop.textContent = `GOAL  ${ev.player_name || "Unknown"} · ${teamName}`;
    els.goalPop.classList.add("show");
    setTimeout(() => els.goalPop.classList.remove("show"), 2600);
  }
  if (els.goalFlash) {
    els.goalFlash.classList.remove("flash");
    void els.goalFlash.offsetWidth;
    els.goalFlash.classList.add("flash");
    setTimeout(() => els.goalFlash.classList.remove("flash"), 800);
  }
  if (els.score) {
    els.score.classList.remove("bump");
    void els.score.offsetWidth;
    els.score.classList.add("bump");
    setTimeout(() => els.score.classList.remove("bump"), 700);
  }
}

function onTick(s) {
  els.clock.textContent = `${s.minute}'`;
  els.score.textContent = `${s.home.goals} – ${s.away.goals}`;
  els.haPoss.textContent = `${s.home.possession}%`;
  els.awPoss.textContent = `${s.away.possession}%`;
  els.posHome.style.width = `${s.home.possession}%`;
  els.haShots.textContent = s.home.shots;
  els.awShots.textContent = s.away.shots;
  els.haXg.textContent = s.home.xg.toFixed(2);
  els.awXg.textContent = s.away.xg.toFixed(2);
  els.haPass.textContent = `${s.home.pass_accuracy}%`;
  els.awPass.textContent = `${s.away.pass_accuracy}%`;
  els.haTilt.textContent = `${s.home.field_tilt}%`;
  els.awTilt.textContent = `${s.away.field_tilt}%`;
  els.possessionTag.textContent = s.possession_team === "HOME" ? "home possession" : "away possession";

  const [bx, by] = s.ball;
  els.ball.setAttribute("cx", mapX(bx));
  els.ball.setAttribute("cy", mapY(by));
  addTrailPoint(bx, by);

  const ev = s.last_event;
  renderPlayers(s.players, ev);
  if (ev) addPitchMarker(ev);
  if (ev) addActionArrow(ev);
  if (ev) celebrateGoal(ev);
  if (ev && ev.description && ev.type !== "pass") addCommentary(ev);

  drawMomentum(s.momentum);
  drawPatterns(s.patterns);
}

function addPitchMarker(ev) {
  const keyTypes = ["goal", "shot", "save", "corner"];
  if (!keyTypes.includes(ev.type)) return;
  const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  const x = mapX(ev.end_x != null ? ev.end_x : ev.x);
  const y = mapY(ev.end_y != null ? ev.end_y : ev.y);
  dot.setAttribute("cx", x);
  dot.setAttribute("cy", y);
  dot.setAttribute("r", ev.type === "goal" ? 2.4 : 1.6);
  dot.setAttribute("class", `ev-dot ${ev.type === "goal" ? "ev-goal" : "ev-shot"}`);
  els.pitchEvents.appendChild(dot);
  while (els.pitchEvents.childElementCount > 60) els.pitchEvents.removeChild(els.pitchEvents.firstChild);
}

function addCommentary(ev) {
  const line = document.createElement("div");
  const isKey = ev.tags.includes("goal") || ev.tags.includes("key_moment");
  line.className = "line" + (isKey ? " key" : "");
  line.innerHTML = `<span class="min">${ev.minute}'</span>${ev.description}`;
  els.commentary.prepend(line);
  while (els.commentary.childElementCount > 200) els.commentary.removeChild(els.commentary.lastChild);
}

function drawMomentum(points) {
  if (!points || points.length < 2) return;
  const max = Math.max(5, ...points.map((p) => Math.max(p.home, p.away)));
  const X = (m) => (m / 90) * 600;
  const yHome = (v) => 90 - (v / max) * 82;
  const yAway = (v) => 90 + (v / max) * 82;
  let dh = "";
  let da = "";
  points.forEach((p, i) => {
    dh += `${i === 0 ? "M" : "L"}${X(p.minute).toFixed(1)} ${yHome(p.home).toFixed(1)} `;
    da += `${i === 0 ? "M" : "L"}${X(p.minute).toFixed(1)} ${yAway(p.away).toFixed(1)} `;
  });
  els.momHome.setAttribute("d", dh);
  els.momAway.setAttribute("d", da);
}

function drawPatterns(patterns) {
  if (!patterns || !patterns.length) { els.patterns.innerHTML = '<span class="muted">None detected yet.</span>'; return; }
  els.patterns.innerHTML = "";
  patterns.forEach((p) => {
    const chip = document.createElement("div");
    chip.className = "pattern-chip " + (p.team_id === "HOME" ? "home" : "away");
    chip.innerHTML = `<span>${p.label}</span>
      <span class="bar"><i style="width:${Math.round(p.strength * 100)}%"></i></span>
      <span class="pct">${Math.round(p.strength * 100)}%</span>`;
    els.patterns.appendChild(chip);
  });
}

function visibleInsights() {
  return state.teamFilter === "all"
    ? state.insights
    : state.insights.filter((i) => i.team_id === state.teamFilter);
}

function renderInsightsList() {
  els.insights.innerHTML = "";
  const visible = visibleInsights();
  if (!visible.length) {
    els.insights.innerHTML = '<div class="empty">No insights for this filter yet.</div>';
  } else {
    visible.slice().reverse().forEach((insight) => els.insights.appendChild(buildCard(insight)));
  }
  els.insightCount.textContent = visible.length;
}

function onInsight(insight) {
  state.insights.push(insight);
  state.insightCount = visibleInsights().length;
  if (state.teamFilter === "all" || insight.team_id === state.teamFilter) {
    if (els.insights.querySelector(".empty")) els.insights.innerHTML = "";
    els.insights.prepend(buildCard(insight));
    els.insightCount.textContent = visibleInsights().length;
    while (els.insights.childElementCount > 40) els.insights.removeChild(els.insights.lastChild);
  }
}

function confClass(c) { return c >= 0.75 ? "high" : c >= 0.55 ? "mid" : "low"; }

function buildCard(insight) {
  const card = document.createElement("div");
  card.className = "card " + (insight.team_id === "HOME" ? "home" : "away");
  const langs = Object.keys(insight.translations || {});
  card.dataset.insight = JSON.stringify(insight);
  card.dataset.lang = state.lang;

  const factors = insight.factors.map((f) => `
    <div class="factor">
      <span class="fname" title="${escapeAttr(f.name)}">${f.name}</span>
      <span class="fbar"><i style="width:${Math.round(f.weight * 100)}%"></i></span>
      <span class="fw">${Math.round(f.weight * 100)}%</span>
    </div>
    <div class="card-sub" style="margin:-2px 0 6px 0">${f.detail}</div>`).join("");

  const evidence = insight.evidence.map((e) => `
    <div class="ev-item"><b>${e.label}:</b> ${e.detail}
      ${e.event_ids && e.event_ids.length ? `<div class="ev-ids">evidence refs: ${e.event_ids.join(", ")}</div>` : ""}
    </div>`).join("");

  const chips = langs.map((l) => `<span class="langchip" data-lang="${l}">${LANG_LABELS[l] || l}</span>`).join("");

  card.innerHTML = `
    <div class="card-head">
      <div class="card-title">${insight.title}</div>
      <div class="card-meta">
        <span class="kind">${insight.kind.replace("_", " ")}</span>
        <span class="conf ${confClass(insight.confidence)}">${Math.round(insight.confidence * 100)}%</span>
      </div>
    </div>
    <div class="card-narrative card-claim"></div>
    <div class="section-label">Why this happened — weighted factors</div>
    ${factors}
    <div class="section-label">Evidence</div>
    <div class="evidence">${evidence}</div>
    ${insight.counterfactual ? `<div class="counterfactual"><b>What-if:</b> ${insight.counterfactual.replace(/^Counterfactual:\s*/, "")}</div>` : ""}
    <div class="langchips">${chips}</div>`;

  card.querySelectorAll(".langchip").forEach((chip) => {
    chip.addEventListener("click", () => {
      card.dataset.lang = chip.dataset.lang;
      renderCardText(card);
    });
  });
  setTimeout(() => renderCardText(card), 0);
  return card;
}

function renderCardText(card) {
  const insight = JSON.parse(card.dataset.insight);
  const lang = card.dataset.lang || "en";
  const text = (insight.translations && insight.translations[lang]) || insight.narrative || insight.claim;
  card.querySelector(".card-narrative").textContent = text;
  card.querySelectorAll(".langchip").forEach((c) =>
    c.classList.toggle("active", c.dataset.lang === lang));
}

function escapeAttr(s) { return String(s).replace(/"/g, "&quot;"); }

function renderHighlightsFiltered() {
  const list = state.teamFilter === "all"
    ? state.highlights
    : state.highlights.filter((h) => h.team_id === state.teamFilter);
  renderHighlights(list);
}

function onEnd(frame) {
  state.playing = false;
  state.matchDone = true;
  els.playBtn.textContent = "▶ Replay";
  els.playBtn.classList.remove("playing");
  const score = frame.summary ? frame.summary.score : "";
  setStatus(`Full-time ${score}. ${state.insightCount} explainable insights generated.`);
  if (frame.summary && frame.summary.highlights) {
    state.highlights = frame.summary.highlights;
    renderHighlightsFiltered();
  }
  loadRecap();
}

async function loadRecap() {
  try {
    const res = await fetch(`/api/recap?persona=${state.persona}&home=${state.home}&away=${state.away}`);
    const d = await res.json();
    if (!d.recap) return;
    document.querySelectorAll(".recap-card").forEach((n) => n.remove());
    const card = document.createElement("div");
    card.className = "card recap-card";
    card.style.borderLeft = "4px solid var(--accent)";
    card.innerHTML = `<div class="card-head"><div class="card-title">Full-time recap</div>
      <div class="card-meta"><span class="kind">${state.persona}</span></div></div>
      <div class="card-claim">${d.recap}</div>`;
    els.insights.prepend(card);
  } catch (e) { /* ignore */ }
}

function renderHighlights(list) {
  els.highlights.innerHTML = "";
  els.hlCount.textContent = list.length;
  list.forEach((h, i) => {
    const card = document.createElement("div");
    card.className = "hl-card " + (h.team_id === "HOME" ? "home" : "away");
    card.innerHTML = `
      <div class="hl-top"><span class="hl-rank">#${i + 1} · ${h.minute}'</span><span class="hl-score">${Math.round(h.excitement)}</span></div>
      <div class="hl-title">${h.title}</div>
      <div class="hl-desc">${h.description || ""}</div>
      <div class="hl-reason">${h.reason} · refs ${h.event_ids.join(",")}</div>`;
    els.highlights.appendChild(card);
  });
}

function resetGame() {
  if (state.ws) { try { state.ws.close(); } catch (e) {} state.ws = null; }
  state.playing = false;
  state.matchDone = false;
  state.insights = [];
  state.highlights = [];
  state.insightCount = 0;
  state.lastGoalId = null;
  els.insightCount.textContent = "0";
  els.hlCount.textContent = "0";
  els.score.textContent = "0 – 0";
  els.clock.textContent = "0'";
  els.insights.innerHTML = '<div class="empty">Insights will appear here — each with evidence, weighted factors, a confidence score and a counterfactual.</div>';
  els.commentary.innerHTML = "";
  els.pitchEvents.innerHTML = "";
  els.patterns.innerHTML = '<span class="muted">None detected yet.</span>';
  if (els.momHome) els.momHome.setAttribute("d", "");
  if (els.momAway) els.momAway.setAttribute("d", "");
  els.highlights.innerHTML = '<span class="muted">Ranked key moments appear at full-time.</span>';
  clearPlayers();
  clearTrail();
  clearArrows();
  els.playBtn.textContent = "▶ Play live";
  els.playBtn.classList.remove("playing");

  // return to defaults
  state.home = "MUN";
  state.away = "MCI";
  state.homeColor = "#3b82f6";
  state.awayColor = "#ef4444";
  state.persona = "broadcast-hype";

  document.documentElement.style.setProperty("--home", "#3b82f6");
  document.documentElement.style.setProperty("--away", "#ef4444");
  els.homeName.textContent = "Home";
  els.awayName.textContent = "Away";
  els.homeNameLegend.textContent = "Home";
  els.awayNameLegend.textContent = "Away";
  if (els.halfHome) els.halfHome.textContent = "HOME";
  if (els.halfAway) els.halfAway.textContent = "AWAY";
  state.lang = "en";
  state.teamFilter = "all";
  try { els.homeTeam.value = state.home; } catch (e) {}
  try { els.awayTeam.value = state.away; } catch (e) {}
  try { els.persona.value = state.persona; } catch (e) {}
  try { els.lang.value = state.lang; } catch (e) {}
  try { els.teamFilter.value = state.teamFilter; } catch (e) {}
  try { els.speed.value = "60"; } catch (e) {}
  clearPlayers();
  setStatus("Match cleared. Press “Play live” to start a new synthetic match feed.");
}

els.refreshBtn.addEventListener("click", resetGame);

els.playBtn.addEventListener("click", () => {
  if (state.playing) {
    if (state.ws) state.ws.close();
    state.playing = false;
    els.playBtn.textContent = "▶ Play live";
    els.playBtn.classList.remove("playing");
    return;
  }
  state.insightCount = 0;
  state.insights = [];
  state.highlights = [];
  state.matchDone = false;
  els.insightCount.textContent = "0";
  els.insights.innerHTML = '<div class="empty">Waiting for key moments…</div>';
  els.commentary.innerHTML = "";
  els.pitchEvents.innerHTML = "";
  clearPlayers();
  clearTrail();
  clearArrows();
  state.lastGoalId = null;
  els.highlights.innerHTML = '<span class="muted">Ranked key moments appear at full-time.</span>';
  els.hlCount.textContent = "0";
  state.playing = true;
  els.playBtn.textContent = "■ Stop";
  els.playBtn.classList.add("playing");
  connect();
});

els.speed.addEventListener("change", () => {
  if (state.playing && state.ws) { state.ws.close(); connect(); }
});

els.lang.addEventListener("change", () => {
  state.lang = els.lang.value;
  document.querySelectorAll(".card").forEach((c) => { c.dataset.lang = state.lang; renderCardText(c); });
});

els.teamFilter.addEventListener("change", () => {
  state.teamFilter = els.teamFilter.value;
  renderInsightsList();
  if (state.matchDone) renderHighlightsFiltered();
});

els.persona.addEventListener("change", () => {
  state.persona = els.persona.value;
  const p = PERSONAS[state.persona];
  if (p) {
    els.lang.value = p.language;
    state.lang = p.language;
    document.querySelectorAll(".card").forEach((c) => { c.dataset.lang = p.language; renderCardText(c); });
  }
  if (state.matchDone) { loadRecap(); refreshHighlights(); }
});

async function refreshHighlights() {
  try {
    const res = await fetch(`/api/highlights?persona=${state.persona}&home=${state.home}&away=${state.away}`);
    const d = await res.json();
    renderHighlights(d.highlights);
  } catch (e) { /* ignore */ }
}

function onTeamsChanged() {
  state.home = els.homeTeam.value;
  state.away = els.awayTeam.value;
  clearPlayers();
  if (state.playing && state.ws) { state.ws.close(); connect(); }
  else if (state.matchDone) { loadRecap(); refreshHighlights(); }
}

els.homeTeam.addEventListener("change", onTeamsChanged);
els.awayTeam.addEventListener("change", onTeamsChanged);

loadPersonas();
loadTeams();
