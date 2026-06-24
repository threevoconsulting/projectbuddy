// Audio pipeline — M4 (voice in/out). Placeholder documenting the intended seam.
//
// Planned responsibilities:
//   * mic capture via AudioWorklet, downsampled to 16 kHz mono PCM for STT;
//   * push-to-talk for v1 (energy-VAD / server-VAD later);
//   * a TTS playback queue that decodes base64 PCM chunks from the WS `audio` frames
//     and feeds live amplitude into BuddyState.setAmplitude() so the mouth tracks
//     the voice.
//
// Until M4 lands, the text demo in app.js simulates amplitude with an oscillator.

window.BuddyAudio = {
  ready: false,
  // start(onAmplitude) {}  // begin mic capture
  // playChunk(base64Pcm) {} // enqueue a TTS chunk
};
