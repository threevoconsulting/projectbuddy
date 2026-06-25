// Wiring for the Phase-1 text demo + the mock harness + behaviour polish (M6).
//
//   /app/            → type or hold-to-talk; backend returns {emotion, say}, face reacts.
//   /app/?mock=1     → cycle all 8 emotions (incl. sleepy) with a fake amplitude
//                      oscillator (no backend / no models — pure face QA).
//   /app/?kiosk=1    → robot-screen layout: hide controls, keep screen awake, hide the
//                      cursor when idle, suppress context menu / zoom.
//
// Buddy also blinks at rest and drifts to sleep after a stretch of no interaction.

const params = new URLSearchParams(location.search);
const buddy = new BuddyState(window.BuddyFace.render);
const caption = document.getElementById('caption');

const KIOSK = params.get('kiosk') === '1';
if (KIOSK) document.body.classList.add('kiosk');

buddy.toIdle();
caption.textContent = "Hi! I'm Buddy. Talk to me!";

// --- Camera-active indicator (M7): the only owner of the on-screen "camera on" cue. ---
window.BuddyCamera = {
  show() { document.getElementById('camera-indicator')?.classList.add('active'); },
  hide() { document.getElementById('camera-indicator')?.classList.remove('active'); },
};

// --- Blinking: a quick lid-squash every few seconds while at rest or speaking. ---
function startBlink() {
  const head = document.getElementById('head');
  (function loop() {
    setTimeout(() => {
      const restful = buddy.state === 'idle' || buddy.state === 'speaking';
      if (restful && buddy.emotion !== 'sleepy') {
        head.classList.add('blink');
        setTimeout(() => head.classList.remove('blink'), 120);
      }
      loop();
    }, 3000 + Math.random() * 3000);
  })();
}

// --- Sleepy timeout: drift to sleep after inactivity; any activity wakes Buddy. ---
const SLEEPY_AFTER_MS = 45000;
let sleepyTimer = null;
function resetSleepy() {
  if (buddy.emotion === 'sleepy') buddy.wake();
  if (sleepyTimer) clearTimeout(sleepyTimer);
  sleepyTimer = setTimeout(() => {
    if (buddy.state === 'idle') buddy.toSleepy();
  }, SLEEPY_AFTER_MS);
}

function startBehaviours() {
  startBlink();
  resetSleepy();
  ['pointerdown', 'keydown', 'pointermove'].forEach((ev) =>
    window.addEventListener(ev, resetSleepy, { passive: true })
  );
}

// --- Kiosk hardening: screen wake-lock, no context menu/zoom, cursor auto-hide. ---
function setupKiosk() {
  if ('wakeLock' in navigator) {
    let lock = null;
    const acquire = async () => {
      try { lock = await navigator.wakeLock.request('screen'); } catch (_) { /* best effort */ }
    };
    acquire();
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') acquire();
    });
  }
  window.addEventListener('contextmenu', (e) => e.preventDefault());
  document.addEventListener('gesturestart', (e) => e.preventDefault());

  let cursorTimer = null;
  const pokeCursor = () => {
    document.body.classList.remove('cursor-hidden');
    if (cursorTimer) clearTimeout(cursorTimer);
    cursorTimer = setTimeout(() => document.body.classList.add('cursor-hidden'), 3000);
  };
  ['pointermove', 'pointerdown', 'keydown'].forEach((ev) =>
    window.addEventListener(ev, pokeCursor, { passive: true })
  );
  pokeCursor();
}

// --- A simple amplitude oscillator so the mouth moves while "speaking" ---
function animateSpeaking(durationMs) {
  const start = performance.now();
  return new Promise((resolve) => {
    function tick(now) {
      const t = now - start;
      if (t >= durationMs) {
        buddy.setAmplitude(0);
        resolve();
        return;
      }
      // Pseudo-random mouth movement; voice mode feeds real TTS amplitude instead.
      const amp = 0.35 + 0.35 * Math.abs(Math.sin(t / 90)) * Math.abs(Math.cos(t / 50));
      buddy.setAmplitude(amp);
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
}

// Optional: voice the line with the browser's built-in TTS (placeholder for Piper).
function speakAloud(text) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.0;
    u.pitch = 1.2;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  } catch (_) {
    /* speechSynthesis unavailable — the visual demo still works */
  }
}

let sessionId = null;

async function sendText(text) {
  if (!text.trim()) return;
  buddy.toThinking();
  caption.textContent = '…';
  try {
    const resp = await fetch('/converse-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, session_id: sessionId }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    sessionId = data.session_id;
    const { emotion, say } = data.reply;
    buddy.toSpeaking(emotion);
    caption.textContent = say;
    speakAloud(say);
    await animateSpeaking(Math.min(6000, 900 + say.length * 55));
  } catch (err) {
    buddy.toSpeaking('confused');
    caption.textContent = "Hmm, I couldn't reach my brain. Is the backend running?";
  } finally {
    buddy.toIdle();
  }
}

// --- Mock harness: cycle every emotion (incl. sleepy) + oscillate amplitude. ---
function startMock() {
  document.body.classList.add('kiosk');
  const emotions = window.BuddyFace.EMOTIONS;
  let i = 0;
  caption.textContent = 'Mock mode — cycling all expressions';
  buddy.toSpeaking(emotions[0]);
  setInterval(() => {
    i = (i + 1) % emotions.length;
    buddy.toSpeaking(emotions[i]);
    document.getElementById('emotion-label').textContent = emotions[i];
  }, 1600);
  // Continuous gentle mouth movement.
  (function osc(now) {
    buddy.setAmplitude(0.4 + 0.4 * Math.abs(Math.sin((now || 0) / 220)));
    requestAnimationFrame(osc);
  })();
}

// --- Camera test (M7, ?camtest=1): a dev affordance to exercise /recognize and the
//     camera-active indicator. Grabs a frame every couple of seconds and asks the
//     backend who it sees. The full enrollment/parent capture UI lands in M9. ---
async function startCamtest() {
  document.body.classList.add('kiosk');
  caption.textContent = 'Camera test — point at a face.';
  const video = document.createElement('video');
  video.autoplay = true;
  video.playsInline = true;
  const canvas = document.createElement('canvas');
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    window.BuddyCamera.show();
    video.srcObject = stream;
    await video.play();
  } catch (_) {
    caption.textContent = 'No camera available for the test.';
    return;
  }
  setInterval(async () => {
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return;
    canvas.width = w;
    canvas.height = h;
    canvas.getContext('2d').drawImage(video, 0, 0, w, h);
    const image = canvas.toDataURL('image/jpeg').split(',')[1];
    try {
      const resp = await fetch('/recognize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image }),
      });
      const r = await resp.json();
      caption.textContent = r.matched
        ? `I see person #${r.person_id} (${r.confidence.toFixed(2)})`
        : "I don't recognize anyone yet.";
    } catch (_) {
      /* keep trying on the next tick */
    }
  }, 2000);
}

if (params.get('mock') === '1') {
  startMock();
} else if (params.get('camtest') === '1') {
  startCamtest();
} else {
  startBehaviours();
  if (KIOSK) setupKiosk();

  const input = document.getElementById('text-input');
  const sendBtn = document.getElementById('send-btn');
  const mockBtn = document.getElementById('mock-btn');
  sendBtn.addEventListener('click', () => {
    sendText(input.value);
    input.value = '';
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      sendText(input.value);
      input.value = '';
    }
  });
  mockBtn.addEventListener('click', () => {
    location.search = '?mock=1';
  });

  // --- Voice: hold the mic button to talk; release to let Buddy reply. ---
  const talkBtn = document.getElementById('talk-btn');
  const voice = window.BuddyWS.connect(buddy, {
    onCaption: (say) => {
      caption.textContent = say;
    },
    onStatus: (status) => {
      if (status === 'reconnecting') {
        caption.textContent = 'One sec… reconnecting.';
        buddy.setEmotion('curious');
      }
    },
  });
  const press = (e) => {
    e.preventDefault();
    talkBtn.classList.add('active');
    caption.textContent = "I'm listening…";
    voice.startTalking();
  };
  const release = (e) => {
    e.preventDefault();
    talkBtn.classList.remove('active');
    voice.stopTalking();
  };
  talkBtn.addEventListener('pointerdown', press);
  talkBtn.addEventListener('pointerup', release);
  talkBtn.addEventListener('pointerleave', release);
  talkBtn.addEventListener('pointercancel', release);

  // Keep a live connection on the always-on kiosk, and recover it when the screen
  // wakes or the tab returns to the foreground.
  if (KIOSK) {
    voice.open();
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') voice.open();
    });
  }
}

// Register the PWA service worker (offline kiosk shell).
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/app/service-worker.js').catch(() => {});
}
