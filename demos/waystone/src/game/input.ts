// Unified input: keyboard + mouse (pointer lock) and touch (virtual stick, drag-look, buttons).
// Game code reads `move`, `look` deltas and button states; edges via pressed(name).

export type Button = "jump" | "skill" | "interact" | "attack";

export class Input {
  readonly touch: boolean;
  /** Movement in camera space: x right, y forward, length 0..1. */
  move = { x: 0, y: 0 };
  /** Look delta accumulated since last frame, in pixels. */
  look = { x: 0, y: 0 };
  zoom = 0;
  enabled = false;
  private keys = new Set<string>();
  private held = new Set<Button>();
  private edges = new Set<Button>();
  private stick = { id: -1, ox: 0, oy: 0, x: 0, y: 0 };
  private lookId = -1;
  private lookLast = { x: 0, y: 0 };
  private touchHeld = new Set<Button>();
  private dragLook = false;
  onFirstGesture?: () => void;

  constructor(private canvas: HTMLCanvasElement, private ui: HTMLElement) {
    this.touch = matchMedia("(pointer: coarse)").matches || ("ontouchstart" in window && navigator.maxTouchPoints > 0);
    addEventListener("keydown", (e) => this.key(e, true));
    addEventListener("keyup", (e) => this.key(e, false));
    addEventListener("blur", () => {
      this.keys.clear();
      this.held.clear();
    });
    canvas.addEventListener("mousedown", (e) => {
      this.gesture();
      if (!this.enabled) return;
      if (e.button === 2) {
        this.dragLook = true; // fallback look where pointer lock is unavailable
        return;
      }
      if (e.button !== 0) return;
      if (document.pointerLockElement !== canvas && !this.touch) {
        try {
          void (canvas.requestPointerLock?.() as unknown as Promise<void> | undefined)?.catch?.(() => {});
        } catch {
          /* embedded without pointer-lock permission: right-drag looks instead */
        }
      }
      this.press("attack");
    });
    addEventListener("mouseup", (e) => {
      if (e.button === 0) this.release("attack");
      if (e.button === 2) this.dragLook = false;
    });
    addEventListener("mousemove", (e) => {
      if (document.pointerLockElement === canvas || this.dragLook) {
        this.look.x += e.movementX;
        this.look.y += e.movementY;
      }
    });
    canvas.addEventListener("wheel", (e) => (this.zoom += e.deltaY), { passive: true });
    canvas.addEventListener("contextmenu", (e) => e.preventDefault());

    // Touch: left half = stick (spawns where you put your thumb), right half = look
    canvas.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "mouse") return;
      this.gesture();
      if (!this.enabled) return;
      if (e.clientX < innerWidth * 0.45 && this.stick.id < 0) {
        this.stick = { id: e.pointerId, ox: e.clientX, oy: e.clientY, x: e.clientX, y: e.clientY };
        this.showStick(true);
      } else if (this.lookId < 0) {
        this.lookId = e.pointerId;
        this.lookLast = { x: e.clientX, y: e.clientY };
      }
    });
    addEventListener("pointermove", (e) => {
      if (e.pointerId === this.stick.id) {
        this.stick.x = e.clientX;
        this.stick.y = e.clientY;
        this.showStick(true);
      } else if (e.pointerId === this.lookId) {
        this.look.x += (e.clientX - this.lookLast.x) * 1.6;
        this.look.y += (e.clientY - this.lookLast.y) * 1.6;
        this.lookLast = { x: e.clientX, y: e.clientY };
      }
    });
    const end = (e: PointerEvent) => {
      if (e.pointerId === this.stick.id) {
        this.stick.id = -1;
        this.showStick(false);
      }
      if (e.pointerId === this.lookId) this.lookId = -1;
    };
    addEventListener("pointerup", end);
    addEventListener("pointercancel", end);
  }

  private gesture() {
    this.onFirstGesture?.();
    this.onFirstGesture = undefined;
  }

  private key(e: KeyboardEvent, down: boolean) {
    if (down) this.gesture();
    if (e.code === "Space" || e.code.startsWith("Arrow")) e.preventDefault();
    if (down) this.keys.add(e.code);
    else this.keys.delete(e.code);
    const map: Record<string, Button> = { Space: "jump", ShiftLeft: "skill", ShiftRight: "skill", KeyE: "interact", KeyF: "attack", KeyJ: "attack" };
    const b = map[e.code];
    if (!b) return;
    if (down && !e.repeat) this.press(b);
    if (!down) this.release(b);
  }

  press(b: Button) {
    if (!this.held.has(b)) this.edges.add(b);
    this.held.add(b);
  }
  release(b: Button) {
    this.held.delete(b);
  }
  /** True once per press. */
  pressed(b: Button) {
    return this.enabled && this.edges.has(b);
  }
  down(b: Button) {
    return this.enabled && this.held.has(b);
  }

  /** Touch buttons in the HUD call these. */
  bindTouchButton(el: HTMLElement, b: Button) {
    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.gesture();
      el.setPointerCapture(e.pointerId);
      el.classList.add("on");
      this.touchHeld.add(b);
      this.press(b);
    });
    const up = () => {
      el.classList.remove("on");
      this.touchHeld.delete(b);
      this.release(b);
    };
    el.addEventListener("pointerup", up);
    el.addEventListener("pointercancel", up);
    el.addEventListener("lostpointercapture", up);
  }

  private stickEl?: HTMLElement;
  private showStick(on: boolean) {
    if (!this.stickEl) {
      this.stickEl = document.createElement("div");
      this.stickEl.className = "ws-stick";
      this.stickEl.innerHTML = "<i></i>";
      this.ui.append(this.stickEl);
    }
    this.stickEl.hidden = !on;
    if (!on) return;
    const R = 56;
    let dx = this.stick.x - this.stick.ox, dy = this.stick.y - this.stick.oy;
    const l = Math.hypot(dx, dy);
    if (l > R) (dx *= R / l), (dy *= R / l);
    this.stickEl.style.transform = `translate(${this.stick.ox}px, ${this.stick.oy}px)`;
    (this.stickEl.firstChild as HTMLElement).style.transform = `translate(${dx}px, ${dy}px)`;
  }

  /** Call once per frame before reading. */
  update() {
    let x = 0, y = 0;
    const k = this.keys;
    if (k.has("KeyW") || k.has("ArrowUp")) y += 1;
    if (k.has("KeyS") || k.has("ArrowDown")) y -= 1;
    if (k.has("KeyD") || k.has("ArrowRight")) x += 1;
    if (k.has("KeyA") || k.has("ArrowLeft")) x -= 1;
    const l = Math.hypot(x, y);
    if (l > 0) (x /= l), (y /= l);
    if (this.stick.id >= 0) {
      const R = 56;
      const dx = (this.stick.x - this.stick.ox) / R, dy = (this.stick.y - this.stick.oy) / R;
      const m = Math.min(1, Math.hypot(dx, dy));
      if (m > 0.12) {
        const a = Math.atan2(dy, dx);
        x = Math.cos(a) * m;
        y = -Math.sin(a) * m;
      }
    }
    this.move.x = this.enabled ? x : 0;
    this.move.y = this.enabled ? y : 0;
  }

  /** Call once per frame after reading. */
  endFrame() {
    this.edges.clear();
    this.look.x = this.look.y = 0;
    this.zoom = 0;
  }

  releaseAll() {
    this.held.clear();
    this.keys.clear();
    this.edges.clear();
  }
}
