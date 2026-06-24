// Buddy face — the expression engine, ported from the design mockup's `emotionMeta`.
// Pure function of (state, amplitude): given an emotion/state name and an optional
// audio amplitude (0..1, drives the mouth while speaking), it sets the SVG geometry.
// No framework, no build step — runs unchanged in a browser or a Pi Chromium kiosk.

// "Boop" face geometry. The eight protocol emotions plus the transient UI states
// `listening` and `thinking`. Numbers carried over from the mockup; `sad` added to
// complete the protocol's eight emotions.
const META = {
  happy:       { label: 'Happy',       lRY: 28, rRY: 28, lPCY: 88, rPCY: 88, lHO: 0.9, rHO: 0.9, mouth: 'M 68 140 Q 100 162 132 140', rotate: 0,  blush: 0.42, sparkle: false, anim: 'buddyBob 3s ease-in-out infinite' },
  curious:     { label: 'Curious',     lRY: 34, rRY: 20, lPCY: 86, rPCY: 88, lHO: 0.9, rHO: 0.9, mouth: 'M 80 140 Q 100 152 118 134', rotate: -8, blush: 0.18, sparkle: false, anim: 'buddyBob 4s ease-in-out infinite' },
  thinking:    { label: 'Thinking',    lRY: 10, rRY: 10, lPCY: 85, rPCY: 85, lHO: 0.3, rHO: 0.3, mouth: 'M 80 140 Q 100 146 118 136', rotate: 5,  blush: 0.06, sparkle: false, anim: 'buddySlowBob 5s ease-in-out infinite' },
  excited:     { label: 'Excited',     lRY: 32, rRY: 32, lPCY: 86, rPCY: 86, lHO: 0.9, rHO: 0.9, mouth: 'M 56 132 Q 100 176 144 132', rotate: 0,  blush: 0.78, sparkle: true,  anim: 'buddyBounce 0.5s ease-in-out infinite' },
  listening:   { label: 'Listening',   lRY: 24, rRY: 24, lPCY: 88, rPCY: 88, lHO: 0.9, rHO: 0.9, mouth: 'M 76 140 Q 100 154 124 140', rotate: -4, blush: 0.26, sparkle: false, anim: 'buddyLean 2.5s ease-in-out infinite' },
  confused:    { label: 'Confused',    lRY: 18, rRY: 28, lPCY: 90, rPCY: 86, lHO: 0.9, rHO: 0.9, mouth: 'M 74 140 Q 88 130 104 142 Q 116 150 130 136', rotate: 7, blush: 0.04, sparkle: false, anim: 'buddyShake 1.8s ease-in-out infinite' },
  sleepy:      { label: 'Sleepy',      lRY: 4,  rRY: 4,  lPCY: 88, rPCY: 88, lHO: 0.0, rHO: 0.0, mouth: 'M 82 140 Q 100 148 118 140', rotate: 4,  blush: 0.07, sparkle: false, anim: 'buddyDroop 4s ease-in-out infinite' },
  sad:         { label: 'Sad',         lRY: 20, rRY: 20, lPCY: 92, rPCY: 92, lHO: 0.5, rHO: 0.5, mouth: 'M 72 150 Q 100 134 128 150', rotate: 0,  blush: 0.10, sparkle: false, anim: 'buddyDroop 4.5s ease-in-out infinite' },
  celebrating: { label: 'Celebrating', lRY: 32, rRY: 32, lPCY: 84, rPCY: 84, lHO: 0.9, rHO: 0.9, mouth: 'M 50 132 Q 100 182 150 132', rotate: 0,  blush: 0.9,  sparkle: true,  anim: 'buddyBigBounce 0.4s ease-in-out infinite' },
};

// The eight emotions the backend can send (UI states `listening`/`thinking` excluded).
const EMOTIONS = ['happy', 'curious', 'thinking', 'excited', 'confused', 'sleepy', 'sad', 'celebrating'];

const $ = (id) => document.getElementById(id);

function render(state, amplitude = 0) {
  const m = META[state] || META.happy;

  // Derived iris + pupil radii (kept inside the sclera), as in the mockup.
  const lIris = Math.max(2, Math.round(m.lRY * 0.68));
  const rIris = Math.max(2, Math.round(m.rRY * 0.68));
  const lPupil = Math.max(1, Math.round(m.lRY * 0.40));
  const rPupil = Math.max(1, Math.round(m.rRY * 0.40));

  $('eye-l-sclera').setAttribute('ry', m.lRY);
  $('eye-r-sclera').setAttribute('ry', m.rRY);
  $('eye-l-iris').setAttribute('ry', lIris);
  $('eye-r-iris').setAttribute('ry', rIris);
  $('eye-l-pupil').setAttribute('ry', lPupil);
  $('eye-r-pupil').setAttribute('ry', rPupil);
  $('eye-l-pupil').setAttribute('cy', m.lPCY);
  $('eye-r-pupil').setAttribute('cy', m.rPCY);
  $('eye-l-light').setAttribute('opacity', m.lHO);
  $('eye-r-light').setAttribute('opacity', m.rHO);
  $('blush-l').setAttribute('opacity', m.blush);
  $('blush-r').setAttribute('opacity', m.blush);
  $('mouth').setAttribute('d', m.mouth);
  $('head').setAttribute('transform', `rotate(${m.rotate}, 100, 100)`);
  $('sparkles').style.opacity = m.sparkle ? 1 : 0;
  $('face').style.animation = m.anim;

  // Amplitude opens the mouth a little while Buddy speaks (M4 feeds real audio).
  const amp = Math.max(0, Math.min(1, amplitude));
  const mouth = $('mouth');
  mouth.style.transformBox = 'fill-box';
  mouth.style.transformOrigin = 'center';
  mouth.style.transform = `scaleY(${1 + amp * 0.8})`;

  $('thinking-dots').classList.toggle('active', state === 'thinking');
  $('listening-ring').classList.toggle('active', state === 'listening');
  $('emotion-label').textContent = m.label;
}

window.BuddyFace = { render, EMOTIONS, META };
