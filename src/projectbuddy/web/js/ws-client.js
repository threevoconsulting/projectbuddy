// WebSocket client for /ws/converse — M4 (the realtime voice loop).
//
// Push-to-talk: hold the button → connect (once), stream mic audio up; release →
// send {type:"end"}. The server replies state→emotion→audio→final, which we map onto
// BuddyState so the face leads the voice. Frame shapes: protocol/ws.py.

window.BuddyWS = (function () {
  function connect(buddyState, { onCaption } = {}) {
    let ws = null;
    let talking = false;

    function wsUrl() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      return `${proto}://${location.host}/ws/converse`;
    }

    function ensureSocket() {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        return Promise.resolve();
      }
      ws = new WebSocket(wsUrl());
      ws.onmessage = (e) => handleFrame(JSON.parse(e.data));
      return new Promise((resolve, reject) => {
        ws.onopen = resolve;
        ws.onerror = reject;
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
      await ensureSocket();
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

    return { startTalking, stopTalking };
  }

  return { connect };
})();
