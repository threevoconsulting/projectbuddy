// Client state machine: idle → listening → thinking → speaking → idle.
// Decoupled from rendering — it just decides which (state, emotion, amplitude) the
// face should show. In M4 the WebSocket frames drive these transitions; in the M3
// text demo, app.js drives them.

class BuddyState {
  constructor(render) {
    this.render = render;
    this.state = 'idle';
    this.emotion = 'happy';
    this.amplitude = 0;
  }

  toIdle() {
    this.state = 'idle';
    this.render(this.emotion, 0);
  }

  toListening() {
    this.state = 'listening';
    this.render('listening', 0);
  }

  toThinking() {
    this.state = 'thinking';
    this.render('thinking', 0);
  }

  toSpeaking(emotion) {
    this.state = 'speaking';
    this.emotion = emotion;
    this.render(emotion, this.amplitude);
  }

  // Drift off to sleep after a stretch of no interaction (M6). The inactivity timer
  // that calls this lives in app.js; wake() is called on any child activity.
  toSleepy() {
    this.state = 'idle';
    this.emotion = 'sleepy';
    this.render('sleepy', 0);
  }

  wake() {
    if (this.emotion === 'sleepy') this.emotion = 'happy';
    this.toIdle();
  }

  setEmotion(emotion) {
    this.emotion = emotion;
    if (this.state === 'idle' || this.state === 'speaking') {
      this.render(emotion, this.amplitude);
    }
  }

  // 0..1, drives the mouth while speaking.
  setAmplitude(a) {
    this.amplitude = a;
    if (this.state === 'speaking') this.render(this.emotion, a);
  }
}

window.BuddyState = BuddyState;
