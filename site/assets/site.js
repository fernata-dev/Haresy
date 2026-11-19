// Bawwab website behaviour. Text from data is inserted with textContent only; icons are constant
// SVG strings parsed with DOMParser. No network calls, no tracking.
import DEMO from "./demo-data.js";

const lang = document.documentElement.lang === "ar" ? "ar" : "en";
const T = DEMO.text[lang];
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
document.documentElement.classList.add("js");

function h(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}
const ICON = {
  shut: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  open: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 7.5-2"/>',
};
function icon(name) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[name]}</svg>`;
  return document.importNode(new DOMParser().parseFromString(svg, "image/svg+xml").documentElement, true);
}
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg; el.classList.add("show");
  clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("show"), 2200);
}

// ------------------------------------------------------------ nav
const nav = document.getElementById("nav");
const onScroll = () => nav.classList.toggle("solid", window.scrollY > 24);
window.addEventListener("scroll", onScroll, {passive: true});
onScroll();

// ------------------------------------------------------------ copy buttons
for (const btn of document.querySelectorAll("[data-copy-target]")) {
  btn.addEventListener("click", async () => {
    const holder = btn.closest("[data-copy]") || btn.parentElement.querySelector("[data-copy]");
    const text = holder ? holder.getAttribute("data-copy") : "";
    try { await navigator.clipboard.writeText(text); }
    catch (e) { const ta = h("textarea", {}); ta.value = text; document.body.append(ta); ta.select(); document.execCommand && document.execCommand("copy"); ta.remove(); }
    btn.textContent = btn.dataset.done; btn.classList.add("done");
    toast(btn.dataset.done);
    setTimeout(() => { btn.textContent = btn.dataset.label; btn.classList.remove("done"); }, 1800);
  });
}

// ------------------------------------------------------------ OS tabs (arrow keys move between tabs)
const osTabs = [...document.querySelectorAll(".os-tabs [role=tab]")];
function selectOs(tab) {
  for (const t of osTabs) {
    const on = t === tab;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
    document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
  }
}
osTabs.forEach((t, i) => {
  t.addEventListener("click", () => selectOs(t));
  t.addEventListener("keydown", (e) => {
    const step = {ArrowRight: 1, ArrowLeft: -1}[e.key];
    if (!step) return;
    const dir = document.documentElement.dir === "rtl" ? -step : step;
    const next = osTabs[(i + dir + osTabs.length) % osTabs.length];
    selectOs(next); next.focus(); e.preventDefault();
  });
});
const ua = navigator.userAgent;
const guess = /Windows/.test(ua) ? "win" : /Mac OS X/.test(ua) && !/iPhone|iPad/.test(ua) ? "mac" : /Ubuntu|Debian/.test(ua) ? "debian" : null;
if (guess) selectOs(document.getElementById("tab-" + guess));

// ------------------------------------------------------------ demo
const list = document.getElementById("scn-list");
const stage = document.getElementById("demo-stage");
const SC = DEMO.data.scenarios;
let cur = 0, variant = 0;

function renderStage() {
  const sc = SC[cur], v = sc.variants[Math.min(variant, sc.variants.length - 1)], d = v.decision;
  stage.textContent = "";
  stage.setAttribute("aria-labelledby", "scn-" + sc.id);
  const vt = h("div", {class: "vtabs", role: "group", "aria-label": T.demo_lang},
    sc.variants.map((x, i) => h("button", {type: "button", "aria-pressed": String(i === variant), onclick: () => { variant = i; renderStage(); }, text: T["v_" + x.code]})));
  stage.append(h("div", {class: "stage-top"},
    h("div", {}, h("span", {class: "label", text: T.demo_lang + ": "}), vt),
    h("span", {class: "modechip", text: `${T.demo_mode}: ${T["mode_" + sc.mode]}`})));
  const s1 = h("div", {class: "st"}, h("h3", {text: T.demo_step1}),
    h("span", {class: "src-k", text: T["src_" + sc.source]}),
    h("div", {class: "said", dir: "auto", text: v.text}),
    sc.source === "user" ? null : h("div", {class: "scanner"}, h("span", {text: T.demo_scanner + ":"}),
      h("span", {class: "pill " + (v.d2.flagged ? "ok" : "no"), text: v.d2.flagged ? T.demo_flagged : T.demo_missed}),
      h("span", {class: "pill mute ltr", text: `D2: ${v.d2.score}`})));
  const call = JSON.stringify({tool: sc.call.tool, args: sc.call.args}, null, 2);
  const s2 = h("div", {class: "st"}, h("h3", {text: T.demo_step2}), h("pre", {text: call}));
  const ok = d.allowed;
  const verdict = h("div", {class: "verdict " + (ok ? "ok" : "no")},
    h("div", {class: "door"}, icon(ok ? "open" : "shut"), h("span", {text: ok ? T.dec_allow : T.dec_block})),
    h("dl", {},
      h("dt", {text: T.demo_rule}), h("dd", {}, h("span", {text: T["rule_" + d.rule] || d.rule}), d.rule ? h("div", {}, h("code", {class: "ltr", text: d.rule})) : null),
      d.hosts.length ? [h("dt", {text: T.demo_hosts}), h("dd", {}, h("code", {class: "ltr", text: d.hosts.join(", ")}))] : null,
      d.detail ? [h("dt", {text: T.demo_detail}), h("dd", {}, h("code", {class: "ltr", text: d.detail}))] : null));
  const s3 = h("div", {class: "st"}, h("h3", {text: T.demo_step3}), verdict,
    sc.also ? h("p", {class: "also"}, T.demo_also + " ", h("code", {class: "ltr", text: `${sc.also.tool} ${sc.also.args.url || ""}`}), " → ",
      h("b", {text: sc.also.decision.allowed ? T.dec_allow : T.dec_block})) : null);
  stage.append(h("div", {class: "stage-flow"}, s1, s2, s3), h("p", {class: "stage-note", text: T.demo_scanner_note}));
}

function renderList() {
  list.textContent = "";
  SC.forEach((sc, i) => {
    const allowed = sc.variants[0].decision.allowed;
    list.append(h("button", {class: "scn", type: "button", role: "tab", id: "scn-" + sc.id, "aria-selected": String(i === cur),
      "aria-controls": "demo-stage", tabindex: i === cur ? "0" : "-1",
      onclick: () => { cur = i; variant = 0; renderList(); renderStage(); },
      onkeydown: (e) => {
        const flip = document.documentElement.dir === "rtl" ? -1 : 1;     // in RTL, "next" is to the left
        const step = {ArrowDown: 1, ArrowUp: -1, ArrowRight: flip, ArrowLeft: -flip}[e.key];
        if (!step) return;
        e.preventDefault();
        cur = (i + step + SC.length) % SC.length; variant = 0; renderList(); renderStage();
        document.getElementById("scn-" + SC[cur].id).focus();
      }}, h("i", {class: allowed ? "ok" : ""}), T["scn_" + sc.id]));
  });
}
if (list && stage) { renderList(); renderStage(); }

// ------------------------------------------------------------ hero ledger (decorative; the demo above is the accessible version)
const ledger = document.getElementById("ledger");
if (ledger && !reduce) {
  const lines = [];
  for (const sc of SC) for (const v of sc.variants) {
    const d = v.decision, target = d.hosts.join(", ") || Object.values(sc.call.args)[0];
    lines.push([d.allowed, `${sc.call.tool} → ${target} · ${d.rule || "ok"} [${v.code}]`]);
  }
  let k = 7 % lines.length;
  setInterval(() => {
    if (document.hidden) return;
    const [ok, txt] = lines[k++ % lines.length];
    ledger.append(h("p", {class: ok ? "ok" : "no"}, h("b", {text: ok ? "ALLOW" : "BLOCK"}), " " + txt));
    while (ledger.children.length > 7) ledger.firstElementChild.remove();
  }, 2400);
}

// ------------------------------------------------------------ reveal on scroll
if (!reduce && "IntersectionObserver" in window) {
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), {rootMargin: "0px 0px -8% 0px"});
  for (const el of document.querySelectorAll(".sec .wrap > *, .strip .wrap > *, .final-in > *")) { el.classList.add("rv"); io.observe(el); }
}
