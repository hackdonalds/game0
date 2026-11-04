// All sound is synthesized here with WebAudio: no sample files, nothing to license (see public/audio/CREDITS.md).
// Wind and campfire loops, footsteps, swing, hit, pickup, boss cues and a short theme.

export class Audio {
  ctx?: AudioContext;
  private master?: GainNode;
  private sfx?: GainNode;
  private windGain?: GainNode;
  private windFilter?: BiquadFilterNode;
  private fireGain?: GainNode;
  private noise?: AudioBuffer;
  private nextCrackle = 0;
  // Silent on any local server, dev or preview (and with ?mute) so playtests during development make no noise; ?sound turns it back on
  muted = (import.meta.env.DEV || /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname) || new URLSearchParams(location.search).has("mute")) && !new URLSearchParams(location.search).has("sound");
  private storm = 0.3;

  /** Must run inside a user gesture. */
  start() {
    if (this.ctx) {
      void this.ctx.resume();
      return;
    }
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AC) return;
    const ctx = (this.ctx = new AC());
    this.master = ctx.createGain();
    this.master.gain.value = this.muted ? 0 : 0.8;
    this.master.connect(ctx.destination);
    this.sfx = ctx.createGain();
    this.sfx.connect(this.master);
    // 3 s of white noise reused by everything
    const len = ctx.sampleRate * 3;
    this.noise = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = this.noise.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;

    // Wind: noise through a slowly wandering band-pass
    const wind = this.src(true);
    this.windFilter = ctx.createBiquadFilter();
    this.windFilter.type = "bandpass";
    this.windFilter.Q.value = 0.7;
    this.windFilter.frequency.value = 400;
    this.windGain = ctx.createGain();
    this.windGain.gain.value = 0;
    wind.connect(this.windFilter).connect(this.windGain).connect(this.master);
    wind.start();
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.13;
    const lfoAmt = ctx.createGain();
    lfoAmt.gain.value = 220;
    lfo.connect(lfoAmt).connect(this.windFilter.frequency);
    lfo.start();

    // Campfire bed: low rumble of filtered noise, crackles added in update()
    const fire = this.src(true);
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = 500;
    this.fireGain = ctx.createGain();
    this.fireGain.gain.value = 0;
    fire.connect(lp).connect(this.fireGain).connect(this.master);
    fire.start();
  }

  private src(loop = false) {
    const s = this.ctx!.createBufferSource();
    s.buffer = this.noise!;
    s.loop = loop;
    if (!loop) s.loopStart = 0;
    return s;
  }

  setMuted(m: boolean) {
    this.muted = m;
    if (this.master && this.ctx) this.master.gain.setTargetAtTime(m ? 0 : 0.8, this.ctx.currentTime, 0.05);
  }

  setStorm(level: number) {
    this.storm = level;
  }

  /** campDist in metres (Infinity when unknown). */
  update(campDist: number) {
    const ctx = this.ctx;
    if (!ctx || !this.windGain || !this.fireGain || !this.windFilter) return;
    const now = ctx.currentTime;
    this.windGain.gain.setTargetAtTime(0.05 + this.storm * 0.22, now, 0.5);
    this.windFilter.Q.setTargetAtTime(0.6 + this.storm * 0.8, now, 0.5);
    const fire = Math.max(0, 1 - campDist / 16);
    this.fireGain.gain.setTargetAtTime(fire * 0.12, now, 0.2);
    if (fire > 0 && now > this.nextCrackle) {
      this.nextCrackle = now + 0.04 + Math.random() * 0.25;
      this.burst({ freq: 1800 + Math.random() * 2500, q: 3, dur: 0.02 + Math.random() * 0.03, gain: fire * (0.15 + Math.random() * 0.25), type: "bandpass", dest: this.master });
    }
  }

  private burst(o: { freq: number; q?: number; dur: number; gain: number; type?: BiquadFilterType; sweepTo?: number; dest?: AudioNode; delay?: number }) {
    const ctx = this.ctx;
    if (!ctx || this.muted) return;
    const t = ctx.currentTime + (o.delay ?? 0);
    const s = this.src();
    const f = ctx.createBiquadFilter();
    f.type = o.type ?? "bandpass";
    f.frequency.setValueAtTime(o.freq, t);
    if (o.sweepTo) f.frequency.exponentialRampToValueAtTime(o.sweepTo, t + o.dur);
    f.Q.value = o.q ?? 1;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(o.gain, t + Math.min(0.01, o.dur * 0.2));
    g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);
    s.connect(f).connect(g).connect(o.dest ?? this.sfx!);
    s.start(t, Math.random() * 2, o.dur + 0.05);
  }

  private tone(o: { freq: number; to?: number; dur: number; gain: number; type?: OscillatorType; delay?: number; attack?: number }) {
    const ctx = this.ctx;
    if (!ctx || this.muted) return;
    const t = ctx.currentTime + (o.delay ?? 0);
    const osc = ctx.createOscillator();
    osc.type = o.type ?? "sine";
    osc.frequency.setValueAtTime(o.freq, t);
    if (o.to) osc.frequency.exponentialRampToValueAtTime(o.to, t + o.dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(o.gain, t + (o.attack ?? 0.01));
    g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);
    osc.connect(g).connect(this.sfx!);
    osc.start(t);
    osc.stop(t + o.dur + 0.05);
  }

  step(heavy: number) {
    this.burst({ freq: 260 + Math.random() * 120 - heavy * 90, q: 0.8, dur: 0.09 + heavy * 0.05, gain: 0.25 + heavy * 0.15, type: "lowpass" });
  }
  swing() {
    this.burst({ freq: 600, sweepTo: 2600, q: 1.5, dur: 0.18, gain: 0.35 });
  }
  hit(big = false) {
    this.tone({ freq: big ? 140 : 190, to: 60, dur: 0.22, gain: 0.5, type: "triangle" });
    this.burst({ freq: 1200, q: 0.7, dur: 0.12, gain: 0.4 });
  }
  hurt() {
    this.tone({ freq: 220, to: 90, dur: 0.3, gain: 0.35, type: "sawtooth" });
    this.burst({ freq: 500, q: 0.7, dur: 0.2, gain: 0.35, type: "lowpass" });
  }
  pickup() {
    [784, 988, 1175, 1568].forEach((f, i) => this.tone({ freq: f, dur: 0.5, gain: 0.18, delay: i * 0.07 }));
  }
  gust() {
    this.burst({ freq: 300, sweepTo: 1400, q: 0.8, dur: 1.1, gain: 0.35 });
  }
  roar() {
    this.tone({ freq: 110, to: 55, dur: 0.9, gain: 0.3, type: "sawtooth", attack: 0.1 });
    this.burst({ freq: 400, sweepTo: 150, q: 1, dur: 0.9, gain: 0.4, type: "lowpass" });
  }
  charge() {
    this.burst({ freq: 200, sweepTo: 2000, q: 1, dur: 0.7, gain: 0.45 });
  }
  thump() {
    this.tone({ freq: 80, to: 40, dur: 0.35, gain: 0.5 });
  }
  talk() {
    this.tone({ freq: 330 + Math.random() * 60, dur: 0.06, gain: 0.05, type: "triangle" });
  }
  ui() {
    this.tone({ freq: 660, dur: 0.12, gain: 0.12, type: "triangle" });
  }
  heal() {
    this.tone({ freq: 523, to: 784, dur: 0.6, gain: 0.08, attack: 0.2 });
  }

  /** Short pentatonic theme over a soft pad. `bright` for the ending. */
  theme(bright = false) {
    if (!this.ctx) return;
    const root = bright ? 392 : 330;
    const scale = [0, 2, 4, 7, 9, 12, 14];
    const melody = bright ? [0, 2, 4, 5, 4, 6, 5, 3, 4] : [0, 2, 3, 2, 4, 3, 1, 2, 0];
    const beat = bright ? 0.42 : 0.5;
    melody.forEach((n, i) => {
      const f = root * Math.pow(2, scale[n] / 12);
      this.tone({ freq: f, dur: beat * 1.8, gain: 0.12, type: "triangle", delay: i * beat, attack: 0.03 });
    });
    for (const [n, d] of [[0, 0], [4, 0], [3, 4 * beat], [5, 4 * beat]] as const)
      this.tone({ freq: (root / 2) * Math.pow(2, scale[n] / 12), dur: beat * 5, gain: 0.07, type: "sine", delay: d, attack: 0.6 });
  }
}
