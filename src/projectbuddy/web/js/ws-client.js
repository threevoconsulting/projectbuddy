// WebSocket client for /ws/converse — the realtime voice loop.
//
// Push-to-talk: hold the button → connect (once), stream mic audio up; release →
// send {type:"end"}. The server replies state→emotion→speaking→audio→final, which we
// map onto BuddyState so the face leads the voice. Frame shapes: protocol/ws.py.
//
// Robustness (M6): if the socket drops unexpectedly it auto-reconnects with
// exponential backoff (1s→2s→…→15s) and reports status via `onStatus` so the UI can
// show a gentle "reconnecting" cue. A clean shutdown (page close) does not reconnect.

window.BuddyWS = (function () {
  function connect(buddyState, { onCaption, onStatus, getSessionId } = {}) {
    let ws = null;
    let talking = false;
    let manualClose = false;
    let reconnectTimer = null;
    let backoff = 1000;
    const MAX_BACKOFF = 15000;

    function wsUrl() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      return `${proto}://${location.host}/ws/converse`;
    }

    function scheduleReconnect() {
      if (reconnectTimer || manualClose) return;
      if (onStatus) onStatus('reconnecting');
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        ensureSocket().catch(() => {}); // failure re-triggers onclose → reschedule
      }, backoff);
      backoff = Math.min(MAX_BACKOFF, backoff * 2);
    }

    function ensureSocket() {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        return Promise.resolve();
      }
      return new Promise((resolve, reject) => {
        ws = new WebSocket(wsUrl());
        ws.onmessage = (e) => handleFrame(JSON.parse(e.data));
        ws.onopen = () => {
          backoff = 1000; // recovered — reset the backoff
          if (onStatus) onStatus('connected');
          resolve();
        };
        ws.onerror = (err) => reject(err);
        ws.onclose = () => {
          if (!manualClose) scheduleReconnect();
        };
      });
    }

    function handleFrame(frame) {
      switch (frame.type) {
        case 'state':
          if (frame.value === 'thinking') buddyState.toThinking();
          else if (frame.value === 'listening') {
            // Server is ready for the next utterance. Show listening only while the
            // mic is actually open (push-to-talk); otherwise rest at idle.
            if (talking) buddyState.toListening();
            else buddyState.toIdle();
          }
          // 'speaking' needs no action here: the emotion frame already entered the
          // speaking state (face leads the voice).
          break;
        case 'emotion':
          buddyState.toSpeaking(frame.value); // face leads the voice
          break;
        case 'audio':
          window.BuddyAudio.playChunk(frame.chunk, (a) => buddyState.setAmplitude(a));
          break;
        case 'final':
          if (onCaption) onCaption(frame.say);
          break;
      }
    }

    async function startTalking() {
      if (talking) return;
      talking = true;
      try {
        await ensureSocket();
      } catch (err) {
        talking = false;
        if (onStatus) onStatus('reconnecting');
        scheduleReconnect();
        return;
      }
      // Bind this utterance to the recognized person's session, if any, so the brain
      // uses their memory. With no session (nobody recognized) the server keeps its
      // own continuity for the default profile.
      const sid = getSessionId ? getSessionId() : null;
      if (sid && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'start', session_id: sid }));
      }
      window.BuddyAudio.resetPlayback();
      buddyState.toListening();
      try {
        await window.BuddyAudio.startCapture((chunk) => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'audio', chunk }));
          }
        });
      } catch (err) {
        talking = false;
        buddyState.toSpeaking('confused');
        if (onCaption) onCaption("I can't hear my microphone. Can you let me listen?");
      }
    }

    function stopTalking() {
      if (!talking) return;
      talking = false;
      window.BuddyAudio.stopCapture();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'end' }));
      }
    }

    // Proactively open the socket (used by the always-on kiosk so it shows a live
    // connection state even before the first utterance).
    function open() {
      return ensureSocket().catch(() => {});
    }

    // Ask Buddy to greet a just-recognized person out loud (M8). Streams a greeting
    // turn back over the same socket (emotion → speaking → audio → final).
    async function greet(sessionId) {
      try {
        await ensureSocket();
      } catch (_) {
        return;
      }
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'hello', session_id: sessionId ?? null }));
      }
    }

    // Ask Buddy to introduce itself to an unrecognized new face (M9). No session.
    async function intro() {
      try {
        await ensureSocket();
      } catch (_) {
        return;
      }
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'intro' }));
      }
    }

    function close() {
      manualClose = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    }

    return { startTalking, stopTalking, open, close, greet, intro };
  }

  return { connect };
})();
