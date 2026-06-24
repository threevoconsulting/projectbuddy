// WebSocket client for /ws/converse — M4 (voice loop). Placeholder documenting the seam.
//
// Planned responsibilities:
//   * connect with auto-reconnect to /ws/converse;
//   * stream mic audio frames up;
//   * dispatch server frames to BuddyState:
//       {type:state}   → toListening()/toThinking()
//       {type:emotion} → toSpeaking(value)        (face leads the voice)
//       {type:audio}   → BuddyAudio.playChunk(chunk)
//       {type:final}   → caption + return to idle
//
// The frame shapes are defined in src/projectbuddy/protocol/ws.py.

window.BuddyWS = {
  // connect(buddyState) {}
};
