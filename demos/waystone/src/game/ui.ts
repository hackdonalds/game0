// DOM HUD in #ui: race select, bars, objective tracker, prompts, dialogue, boss bar, marker, touch buttons, end card.
import type { People } from "../contracts";
import { PEOPLES, type PeopleDef } from "./data";
import type { Input } from "./input";

const CSS = `
#ui { position: fixed; inset: 0; pointer-events: none; font: 500 15px/1.35 system-ui, -apple-system, "Segoe UI", sans-serif; color: #f6efdc;
  --gold: #e9c46a; --panel: rgba(18, 22, 34, .72); --line: rgba(255,255,255,.14); -webkit-tap-highlight-color: transparent; }
#ui * { box-sizing: border-box; }
#ui button { font: inherit; color: inherit; pointer-events: auto; cursor: pointer; }
.ws-hud { position: absolute; inset: 0; padding: max(12px, env(safe-area-inset-top)) max(12px, env(safe-area-inset-right)) max(12px, env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left)); transition: opacity .4s; }
#ui [hidden] { display: none !important; }
.ws-top { display: flex; gap: 10px; align-items: flex-start; justify-content: space-between; }
.ws-left { display: grid; gap: 8px; width: min(300px, 62vw); }
.ws-panel { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 8px 10px; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); }
.ws-who { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; opacity: .8; margin-bottom: 4px; display: flex; justify-content: space-between; }
.ws-bar { height: 9px; border-radius: 5px; background: rgba(255,255,255,.12); overflow: hidden; margin-top: 4px; }
.ws-bar > i { display: block; height: 100%; width: 100%; border-radius: 5px; transition: width .15s; }
.ws-hp > i { background: linear-gradient(90deg, #c8463b, #ef7a54); }
.ws-st > i { background: linear-gradient(90deg, #4aa99a, #9fe0b8); }
.ws-quest h3 { margin: 0 0 4px; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--gold); }
.ws-quest ol { margin: 0; padding: 0; list-style: none; display: grid; gap: 2px; font-size: 14px; }
.ws-quest li { opacity: .45; padding-left: 18px; position: relative; }
.ws-quest li::before { content: "○"; position: absolute; left: 0; }
.ws-quest li.now { opacity: 1; }
.ws-quest li.now::before { content: "◆"; color: var(--gold); }
.ws-quest li.done { opacity: .55; text-decoration: line-through; }
.ws-quest li.done::before { content: "✓"; color: #9fe0b8; }
.ws-quest li:not(.now):not(.done) { display: none; }
.ws-right { display: flex; gap: 8px; }
.ws-icon { width: 40px; height: 40px; border-radius: 50%; background: var(--panel); border: 1px solid var(--line); display: grid; place-content: center; font-size: 18px; }
.ws-boss { position: absolute; left: 50%; top: max(14px, env(safe-area-inset-top)); transform: translateX(-50%); width: min(360px, 54vw); text-align: center; font-size: 12px; letter-spacing: .1em; text-transform: uppercase; }
.ws-boss .ws-bar { height: 10px; }
.ws-boss .ws-bar > i { background: linear-gradient(90deg, #6c7bd9, #b9a2ff); }
.ws-prompt { position: absolute; left: 50%; bottom: 22%; transform: translateX(-50%); display: grid; gap: 6px; justify-items: center; text-align: center; }
.ws-chip { background: var(--panel); border: 1px solid var(--line); border-radius: 999px; padding: 6px 14px; font-size: 14px; white-space: nowrap; }
.ws-chip kbd { font: 600 12px ui-monospace, monospace; background: rgba(255,255,255,.18); border-radius: 4px; padding: 1px 6px; margin-right: 6px; }
.ws-chip.warn { border-color: #f2b45a; color: #ffd79a; animation: ws-pulse .5s infinite alternate; }
@keyframes ws-pulse { to { background: rgba(120, 70, 20, .75); } }
.ws-toast { position: absolute; left: 50%; top: 22%; transform: translateX(-50%); font-size: clamp(18px, 4vw, 26px); font-weight: 650; text-shadow: 0 2px 12px #000a; text-align: center; transition: opacity .5s; opacity: 0; width: max-content; max-width: calc(100vw - 32px); }
.ws-toast.on { opacity: 1; }
.ws-hint { position: absolute; left: max(12px, env(safe-area-inset-left)); bottom: max(12px, env(safe-area-inset-bottom)); font-size: 12px; opacity: .75; line-height: 1.6; }
.ws-hint kbd { font: 600 11px ui-monospace, monospace; background: rgba(255,255,255,.15); border-radius: 3px; padding: 0 5px; }
.ws-hud.talking .ws-hint, .ws-hud.talking .ws-touch .b-attack ~ * { visibility: hidden; }
.ws-dialog { position: absolute; left: 50%; bottom: max(16px, env(safe-area-inset-bottom)); transform: translateX(-50%); width: min(620px, calc(100vw - 24px)); pointer-events: auto; padding: 14px 16px 12px; }
.ws-dialog b { color: var(--gold); display: block; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 4px; }
.ws-dialog p { margin: 0 0 8px; font-size: 16px; min-height: 3em; }
.ws-dialog small { opacity: .65; display: block; text-align: right; }
.ws-marker { position: absolute; left: 0; top: 0; transform: translate(-50%, -100%); display: grid; justify-items: center; font-size: 12px; font-weight: 650; text-shadow: 0 1px 4px #000; color: var(--gold); }
.ws-marker i { width: 14px; height: 14px; background: var(--gold); transform: rotate(45deg); border: 2px solid #fff8; box-shadow: 0 0 12px var(--gold); margin-bottom: 3px; }
.ws-marker.edge i { transform: rotate(var(--a)) ; clip-path: polygon(50% 0, 100% 100%, 0 100%); border: 0; width: 16px; height: 16px; }
.ws-fade { position: absolute; inset: 0; background: #0b0e16; opacity: 0; transition: opacity .5s; }
.ws-fade.on { opacity: 1; }
.ws-touch { position: absolute; right: max(14px, env(safe-area-inset-right)); bottom: max(18px, env(safe-area-inset-bottom)); width: 210px; height: 200px; }
.ws-touch button { position: absolute; border-radius: 50%; background: rgba(18, 22, 34, .55); border: 1.5px solid rgba(255,255,255,.3); font-size: 12px; font-weight: 650; letter-spacing: .04em; touch-action: none; display: grid; place-content: center; text-align: center; line-height: 1.1; }
.ws-touch button.on { background: rgba(233, 196, 106, .55); }
.ws-touch .b-attack { width: 84px; height: 84px; right: 0; bottom: 0; font-size: 14px; }
.ws-touch .b-jump { width: 62px; height: 62px; right: 96px; bottom: 0; }
.ws-touch .b-skill { width: 62px; height: 62px; right: 10px; bottom: 98px; }
.ws-touch .b-interact { width: 56px; height: 56px; right: 100px; bottom: 80px; }
.ws-touch .b-interact.dim { opacity: .35; }
.ws-stick { position: absolute; left: -56px; top: -56px; width: 112px; height: 112px; border-radius: 50%; border: 2px solid rgba(255,255,255,.35); background: rgba(18,22,34,.3); pointer-events: none; }
.ws-stick i { position: absolute; left: 31px; top: 31px; width: 46px; height: 46px; border-radius: 50%; background: rgba(255,255,255,.45); }
.ws-select { position: absolute; inset: 0; display: grid; grid-template-rows: auto 1fr auto; padding: max(18px, env(safe-area-inset-top)) 16px max(18px, env(safe-area-inset-bottom)); pointer-events: none; transition: opacity .6s; }
.ws-select h1 { margin: 0; text-align: center; font: 600 clamp(26px, 6vw, 44px)/1.1 Georgia, "Iowan Old Style", serif; letter-spacing: .04em; text-shadow: 0 2px 18px #000a; }
.ws-select h1 + p { margin: 6px 0 0; text-align: center; opacity: .8; }
.ws-card { justify-self: center; width: min(460px, 100%); pointer-events: auto; padding: 14px 16px; display: grid; gap: 8px; }
.ws-card .row { display: flex; align-items: center; gap: 10px; }
.ws-card h2 { flex: 1; margin: 0; text-align: center; font: 600 24px Georgia, serif; }
.ws-card .arrow { width: 44px; height: 44px; border-radius: 50%; background: rgba(255,255,255,.1); border: 1px solid var(--line); font-size: 18px; }
.ws-card p { margin: 0; text-align: center; opacity: .9; }
.ws-card .skill { text-align: center; font-size: 14px; background: rgba(255,255,255,.06); border-radius: 8px; padding: 8px; }
.ws-card .skill b { color: var(--gold); }
.ws-card .dots { display: flex; justify-content: center; gap: 8px; }
.ws-card .dots button { width: auto; padding: 4px 10px; border-radius: 999px; font-size: 12px; background: transparent; border: 1px solid var(--line); opacity: .7; }
.ws-card .dots button.on { opacity: 1; border-color: var(--gold); color: var(--gold); }
.ws-start { margin-top: 4px; padding: 12px; border-radius: 10px; border: 0; background: var(--gold); color: #1d2433 !important; font-weight: 700 !important; font-size: 17px !important; }
.ws-end { position: absolute; inset: 0; display: grid; place-content: center; pointer-events: none; padding: 16px; }
.ws-end .ws-panel { pointer-events: auto; text-align: center; padding: 22px 22px 18px; width: min(440px, calc(100vw - 32px)); display: grid; gap: 10px; }
.ws-end h2 { margin: 0; font: 600 30px Georgia, serif; color: var(--gold); }
.ws-end p { margin: 0; }
@media (max-width: 600px) {
  #ui { font-size: 14px; }
  .ws-quest ol { font-size: 13px; }
  .ws-prompt { bottom: 264px; }
  .ws-dialog { bottom: 230px; }
  .ws-dialog p { font-size: 15px; min-height: 0; }
  .ws-boss { top: auto; bottom: 222px; width: 70vw; padding: 4px 10px; }
}
@media (max-width: 600px) and (pointer: fine) { .ws-dialog { bottom: 16px; } .ws-prompt { bottom: 28%; } .ws-boss { top: 14px; bottom: auto; } }
`;

const h = <K extends keyof HTMLElementTagNameMap>(tag: K, cls = "", html = "") => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html) e.innerHTML = html;
  return e;
};

export interface Steps {
  id: string;
  text: string;
}

export class UI {
  readonly root: HTMLElement;
  readonly hud = h("div", "ws-hud");
  private hp = h("div", "ws-bar ws-hp", "<i></i>");
  private st = h("div", "ws-bar ws-st", "<i></i>");
  private who = h("div", "ws-who");
  private questList = h("ol");
  private boss = h("div", "ws-boss ws-panel", `<div>Stormspawn</div><div class="ws-bar"><i></i></div>`);
  private prompt = h("div", "ws-prompt");
  private toastEl = h("div", "ws-toast");
  private dialog = h("div", "ws-dialog ws-panel");
  private marker = h("div", "ws-marker", "<i></i><span></span>");
  private fadeEl = h("div", "ws-fade");
  private interactBtn?: HTMLElement;
  private toastTimer = 0;
  muteBtn = h("button", "ws-icon", "🔊");
  private dialogNext?: () => void;

  constructor(private input: Input) {
    this.root = document.getElementById("ui")!;
    const style = h("style");
    style.textContent = CSS;
    document.head.append(style);
    const left = h("div", "ws-left");
    const bars = h("div", "ws-panel");
    bars.append(this.who, this.hp, this.st);
    const quest = h("div", "ws-panel ws-quest", "<h3>Relight the Waystone</h3>");
    quest.append(this.questList);
    left.append(bars, quest);
    const right = h("div", "ws-right");
    this.muteBtn.setAttribute("aria-label", "Mute");
    right.append(this.muteBtn);
    const top = h("div", "ws-top");
    top.append(left, right);
    this.boss.hidden = true;
    this.dialog.hidden = true;
    this.marker.hidden = true;
    this.hud.append(top, this.boss, this.prompt, this.toastEl, this.marker, this.dialog);
    if (input.touch) {
      const pad = h("div", "ws-touch");
      for (const [b, label] of [["attack", "Attack"], ["jump", "Jump"], ["skill", "Skill"], ["interact", "Use"]] as const) {
        const btn = h("button", `b-${b}`, label);
        input.bindTouchButton(btn, b);
        pad.append(btn);
        if (b === "skill") btn.dataset.skill = "1";
        if (b === "interact") this.interactBtn = btn;
      }
      this.hud.append(pad);
    } else {
      this.hud.append(
        h("div", "ws-hint", "<kbd>WASD</kbd> move · <kbd>Mouse</kbd> look (click to lock, or right-drag) · <kbd>Space</kbd> jump<br><kbd>Shift</kbd> <span class='sk'>skill</span> · <kbd>E</kbd> interact · <kbd>Click</kbd> attack · <kbd>Esc</kbd> free mouse"),
      );
    }
    this.hud.hidden = true;
    this.dialog.addEventListener("pointerdown", (e) => {
      e.stopPropagation();
      this.advance();
    });
    this.root.append(this.hud, this.fadeEl);
  }

  setPeople(p: PeopleDef) {
    this.who.innerHTML = `<span>${p.name}</span><span>${p.skill.name} · Shift</span>`;
    if (this.input.touch) {
      this.who.innerHTML = `<span>${p.name}</span><span>${p.skill.name}</span>`;
      const b = this.hud.querySelector<HTMLElement>("[data-skill]");
      if (b) b.textContent = p.skill.name;
    }
    const sk = this.hud.querySelector(".sk");
    if (sk) sk.textContent = p.skill.name;
  }

  bars(hp: number, st: number) {
    (this.hp.firstChild as HTMLElement).style.width = `${Math.max(0, hp) * 100}%`;
    (this.st.firstChild as HTMLElement).style.width = `${Math.max(0, st) * 100}%`;
  }

  quest(steps: Steps[], now: number) {
    this.questList.innerHTML = steps.map((s, i) => `<li class="${i < now ? "done" : i === now ? "now" : ""}">${s.text}</li>`).join("");
  }

  bossBar(frac: number | null) {
    this.boss.hidden = frac === null;
    if (frac !== null) (this.boss.querySelector(".ws-bar i") as HTMLElement).style.width = `${Math.max(0, frac) * 100}%`;
  }

  /** chips: [key label, text, warn?] */
  prompts(chips: [string, string, boolean?][]) {
    const html = chips
      .map(([k, t, w]) => `<div class="ws-chip${w ? " warn" : ""}">${k && !this.input.touch ? `<kbd>${k}</kbd>` : ""}${t}</div>`)
      .join("");
    if (this.prompt.innerHTML !== html) this.prompt.innerHTML = html;
  }

  interactAvailable(on: boolean) {
    this.interactBtn?.classList.toggle("dim", !on);
  }

  toast(text: string, secs = 2.5) {
    this.toastEl.textContent = text;
    this.toastEl.classList.add("on");
    clearTimeout(this.toastTimer);
    this.toastTimer = window.setTimeout(() => this.toastEl.classList.remove("on"), secs * 1000);
  }

  /** Screen-space objective marker; clamps to the edge with an arrow when off screen. */
  setMarker(p: { x: number; y: number; behind: boolean } | null, label = "", edgeOnly = false) {
    this.marker.hidden = !p;
    if (!p) return;
    const pad = 36;
    const W = innerWidth, H = innerHeight;
    let { x, y } = p;
    const off = p.behind || x < pad || x > W - pad || y < pad + 60 || y > H - pad;
    if (p.behind) (x = W - x), (y = H - pad);
    const cx = Math.min(W - pad, Math.max(pad, x)), cy = Math.min(H - pad, Math.max(pad + 60, y));
    this.marker.classList.toggle("edge", off);
    if (edgeOnly && !off) {
      this.marker.hidden = true;
      return;
    }
    if (off) this.marker.style.setProperty("--a", `${Math.atan2(cy - H / 2, cx - W / 2) + Math.PI / 2}rad`);
    this.marker.style.transform = `translate(${cx}px, ${cy}px) translate(-50%, -100%)`;
    (this.marker.lastChild as HTMLElement).textContent = label;
  }

  /** Show pages one by one; resolves when the last is dismissed. */
  say(name: string, pages: string[], onPage?: () => void): Promise<void> {
    return new Promise((done) => {
      let i = 0;
      const show = () => {
        this.dialog.hidden = false;
        this.hud.classList.add("talking");
        const more = i < pages.length - 1;
        const key = this.input.touch ? "Tap" : "E / Click";
        this.dialog.innerHTML = `<b>${name}</b><p>${pages[i]}</p><small>${key} ${more ? "▸ next" : "▸ close"}</small>`;
        onPage?.();
      };
      this.dialogNext = () => {
        i++;
        if (i >= pages.length) {
          this.dialog.hidden = true;
          this.hud.classList.remove("talking");
          this.dialogNext = undefined;
          done();
        } else show();
      };
      show();
    });
  }

  get talking() {
    return !!this.dialogNext;
  }

  advance() {
    this.dialogNext?.();
  }

  fade(on: boolean) {
    this.fadeEl.classList.toggle("on", on);
    return new Promise((r) => setTimeout(r, 520));
  }

  /** Race select overlay. The 3D turntable is driven by the caller via onChange. */
  select(initial: People, played: People[], onChange: (p: People) => void): Promise<People> {
    return new Promise((resolve) => {
      const wrap = h("div", "ws-select");
      let idx = Math.max(0, PEOPLES.findIndex((p) => p.id === initial));
      const card = h("div", "ws-card ws-panel");
      wrap.append(h("div", "", "<h1>Waystone</h1><p>Choose your people</p>"), h("div"), card);
      const render = () => {
        const p = PEOPLES[idx];
        card.innerHTML = `
          <div class="dots">${PEOPLES.map((q, i) => `<button data-i="${i}" class="${i === idx ? "on" : ""}">${q.name}${played.includes(q.id) ? " ✓" : ""}</button>`).join("")}</div>
          <div class="row"><button class="arrow" data-d="-1" aria-label="Previous">◀</button><h2>${p.name}</h2><button class="arrow" data-d="1" aria-label="Next">▶</button></div>
          <p>${p.line}</p>
          <div class="skill">Innate skill: <b>${p.skill.name}</b><br>${p.skill.text}</div>
          <button class="ws-start">Start as ${p.name}</button>`;
        onChange(p.id);
      };
      const go = (d: number) => {
        idx = (idx + d + PEOPLES.length) % PEOPLES.length;
        render();
      };
      card.addEventListener("click", (e) => {
        const t = (e.target as HTMLElement).closest("button");
        if (!t) return;
        if (t.dataset.d) go(Number(t.dataset.d));
        else if (t.dataset.i) (idx = Number(t.dataset.i)), render();
        else if (t.classList.contains("ws-start")) finish();
      });
      const key = (e: KeyboardEvent) => {
        if (e.code === "ArrowLeft" || e.code === "KeyA") go(-1);
        if (e.code === "ArrowRight" || e.code === "KeyD") go(1);
        if (e.code === "Enter") finish();
      };
      addEventListener("keydown", key);
      let sx = -1;
      const tdown = (e: PointerEvent) => (sx = e.clientX);
      const tup = (e: PointerEvent) => {
        if (sx >= 0 && Math.abs(e.clientX - sx) > 50 && !(e.target as HTMLElement).closest(".ws-card")) go(e.clientX < sx ? 1 : -1);
        sx = -1;
      };
      addEventListener("pointerdown", tdown);
      addEventListener("pointerup", tup);
      const finish = () => {
        removeEventListener("keydown", key);
        removeEventListener("pointerdown", tdown);
        removeEventListener("pointerup", tup);
        wrap.style.opacity = "0";
        setTimeout(() => wrap.remove(), 600);
        resolve(PEOPLES[idx].id);
      };
      this.root.insertBefore(wrap, this.fadeEl);
      render();
    });
  }

  end(p: PeopleDef, secs: number, next: PeopleDef, onAgain: () => void) {
    const wrap = h("div", "ws-end");
    const m = Math.floor(secs / 60), s = Math.round(secs % 60);
    wrap.innerHTML = `<div class="ws-panel"><h2>The lane is lit</h2>
      <p>The Waystone burns again, and every skiff on the Lantern Spoke can find its way.</p>
      <p style="opacity:.75">${p.name} · ${m}:${String(s).padStart(2, "0")}</p>
      <button class="ws-start">Play another people: ${next.name}</button></div>`;
    wrap.querySelector("button")!.addEventListener("click", onAgain);
    this.hud.hidden = true;
    this.root.insertBefore(wrap, this.fadeEl);
  }
}
