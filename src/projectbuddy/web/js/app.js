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

// --- Camera test (M7, ?camtest=1): a dev affordance to exercise the whole face flow.
//     Grabs a frame periodically and asks the backend who it sees, and offers an
//     "Enroll my face" button that runs create-person → consent → enroll on the
//     current frame so recognition has someone to match. The full parent capture UI
//     lands in M9. ---
async function startCamtest() {
  document.body.classList.add('kiosk');
  caption.textContent = 'Camera test — point at a face, then "Enroll my face".';
  const video = document.createElement('video');
  video.autoplay = true;
  video.playsInline = true;
  const canvas = document.createElement('canvas');

  let busy = false; // pause the recognize loop during enrollment

  const grabFrame = () => {
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return null;
    canvas.width = w;
    canvas.height = h;
    canvas.getContext('2d').drawImage(video, 0, 0, w, h);
    return canvas.toDataURL('image/jpeg').split(',')[1];
  };

  const postJSON = (url, body) =>
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

  // An on-screen enroll button (created here so no HTML change is needed).
  const enrollBtn = document.createElement('button');
  enrollBtn.textContent = '📸 Enroll my face';
  enrollBtn.style.cssText =
    'position:absolute;bottom:24px;left:50%;transform:translateX(-50%);' +
    'border:none;border-radius:12px;padding:12px 18px;font:inherit;font-weight:800;' +
    'color:#fff;background:#22c55e;cursor:pointer;z-index:10;';
  enrollBtn.addEventListener('click', async () => {
    if (!grabFrame()) return;
    const name = prompt("Whose face is this?", 'Me');
    if (!name) return;
    busy = true;
    enrollBtn.disabled = true;
    // Capture several frames a fraction of a second apart so the backend can average
    // them (and log cross-frame consistency for the same face).
    caption.textContent = `Capturing ${name}…`;
    const images = [];
    for (let i = 0; i < 3; i++) {
      const f = grabFrame();
      if (f) images.push(f);
      await new Promise((r) => setTimeout(r, 400));
    }
    if (!images.length) {
      caption.textContent = 'No frame captured — try again.';
      enrollBtn.disabled = false;
      busy = false;
      return;
    }
    caption.textContent = `Enrolling ${name}…`;
    try {
      const person = await postJSON('/person', { display_name: name, role: 'child' }).then((r) =>
        r.json()
      );
      await postJSON(`/person/${person.id}/consent`, { scope: 'face', granted: true });
      const res = await postJSON(`/person/${person.id}/enroll`, { images });
      if (res.status === 400) {
        caption.textContent = 'I couldn’t find a face in that frame — try again, well-lit and centered.';
      } else if (!res.ok) {
        caption.textContent = `Enroll failed (HTTP ${res.status}).`;
      } else {
        caption.textContent = `Enrolled ${name}! Now point the camera back at your face.`;
      }
    } catch (_) {
      caption.textContent = 'Enroll failed — is the backend running?';
    } finally {
      enrollBtn.disabled = false;
      busy = false;
    }
  });
  document.getElementById('stage').appendChild(enrollBtn);

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
    if (busy) return;
    const image = grabFrame();
    if (!image) return;
    try {
      const r = await postJSON('/recognize', { image }).then((resp) => resp.json());
      caption.textContent = r.matched
        ? `I see ${r.person_id ? 'person #' + r.person_id : 'someone'} (${r.confidence.toFixed(2)})`
        : `No match yet (best ${r.confidence.toFixed(2)})`;
    } catch (_) {
      /* keep trying on the next tick */
    }
  }, 2500);
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
