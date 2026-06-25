// Buddy front-end wiring: one screen where Buddy sees you (camera recognition),
// remembers you (per-person session), and talks with you (voice + text).
//
//   /app/            → camera recognizes the person + hold-to-talk / type to chat.
//   /app/?mock=1     → cycle all 8 emotions (no backend / no models — pure face QA).
//   /app/?kiosk=1    → robot-screen layout: hide controls, wake-lock, hide cursor.
//
// Buddy also blinks at rest and drifts to sleep after a stretch of no interaction.

const params = new URLSearchParams(location.search);
const buddy = new BuddyState(window.BuddyFace.render);
const caption = document.getElementById('caption');

const KIOSK = params.get('kiosk') === '1';
if (KIOSK) document.body.classList.add('kiosk');

buddy.toIdle();
caption.textContent = "Hi! I'm Buddy. Talk to me!";

const postJSON = (url, body) =>
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

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

// Voice the line with the browser's built-in TTS — only used in the text-only path
// (the real voice loop streams Piper/Kokoro audio). Tuned calmer and warmer than the
// default, and prefers a natural-sounding system voice when one is available.
function pickWarmVoice() {
  const voices = speechSynthesis.getVoices?.() || [];
  const want = ['Samantha', 'Karen', 'Moira', 'Google US English', 'Jenny', 'Aria'];
  for (const name of want) {
    const v = voices.find((x) => x.name.includes(name));
    if (v) return v;
  }
  return voices.find((x) => x.lang && x.lang.startsWith('en')) || null;
}

function speakAloud(text) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.95; // a touch slower — easier for a young child to follow
    u.pitch = 1.05; // gentle, not chipmunky
    const v = pickWarmVoice();
    if (v) u.voice = v;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  } catch (_) {
    /* speechSynthesis unavailable — the visual demo still works */
  }
}

// Conversation is bound to whoever the camera currently recognizes.
let sessionId = null;
let currentPersonId = null;
let requestGreeting = null; // set to voice.greet once the WS client is wired
let requestIntro = null; // set to voice.intro — used for unrecognized new faces
let introduced = false; // have we introduced to the current unknown face?
const greetedIds = new Set(); // people greeted this page-load (greet each at most once)
let noFaceTicks = 0; // consecutive empty frames (debounce "the face left")
let lastInteraction = 0; // ms timestamp of the last user action

// The camera must never talk over an active conversation: skip auto greet/intro for a
// while after the child speaks or types.
const INTERACTION_QUIET_MS = 20000;
function markInteraction() {
  lastInteraction = Date.now();
}

async function sendText(text) {
  if (!text.trim()) return;
  markInteraction();
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

// --- Vision: camera, recognition, and enrollment, wired into the conversation. ---

let enrolling = false; // pause recognition while capturing an enrollment

// Open the camera and return a frame grabber, or null if unavailable/denied.
async function startCamera() {
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
    return null; // no camera / denied — chat still works without it
  }
  return () => {
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return null;
    canvas.width = w;
    canvas.height = h;
    canvas.getContext('2d').drawImage(video, 0, 0, w, h);
    return canvas.toDataURL('image/jpeg').split(',')[1];
  };
}

// Bind the conversation to a person (their session = their memory). With greet=true,
// Buddy also says hello out loud; recognition passes greet=false to rebind quietly.
async function bindPerson(personId, name, greet = true) {
  if (personId === currentPersonId) return;
  currentPersonId = personId;
  const who = name || 'friend';
  try {
    const s = await postJSON('/session/start', { person_id: personId }).then((r) => r.json());
    sessionId = s.session_id;
    if (!greet) return;
    resetSleepy();
    markInteraction(); // the greeting itself counts as activity — don't immediately re-fire
    if (requestGreeting) {
      // Buddy speaks the greeting in its real voice (uses memory server-side).
      caption.textContent = `Hi ${who}!`;
      requestGreeting(sessionId);
    } else {
      // No voice channel — fall back to a visual greeting.
      caption.textContent = s.resume_summary
        ? `Hi ${who}! ${s.resume_summary}`
        : `Hi ${who}! So good to see you!`;
      buddy.toSpeaking('celebrating');
      setTimeout(() => buddy.toIdle(), 1500);
    }
  } catch (_) {
    /* recognition is best-effort; chat continues regardless */
  }
}

// The green enroll button: capture a few frames → create person → consent → enroll.
function addEnrollButton(grabFrame) {
  const btn = document.createElement('button');
  btn.textContent = '📸 Enroll my face';
  btn.style.cssText =
    'position:absolute;top:16px;left:18px;border:none;border-radius:12px;' +
    'padding:10px 14px;font:inherit;font-weight:800;color:#fff;background:#22c55e;' +
    'cursor:pointer;z-index:10;';
  btn.addEventListener('click', async () => {
    const probe = grabFrame();
    if (!probe) return;
    // Already enrolled? Recognize first so we greet instead of making a duplicate.
    try {
      const r = await postJSON('/recognize', { image: probe }).then((x) => x.json());
      if (r.matched) {
        caption.textContent = `I already know you, ${r.display_name || 'friend'}!`;
        currentPersonId = null; // re-greet
        greetedIds.add(r.person_id);
        await bindPerson(r.person_id, r.display_name);
        return;
      }
    } catch (_) {
      /* fall through to enrollment */
    }
    const name = prompt("I don't know you yet — what's your name?", '');
    if (!name) return;
    const role = confirm(`Is ${name} a grown-up?\n\nOK = parent · Cancel = child`)
      ? 'parent'
      : 'child';
    enrolling = true;
    btn.disabled = true;
    caption.textContent = `Capturing ${name}…`;
    const images = [];
    for (let i = 0; i < 3; i++) {
      const f = grabFrame();
      if (f) images.push(f);
      await new Promise((r) => setTimeout(r, 400));
    }
    try {
      if (!images.length) {
        caption.textContent = 'No frame captured — try again.';
        return;
      }
      caption.textContent = `Enrolling ${name}…`;
      const person = await postJSON('/person', { display_name: name, role }).then((r) =>
        r.json()
      );
      await postJSON(`/person/${person.id}/consent`, { scope: 'face', granted: true });
      const res = await postJSON(`/person/${person.id}/enroll`, { images });
      if (res.status === 400) {
        caption.textContent = "I couldn't find a face — try again, well-lit and centered.";
      } else if (!res.ok) {
        caption.textContent = `Enroll failed (HTTP ${res.status}).`;
      } else {
        currentPersonId = null; // force a fresh greeting/bind for the new profile
        greetedIds.add(person.id);
        await bindPerson(person.id, name);
      }
    } catch (_) {
      caption.textContent = 'Enroll failed — is the backend running?';
    } finally {
      btn.disabled = false;
      enrolling = false;
    }
  });
  document.getElementById('stage').appendChild(btn);
}

// Poll recognition — but stay out of the way of the actual conversation. Recognition's
// only job is the FIRST hello: greet a known person once, introduce to an unknown face
// once. It never re-greets, never resets a bound person on a noisy no-match frame, and
// never fires while the child is talking or just interacted (recognition is jittery
// frame-to-frame, so without this it talks over you).
function startRecognitionLoop(grabFrame) {
  setInterval(async () => {
    if (enrolling) return;
    // Never interrupt an in-flight turn (listening/thinking/speaking)…
    if (buddy.state !== 'idle') return;
    // …nor for a quiet window after the child spoke or typed.
    if (Date.now() - lastInteraction < INTERACTION_QUIET_MS) return;

    const image = grabFrame();
    if (!image) return;
    try {
      const r = await postJSON('/recognize', { image }).then((resp) => resp.json());

      if (r.matched) {
        noFaceTicks = 0;
        introduced = false;
        if (r.person_id !== currentPersonId) {
          // Greet a person only the first time we see them this session; otherwise
          // just rebind their session quietly so chat uses their memory.
          const firstHello = !greetedIds.has(r.person_id);
          greetedIds.add(r.person_id);
          await bindPerson(r.person_id, r.display_name, firstHello);
        }
      } else if (r.face_present) {
        noFaceTicks = 0;
        // Someone unrecognized, and we're not already bound to a person → introduce once.
        if (!introduced && currentPersonId === null) {
          introduced = true;
          caption.textContent = "Hi! I'm Buddy. What's your name?";
          markInteraction();
          if (requestIntro) requestIntro();
        }
      } else if (++noFaceTicks >= 3) {
        // Face gone for a sustained stretch — allow a fresh intro when someone returns.
        introduced = false;
      }
    } catch (_) {
      /* keep trying on the next tick */
    }
  }, 3000);
}

async function setupVision() {
  const grabFrame = await startCamera();
  if (!grabFrame) return; // camera unavailable — chat-only is fine
  addEnrollButton(grabFrame);
  startRecognitionLoop(grabFrame);
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
  (function osc(now) {
    buddy.setAmplitude(0.4 + 0.4 * Math.abs(Math.sin((now || 0) / 220)));
    requestAnimationFrame(osc);
  })();
}

if (params.get('mock') === '1') {
  startMock();
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
    getSessionId: () => sessionId,
  });
  requestGreeting = voice.greet; // let recognition trigger a spoken greeting
  requestIntro = voice.intro; // …and a self-introduction for unknown faces
  const press = (e) => {
    e.preventDefault();
    markInteraction();
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

  if (KIOSK) {
    voice.open();
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') voice.open();
    });
  }

  // Camera recognition runs alongside the chat (best-effort; no-op if denied).
  setupVision();
}

// Register the PWA service worker (offline kiosk shell).
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/app/service-worker.js').catch(() => {});
}
