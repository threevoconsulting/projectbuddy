// Audio pipeline — M4 (voice in/out). No build step; runs in a browser or Pi kiosk.
//
//   * startCapture(onChunk): mic → AudioWorklet → 16 kHz mono Int16 PCM, base64-encoded
//     chunks handed to onChunk (sent up the WebSocket as {type:"audio"}).
//   * playChunk(base64, onAmplitude): decode a streamed TTS chunk, schedule it
//     gaplessly, and report its amplitude (0..1) so the mouth tracks the voice.
//   * resetPlayback(): start a fresh playback timeline for a new turn.
//
// Sample rates are the contract with the backend seams (models/stt, models/tts).

window.BuddyAudio = (function () {
  const STT_RATE = 16000; // must match models/stt/base.py SAMPLE_RATE
  const TTS_RATE = 22050; // must match models/tts/base.py SAMPLE_RATE

  let captureCtx = null;
  let workletNode = null;
  let sourceNode = null;
  let mediaStream = null;
  let captureAcc = []; // pending 16 kHz Int16 samples, flushed in ~100 ms chunks
  let captureSink = null; // onChunk callback for the active capture

  let playCtx = null;
  let nextStartTime = 0;

  function int16ToBase64(int16) {
    const bytes = new Uint8Array(int16.buffer, int16.byteOffset, int16.byteLength);
    let bin = '';
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  }

  function base64ToInt16(b64) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new Int16Array(bytes.buffer);
  }

  const FLUSH_SAMPLES = STT_RATE / 10; // ~100 ms of 16 kHz audio per WS chunk

  function flushCapture(force) {
    if (!captureSink) return;
    while (captureAcc.length >= FLUSH_SAMPLES) {
      captureSink(int16ToBase64(Int16Array.from(captureAcc.splice(0, FLUSH_SAMPLES))));
    }
    if (force && captureAcc.length) {
      captureSink(int16ToBase64(Int16Array.from(captureAcc.splice(0))));
    }
  }

  async function startCapture(onChunk) {
    captureSink = onChunk;
    captureAcc = [];
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    // Ask for a 16 kHz context so the browser resamples cleanly (proper anti-alias
    // filter); fall back to the hardware rate + an averaging downsample if it won't.
    try {
      captureCtx = new AudioContext({ sampleRate: STT_RATE });
    } catch (_) {
      captureCtx = new AudioContext();
    }
    await captureCtx.audioWorklet.addModule('/app/js/capture-worklet.js');
    sourceNode = captureCtx.createMediaStreamSource(mediaStream);
    workletNode = new AudioWorkletNode(captureCtx, 'buddy-capture');

    const ratio = captureCtx.sampleRate / STT_RATE; // ~1 if the context honored 16 kHz
    let carry = 0; // fractional read position carried across render quanta
    workletNode.port.onmessage = (e) => {
      const input = e.data; // Float32Array at captureCtx.sampleRate
      if (ratio <= 1.01) {
        for (let i = 0; i < input.length; i++) {
          captureAcc.push(Math.max(-1, Math.min(1, input[i])) * 32767);
        }
      } else {
        // Average each source window into one output sample (basic anti-aliasing).
        let pos = carry;
        while (pos < input.length) {
          const start = Math.floor(pos);
          const end = Math.min(input.length, Math.max(start + 1, Math.floor(pos + ratio)));
          let sum = 0;
          for (let j = start; j < end; j++) sum += input[j];
          const v = sum / (end - start);
          captureAcc.push(Math.max(-1, Math.min(1, v)) * 32767);
          pos += ratio;
        }
        carry = pos - input.length;
      }
      flushCapture(false);
    };

    sourceNode.connect(workletNode);
    // Some browsers only run a worklet that reaches the destination; route through
    // a silent gain so capture runs without echoing the mic to the speakers.
    const sink = captureCtx.createGain();
    sink.gain.value = 0;
    workletNode.connect(sink);
    sink.connect(captureCtx.destination);
  }

  function stopCapture() {
    flushCapture(true); // send the trailing <100 ms so the last word isn't clipped
    if (sourceNode) sourceNode.disconnect();
    if (workletNode) workletNode.disconnect();
    if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
    if (captureCtx) captureCtx.close();
    captureCtx = workletNode = sourceNode = mediaStream = null;
    captureSink = null;
    captureAcc = [];
  }

  function resetPlayback() {
    if (!playCtx) playCtx = new AudioContext();
    nextStartTime = 0;
  }

  function playChunk(b64, onAmplitude) {
    if (!playCtx) playCtx = new AudioContext();
    const pcm = base64ToInt16(b64);
    if (pcm.length === 0) return;

    const f32 = new Float32Array(pcm.length);
    let sumSq = 0;
    for (let i = 0; i < pcm.length; i++) {
      const v = pcm[i] / 32768;
      f32[i] = v;
      sumSq += v * v;
    }
    const rms = Math.sqrt(sumSq / pcm.length);

    const buf = playCtx.createBuffer(1, f32.length, TTS_RATE);
    buf.copyToChannel(f32, 0);
    const src = playCtx.createBufferSource();
    src.buffer = buf;
    src.connect(playCtx.destination);

    const now = playCtx.currentTime;
    if (nextStartTime < now) nextStartTime = now;
    src.start(nextStartTime);

    const durMs = (f32.length / TTS_RATE) * 1000;
    const delayMs = Math.max(0, (nextStartTime - now) * 1000);
    if (onAmplitude) {
      setTimeout(() => onAmplitude(Math.min(1, rms * 3)), delayMs);
      setTimeout(() => onAmplitude(0), delayMs + durMs);
    }
    nextStartTime += f32.length / TTS_RATE;
  }

  return { startCapture, stopCapture, resetPlayback, playChunk };
})();
