// Tiny REST wrapper for the parent app. All endpoints already exist on the backend.
window.ParentAPI = (() => {
  const json = async (method, url, body) => {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error(`${method} ${url} → ${r.status}`);
    return r.status === 204 ? null : r.json();
  };

  return {
    listPeople: () => json('GET', '/person'),
    createPerson: (display_name, role) => json('POST', '/person', { display_name, role }),
    updatePerson: (id, display_name, role) => json('PUT', `/person/${id}`, { display_name, role }),
    deletePerson: (id) => json('DELETE', `/person/${id}`),
    stats: (id) => json('GET', `/person/${id}/stats`),
    sessions: (id) => json('GET', `/person/${id}/sessions`),
    messages: (sid) => json('GET', `/session/${sid}/messages`),
    facts: (id) => json('GET', `/person/${id}/facts`),
    deleteFact: (id, fid) => json('DELETE', `/person/${id}/facts/${fid}`),
    consent: (id) => json('GET', `/person/${id}/consent`),
    setConsent: (id, granted) =>
      json('POST', `/person/${id}/consent`, { scope: 'face', granted }),
    runRetention: () => json('POST', '/retention/run'),
  };
})();
