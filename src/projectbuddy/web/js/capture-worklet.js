// AudioWorklet processor for mic capture (M4). Posts mono Float32 frames from the
// audio thread to the main thread, which downsamples to 16 kHz Int16 PCM for STT.
// A static module (no build step) so it runs unchanged in a Pi Chromium kiosk.

class BuddyCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      // Copy channel 0 — the underlying buffer is reused by the engine.
      this.port.postMessage(input[0].slice(0));
    }
    return true; // keep the processor alive
  }
}

registerProcessor('buddy-capture', BuddyCaptureProcessor);
