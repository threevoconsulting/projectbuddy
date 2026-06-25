// Wiring for the Phase-1 text demo + the mock harness.
//
//   /app/            → type to Buddy; backend returns {emotion, say}, face reacts.
//   /app/?mock=1     → cycle all 8 emotions with a fake amplitude oscillator
//                      (no backend / no models needed — pure face QA).
//   /app/?kiosk=1    → hide the text controls (robot-screen layout).
//
// Voice in/out (M4) will replace the text input with mic capture + streamed TTS,
// reusing the same BuddyState transitions.

const params = new URLSearchParams(location.search);
const buddy = new BuddyState(window.BuddyFace.render);
const caption = document.getElementById('caption');

if (params.get('kiosk') === '1') document.body.classList.add('kiosk');

buddy.toIdle();
caption.textContent = "Hi! I'm Buddy. Talk to me!";

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
      // Pseudo-random mouth movement; M4 replaces this with real TTS amplitude.
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

// --- Mock harness: cycle every emotion + oscillate amplitude, no backend ---
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

if (params.get('mock') === '1') {
  startMock();
} else {
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

  // --- Voice (M4): hold the mic button to talk; release to let Buddy reply. ---
  const talkBtn = document.getElementById('talk-btn');
  const voice = window.BuddyWS.connect(buddy, {
    onCaption: (say) => {
      caption.textContent = say;
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
}

// Register the PWA service worker (offline kiosk shell).
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/app/service-worker.js').catch(() => {});
}
