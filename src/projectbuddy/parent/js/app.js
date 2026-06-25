// Parent companion app (M9): a small hash-routed SPA over the existing REST API.
// Screens: Welcome, Dashboard, Sessions, Conversation, Memory, Profile.

const screen = document.getElementById('screen');
const tabs = document.getElementById('tabs');
const select = document.getElementById('person-select');
const API = window.ParentAPI;

let people = [];
let currentId = null;

const esc = (s) =>
  String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const fmt = (ts) => (ts ? esc(String(ts).replace('T', ' ').slice(0, 16)) : '—');
const go = (route) => {
  location.hash = `#/${route}`;
};

async function loadPeople() {
  people = await API.listPeople();
  select.innerHTML =
    '<option value="">— pick —</option>' +
    people.map((p) => `<option value="${p.id}">${esc(p.display_name)}</option>`).join('');
  if (currentId) select.value = String(currentId);
}

select.addEventListener('change', () => {
  currentId = select.value ? Number(select.value) : null;
  go(currentId ? 'dashboard' : 'welcome');
});

function setTabs(active) {
  tabs.hidden = currentId == null;
  [...tabs.querySelectorAll('a')].forEach((a) =>
    a.classList.toggle('active', a.dataset.route === active)
  );
}

// --- Screens -------------------------------------------------------------

async function welcome() {
  setTabs(null);
  const cards = people
    .map(
      (p) =>
        `<div class="row click" data-pick="${p.id}"><div><div>${esc(p.display_name)}</div>
         <div class="sub">${esc(p.role || 'child')}</div></div><button>Open →</button></div>`
    )
    .join('');
  screen.innerHTML = `
    <h1>Welcome</h1>
    <p class="muted">Pick a child to see what Buddy remembers, or add a new one.</p>
    <div class="list">${cards || '<div class="empty">No children yet.</div>'}</div>
    <h2>Add a child</h2>
    <div class="card">
      <div class="field"><label>Name</label><input id="w-name" placeholder="e.g. Emma" /></div>
      <div class="field"><label>Role</label><input id="w-role" value="child" /></div>
      <div class="actions"><button class="primary" id="w-add">Add child</button></div>
    </div>`;
  screen.querySelectorAll('[data-pick]').forEach((r) =>
    r.addEventListener('click', () => {
      currentId = Number(r.dataset.pick);
      select.value = String(currentId);
      go('dashboard');
    })
  );
  screen.querySelector('#w-add').addEventListener('click', async () => {
    const name = screen.querySelector('#w-name').value.trim();
    if (!name) return;
    const p = await API.createPerson(name, screen.querySelector('#w-role').value.trim() || null);
    await loadPeople();
    currentId = p.id;
    select.value = String(currentId);
    go('dashboard');
  });
}

async function dashboard() {
  setTabs('dashboard');
  const s = await API.stats(currentId);
  const stat = (n, l) => `<div class="card stat"><div class="num">${n}</div><div class="label">${l}</div></div>`;
  screen.innerHTML = `
    <h1>${esc(personName())}</h1>
    <div class="grid cards">
      ${stat(s.session_count, 'Sessions')}
      ${stat(s.message_count, 'Messages')}
      ${stat(s.fact_count, 'Things remembered')}
    </div>
    <h2>Status</h2>
    <div class="list">
      <div class="row"><span>Last seen</span><span class="sub">${fmt(s.last_seen_at)}</span></div>
      <div class="row"><span>First met</span><span class="sub">${fmt(s.created_at)}</span></div>
      <div class="row"><span>Face enrolled</span>${pill(s.face_enrolled)}</div>
      <div class="row"><span>Face consent</span>${pill(s.face_consent)}</div>
    </div>`;
}

async function sessions() {
  setTabs('sessions');
  const list = await API.sessions(currentId);
  const rows = list
    .map(
      (s) =>
        `<div class="row click" data-sid="${s.id}"><div><div>${fmt(s.started_at)}</div>
         <div class="sub">${esc(s.summary || (s.ended_at ? 'No summary' : 'In progress…'))}</div></div>
         <button>View →</button></div>`
    )
    .join('');
  screen.innerHTML = `<h1>Sessions</h1>
    <div class="list">${rows || '<div class="empty">No sessions yet.</div>'}</div>`;
  screen.querySelectorAll('[data-sid]').forEach((r) =>
    r.addEventListener('click', () => go(`session/${r.dataset.sid}`))
  );
}

async function conversation(sid) {
  setTabs('sessions');
  const msgs = await API.messages(sid);
  const bubbles = msgs
    .map(
      (m) =>
        `<div class="bubble ${m.role === 'child' ? 'child' : 'buddy'}">
          <div class="who">${m.role === 'child' ? 'Child' : 'Buddy'}${
            m.emotion ? ' · ' + esc(m.emotion) : ''
          }</div>${esc(m.text)}</div>`
    )
    .join('');
  screen.innerHTML = `
    <h1>Conversation</h1>
    <div class="actions"><button id="back">← Sessions</button></div>
    <div class="list" style="margin-top:14px">${
      bubbles || '<div class="empty">No messages in this session.</div>'
    }</div>`;
  screen.querySelector('#back').addEventListener('click', () => go('sessions'));
}

async function memory() {
  setTabs('memory');
  const facts = await API.facts(currentId);
  const rows = facts
    .map(
      (f) =>
        `<div class="row"><div><div>${esc(f.key)}</div><div class="sub">${esc(f.value)}</div></div>
         <button class="danger" data-fid="${f.id}">Forget</button></div>`
    )
    .join('');
  screen.innerHTML = `
    <h1>Memory</h1>
    <p class="muted">Everything Buddy remembers about ${esc(personName())}. Delete anything, anytime.</p>
    <div class="list">${rows || '<div class="empty">Buddy hasn\\'t remembered anything yet.</div>'}</div>`;
  screen.querySelectorAll('[data-fid]').forEach((b) =>
    b.addEventListener('click', async () => {
      await API.deleteFact(currentId, Number(b.dataset.fid));
      memory();
    })
  );
}

async function profile() {
  setTabs('profile');
  const p = people.find((x) => x.id === currentId);
  const consents = await API.consent(currentId).catch(() => []);
  const face = consents.find((c) => c.scope === 'face');
  const granted = !!(face && face.granted);
  screen.innerHTML = `
    <h1>Profile</h1>
    <div class="card">
      <div class="field"><label>Name</label><input id="p-name" value="${esc(p ? p.display_name : '')}" /></div>
      <div class="field"><label>Role</label><input id="p-role" value="${esc(p ? p.role || '' : '')}" /></div>
      <div class="actions"><button class="primary" id="p-save">Save</button></div>
    </div>
    <h2>Face recognition consent</h2>
    <div class="card">
      <div class="row"><span>Face consent</span>${pill(granted)}</div>
      <div class="actions">
        <button id="p-consent">${granted ? 'Revoke consent (deletes face data)' : 'Grant consent'}</button>
        <button id="p-retention">Run retention now</button>
      </div>
    </div>
    <h2>Danger zone</h2>
    <div class="card">
      <p class="muted">Forget ${esc(personName())} completely — deletes all chats, memory, and face data.</p>
      <div class="actions"><button class="danger" id="p-delete">Delete child</button></div>
    </div>`;
  screen.querySelector('#p-save').addEventListener('click', async () => {
    const name = screen.querySelector('#p-name').value.trim();
    if (!name) return;
    await API.updatePerson(currentId, name, screen.querySelector('#p-role').value.trim() || null);
    await loadPeople();
    dashboard();
  });
  screen.querySelector('#p-consent').addEventListener('click', async () => {
    await API.setConsent(currentId, !granted);
    profile();
  });
  screen.querySelector('#p-retention').addEventListener('click', async () => {
    const r = await API.runRetention();
    alert(`Retention sweep done. Deleted face data for ${r.deleted_person_ids.length} child(ren).`);
  });
  screen.querySelector('#p-delete').addEventListener('click', async () => {
    if (!confirm(`Delete ${personName()} and all their data? This cannot be undone.`)) return;
    await API.deletePerson(currentId);
    currentId = null;
    await loadPeople();
    go('welcome');
  });
}

// --- helpers + router ----------------------------------------------------

const pill = (on) => `<span class="pill ${on ? 'on' : 'off'}">${on ? 'Yes' : 'No'}</span>`;
const personName = () => {
  const p = people.find((x) => x.id === currentId);
  return p ? p.display_name : 'Child';
};

async function render() {
  const parts = (location.hash.replace(/^#\//, '') || 'welcome').split('/');
  const route = parts[0];
  try {
    if (route !== 'welcome' && currentId == null) return welcome();
    if (route === 'dashboard') return await dashboard();
    if (route === 'sessions') return await sessions();
    if (route === 'session') return await conversation(parts[1]);
    if (route === 'memory') return await memory();
    if (route === 'profile') return await profile();
    return await welcome();
  } catch (err) {
    screen.innerHTML = `<div class="empty">Something went wrong loading this screen.<br /><span class="muted">${esc(
      err.message
    )}</span></div>`;
  }
}

window.addEventListener('hashchange', render);

(async function init() {
  await loadPeople();
  if (people.length === 1) {
    currentId = people[0].id;
    select.value = String(currentId);
  }
  render();
})();
