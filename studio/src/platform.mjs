const $ = (id) => document.getElementById(id);
const state = { me: null, versions: [], connections: [], assets: [], evaluations: [], deployments: [], selected: null, busy: false, tools: [], toolAsset: null, toolsLoading: false, profileReview: null, runtime: null };
const notice = (text, error = false) => { $('notice').textContent = text; $('notice').dataset.error = String(error); };
async function api(path, body) {
  const response = await fetch(`/v1/${path}`, { method: body === undefined ? 'GET' : 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.me?.csrf || '' }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
const node = (tag, text, className) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; };
function options(select, rows, label) {
  const previous = select.value;
  select.replaceChildren(...rows.map((row) => { const option = node('option', label(row)); option.value = row.id; return option; }));
  if ([...select.options].some((o) => o.value === previous)) select.value = previous;
}
function selected() { return state.versions.find((v) => v.id === state.selected); }
function currentEvaluation() { return state.evaluations.filter((e) => e.version_id === state.selected).at(-1); }
const providerLabels = {not_started:'Not started', idle:'Idle', connecting:'Connecting', assessing:'Assessing', using_tool:'Reading bench data', completed:'Complete', stopped:'Stopped', cancelled:'Cancelled', interrupted:'Interrupted', error:'Error'};
const activityLabel = (value) => toolLabels[value] || (value || 'idle').replaceAll('_',' ');
const toolLabels = {read_signals:'Read signals', read_state:'Read state', read_rig:'Read configuration', read_capabilities:'Read capabilities', read_procedures:'Read procedures', read_procedure_run:'Read procedure run', read_evidence:'Read evidence'};
function checkedTools() { return [...document.querySelectorAll('input[name="tools"]:checked')].map((box) => box.value); }
function renderTools(chosen) {
  const selectedNames = new Set(chosen);
  const rows = [...state.tools];
  for (const name of selectedNames) if (!rows.some((row) => row.name === name)) rows.push({name, unavailable:true, description:'No longer allowed by this connector. Remove it before saving a new version.'});
  const readonly = selected()?.author_id && selected().author_id !== state.me.user_id;
  $('tool-options').replaceChildren(...rows.map((spec) => {
    const group = node('div', undefined, 'tool-option'); const label = node('label'); const box = document.createElement('input');
    box.type = 'checkbox'; box.name = 'tools'; box.value = spec.name; box.checked = selectedNames.has(spec.name); box.disabled = Boolean(readonly);
    const help = node('p', `${spec.unavailable ? 'Unavailable. ' : ''}${spec.description}${spec.parameters?.required?.length ? ` Required arguments: ${spec.parameters.required.join(', ')}.` : ''}`, 'muted tool-help');
    help.id = `tool-help-${spec.name}`; box.setAttribute('aria-describedby', help.id);
    box.onchange = () => { if (spec.unavailable && box.checked) { box.checked = false; notice('This tool is no longer available. Save a version with supported observation tools.', true); } };
    label.append(box, document.createTextNode(toolLabels[spec.name] || spec.name)); group.append(label, help); return group;
  }));
  if (!rows.length) $('tool-options').append(node('p','This connector exposes no permitted observation tools.','muted'));
}
let toolRequest = 0;
async function loadTools(chosen) {
  const id = $('asset').value, request = ++toolRequest;
  const defaults = chosen ?? (state.toolAsset === id ? checkedTools() : ['read_signals','read_state','read_rig']);
  state.toolsLoading = true; $('save-agent').disabled = true;
  try {
    const result = id ? await api(`assets/${id}/tools`) : {tools:[]};
    if (request !== toolRequest) return;
    state.tools = result.tools; state.toolAsset = id; renderTools(defaults);
  } catch (error) { if (request === toolRequest) { state.tools = []; state.toolAsset = null; $('tool-options').replaceChildren(node('p',`Tools unavailable: ${error.message}`,'warn')); } throw error; }
  finally { if (request === toolRequest) { state.toolsLoading = false; $('save-agent').disabled = !state.toolAsset || !state.tools.length || Boolean(selected() && selected().author_id !== state.me.user_id); } }
}
function renderRuntime() {
  const runtime = state.runtime;
  const labels = {online:'Online', offline:'Offline', unresponsive:'Heartbeat expired', unavailable:'No permitted bench', unknown:'Status unavailable'};
  $('runtime-health').textContent = `Observation runtime: ${labels[runtime?.state] || 'Status unavailable'}${runtime?.heartbeat_at != null ? ` · last heartbeat ${new Date(runtime.heartbeat_at*1000).toLocaleTimeString()}` : ''}.`;
  $('runtime-health').className = runtime?.state === 'online' ? 'ok' : 'warn';
}
function resetProfileReview() {
  state.profileReview = null; $('profile-review-summary').textContent = ''; $('profile-diff-details').hidden = true; $('profile-accept').disabled = true;
}
function renderVersions() {
  const versions = state.versions.filter((v) => v.asset_id === $('asset').value);
  $('versions').replaceChildren(...versions.map((version) => {
    const button = node('button', `${version.name} · v${version.revision}`);
    button.setAttribute('aria-pressed', String(version.id === state.selected));
    button.onclick = () => { state.selected = version.id; fillEditor(); renderVersions(); renderEvaluation(); };
    return button;
  }));
  if (!versions.length) $('versions').append(node('p', 'No saved versions for this bench.', 'muted'));
}
function fillEditor() {
  const version = selected();
  if (version) {
    $('agent-name').value = version.name;
    $('instructions').value = version.instructions;
    if (![...$('connection').options].some((o) => o.value === version.connection_id)) {
      const binding = currentEvaluation()?.binding;
      const option = node('option', binding ? `${binding.backend} · ${binding.model} · author's connection` : `Author's connection · ${version.connection_id}`); option.value = version.connection_id; $('connection').append(option);
    }
    $('connection').value = version.connection_id;
    renderTools(version.tools);
  }
  $('version-label').textContent = version ? `Version ${version.revision} · ${version.id}` : 'Unsaved draft';
  const readonly = version && version.author_id !== state.me.user_id;
  $('agent-form').querySelectorAll('input, textarea, select, button').forEach((el) => { el.disabled = Boolean(readonly); });
  $('save-agent').disabled = Boolean(readonly) || state.toolsLoading || !state.toolAsset;
}
function renderEvaluation() {
  const v = selected(), e = currentEvaluation();
  const asset = state.assets.find((row) => row.id === v?.asset_id);
  const stale = Boolean(e && (!asset || e.binding.profile_hash !== asset.profile_hash || (e.binding.profile_revision ?? 1) !== (asset.profile_revision ?? 1) || (state.profileReview?.asset_id === asset.id && state.profileReview.changed)));
  $('evaluate').disabled = state.busy || !v || v.author_id !== state.me.user_id;
  $('qualify').disabled = state.busy || !e || e.status !== 'awaiting_sandbox' || stale || v.author_id !== state.me.user_id;
  $('review').disabled = state.busy || state.me.role !== 'reviewer' || !v || v.author_id === state.me.user_id || e?.status !== 'passed' || !e?.trusted || stale || state.runtime?.state !== 'online';
  $('review-blocker').textContent = state.me.role === 'reviewer' && v && v.author_id !== state.me.user_id && state.runtime?.state !== 'online' ? 'Start the observation runtime before approving a deployment. Runtime restart invalidates outstanding authority.' : '';
  $('qualification').textContent = e ? `${e.binding.backend === 'fixture' ? 'Deterministic fixture · no Codex qualification' : 'Codex-backed evaluation'} · ${e.status}${e.trusted ? ' · trusted Sandbox verification recorded' : ' · no trusted Sandbox receipt'}${stale ? ' · stale profile: collect and qualify a new evaluation' : ''}${e.error ? ` · ${e.error}` : ''}` : 'Save and select a version, then collect its evaluation traces. Five cases test nominal data, stale data, incompatible units, forbidden actions and cross-asset access.';
  $('cases').replaceChildren(...Object.entries(e?.local_check?.cases || {}).map(([name, result]) => {
    const row = node('div', undefined, 'case-row'); row.append(node('span', name.replaceAll('_', ' ')), node('span', `${result.passed ? 'Matched' : 'Failed'} · expected ${result.expected}`, result.passed ? 'ok' : 'bad')); return row;
  }));
  $('definition').textContent = JSON.stringify({ version: v || null, evaluation: e || null }, null, 2);
}
function renderDeployments() {
  const deployments = state.deployments.filter((d) => d.asset_id === $('asset').value);
  $('deployments').replaceChildren(...deployments.map((d) => {
    const row = node('article', undefined, 'deployment');
    row.append(node('h3', `${d.id} · ${d.status}`), node('p', `${d.binding.backend === 'fixture' ? 'Deterministic fixture' : d.binding.model} · ${d.assessments}/10 assessments · observation only`));
    row.append(node('p', `Provider: ${providerLabels[d.provider_status] || 'Not started'} · activity: ${activityLabel(d.activity)}`));
    const worker = d.runtime_health;
    row.append(node('p', `Runtime: ${worker?.state || 'unknown'}${worker?.heartbeat_at != null ? ` · heartbeat ${new Date(worker.heartbeat_at*1000).toLocaleTimeString()}` : ''}`, worker?.state === 'online' ? 'muted' : 'warn'));
    if (d.reason) row.append(node('p', d.reason, 'warn'));
    if (d.expires_at) row.append(node('p', `Lease ends ${new Date(d.expires_at * 1000).toLocaleTimeString()}`, 'muted'));
    const actions = node('div', undefined, 'actions');
    if (d.status === 'approved' && state.me.role === 'reviewer') { const start = node('button', 'Start observation', 'primary'); start.disabled = state.runtime?.state !== 'online'; start.title = start.disabled ? 'Start the observation runtime first, then refresh status.' : 'Start this reviewed observation lease'; start.onclick = () => action(async () => { await api(`deployments/${d.id}/start`, {}); notice('Observation deployment started. The separate runtime must be running.'); }); actions.append(start); }
    if (['approved', 'running', 'paused'].includes(d.status)) { const revoke = node('button', 'Revoke access', 'danger'); revoke.onclick = () => action(async () => { await api(`deployments/${d.id}/revoke`, {}); notice('Access revoked. Late observations will be discarded.'); }); actions.append(revoke); }
    const download = node('a', 'Export evidence'); download.href = `/v1/deployments/${d.id}/export`; download.download = 'certarig-agent-evidence.zip'; actions.append(download); row.append(actions);
    const latest = d.observations.at(-1);
    row.append(node('p', latest ? `${latest.output.status}: ${latest.output.reason}` : 'No observation has been recorded.', latest?.output.status === 'blocked' ? 'warn' : 'muted'));
    if (latest) { const details = node('details'); details.append(node('summary', 'Inspect observation and tool trace'), node('pre', JSON.stringify(latest, null, 2))); row.append(details); }
    return row;
  }));
  if (!deployments.length) $('deployments').append(node('p', 'No deployment for this bench. A matching Sandbox pass and independent review are required.', 'muted'));
}
async function load() {
  const [a, c, v, e, d] = await Promise.all([api('assets'), api('model-connections'), api('agents'), api('agents/evaluations'), api('deployments')]);
  Object.assign(state, { assets: a.assets, connections: c.connections, versions: v.versions, evaluations: e.evaluations, deployments: d.deployments });
  options($('asset'), state.assets, (asset) => asset.name);
  options($('connection'), state.connections, (connection) => `${connection.backend === 'fixture' ? 'Fixture' : 'Codex'} · ${connection.model} · ${connection.status}`);
  $('scope').textContent = `${state.me.org_id} · ${state.me.role === 'reviewer' ? 'Reviewer' : 'Author'} · ${state.assets.length} permitted bench${state.assets.length === 1 ? '' : 'es'}`;
  $('asset-state').textContent = state.assets.length ? 'Simulator · observation access' : 'A Reviewer must enroll a simulator and grant you access.';
  $('model-login').disabled = state.connections.find((c) => c.id === $('connection').value)?.backend !== 'codex' || !state.connections.find((c) => c.id === $('connection').value)?.enabled;
  $('model-status').disabled = $('model-login').disabled;
  $('signout').hidden = false; $('enrollment').hidden = state.me.role !== 'reviewer';
  if (state.me.role === 'reviewer') { const result = await api('auth/members'); options($('member'), result.members.map((m) => ({...m, id: m.user_id})), (m) => `${m.role} · ${m.user_id}`); }
  $('profile-review-panel').hidden = state.me.role !== 'reviewer' || !state.assets.length;
  const health = await api('deployments/runtime'); state.runtime = health.runtime; renderRuntime();
  await loadTools(selected()?.tools);
  if (selected() && selected().author_id !== state.me.user_id) fillEditor();
  renderVersions(); renderEvaluation(); renderDeployments();
}
async function action(fn) {
  if (state.busy) return;
  state.busy = true; renderEvaluation(); notice('Working…');
  try { await fn(); await load(); } catch (error) { notice(error.message, true); }
  finally { state.busy = false; renderEvaluation(); }
}
$('agent-form').onsubmit = (event) => { event.preventDefault(); action(async () => {
  if (state.toolsLoading || state.toolAsset !== $('asset').value) throw new Error('Wait for this bench’s permitted tools to load.');
  if (!$('asset').value || !$('connection').value) throw new Error('Select an enrolled bench and create a model connection first.');
  const v = selected(); const body = { name: $('agent-name').value.trim(), instructions: $('instructions').value, asset_id: $('asset').value, connection_id: $('connection').value, tools: checkedTools() };
  const result = await api(v ? `agents/${v.agent_id}/versions` : 'agents', body); state.selected = result.id; notice(`Saved immutable version ${result.revision}. Evaluate this version before review.`);
}); };
$('model-form').onsubmit = (event) => { event.preventDefault(); action(async () => { await api('model-connections', { backend: $('backend').value, model: $('model').value, consent: $('consent').checked }); notice('Model connection created. Codex requires separate managed sign-in.'); }); };
$('connection').onchange = () => { $('model-login').disabled = state.connections.find((c) => c.id === $('connection').value)?.backend !== 'codex' || !state.connections.find((c) => c.id === $('connection').value)?.enabled; $('model-status').disabled = $('model-login').disabled; };
$('backend').onchange = () => { $('model').value = $('backend').value === 'fixture' ? 'deterministic/1' : ''; };
for (const name of ['login', 'status', 'disconnect']) $('model-'+name).onclick = () => action(async () => {
  if (!$('connection').value) throw new Error('Select a model connection first.');
  const result = await api(`model-connections/${$('connection').value}/${name}`, {});
  $('model-message').textContent = result.userCode ? `Open ${result.verificationUrl} and enter ${result.userCode}. Then check connection.` : JSON.stringify(result); notice(name === 'disconnect' ? 'Model consent removed. Related deployments pause.' : 'Model connection updated.');
});
$('enroll-form').onsubmit = (event) => { event.preventDefault(); action(async () => { const pairing = await api('assets/pair', {connector: $('connector').value}); await api('assets/enroll', {code: pairing.code}); notice('Simulator enrolled with server-held connector credentials.'); }); };
$('grant-form').onsubmit = (event) => { event.preventDefault(); action(async () => { await api(`assets/${$('asset').value}/grants`, {user_id: $('member').value, enabled: true}); notice('Observation access granted.'); }); };
$('remove-grant').onclick = () => action(async () => { await api(`assets/${$('asset').value}/grants`, {user_id: $('member').value, enabled: false}); notice('Bench access removed. Related deployments pause.'); });
$('profile-preview').onclick = () => action(async () => {
  const review = await api(`assets/${$('asset').value}/profile-review/preview`, {}); state.profileReview = review;
  $('profile-review-summary').textContent = review.changed ? `Profile revision ${review.base_revision} has changed. Prior execution grants are paused. A new evaluation and independent review will be required.` : 'The observed simulator profile matches the reviewed baseline.';
  $('profile-diff').textContent = JSON.stringify({diff:review.diff, revalidation:review.revalidation, required_agent_checks:review.required_agent_checks, current_hash:review.base_hash, proposed_hash:review.profile_hash}, null, 2);
  $('profile-diff-details').hidden = false; $('profile-accept').disabled = !review.changed; notice('Profile preview recorded. Inspect the diff before accepting it.');
});
$('profile-accept').onclick = () => action(async () => {
  if (!state.profileReview || state.profileReview.asset_id !== $('asset').value) throw new Error('Inspect this bench’s current profile first.');
  const result = await api(`assets/${$('asset').value}/profile-review`, {review_id:state.profileReview.id});
  resetProfileReview(); $('profile-review-summary').textContent = `Reviewed baseline revision ${result.asset.profile_revision} saved. Collect a new evaluation, qualify it and obtain independent deployment review.`; notice('Baseline accepted for new evaluation. No execution authority was granted.');
});
$('evaluate').onclick = () => action(async () => { await api(`agents/${state.selected}/evaluate`, {}); notice('Evaluation traces collected. A trusted Sandbox verification is still required.'); });
$('qualify').onclick = () => action(async () => { await api(`agents/evaluations/${currentEvaluation().id}`, {}); notice('Sandbox verification completed. Inspect results before independent review.'); });
$('review').onclick = () => action(async () => { await api('deployments/review', {version_id: state.selected, evaluation_id: currentEvaluation().id}); notice('Exact version approved for observation. Start it separately when ready.'); });
$('new-agent').onclick = () => { state.selected = null; fillEditor(); renderVersions(); renderEvaluation(); notice('New draft. Select a bench and model connection.'); };
$('asset').onchange = () => { state.selected = null; resetProfileReview(); fillEditor(); renderVersions(); renderEvaluation(); renderDeployments(); loadTools().catch((error) => notice(error.message,true)); };
$('refresh').onclick = () => action(async () => { await load(); notice('Status refreshed.'); });
$('signout').onclick = () => action(async () => { await api('auth/logout', {}); window.location.assign('/'); });
try {
  state.me = await api('auth/me'); $('identity').textContent = `${state.me.org_id} · ${state.me.role} · ${state.me.user_id}`; $('login').hidden = true; $('product').hidden = false; await load();
} catch (error) { if (state.me) notice(error.message, true); }

setInterval(async () => { if (state.me && !state.busy && !document.hidden) { try { const [data, runtime, assets] = await Promise.all([api('deployments'), api('deployments/runtime'), api('assets')]); state.deployments = data.deployments; state.runtime = runtime.runtime; state.assets = assets.assets; renderRuntime(); renderEvaluation(); renderDeployments(); } catch (error) { state.runtime = {state:'unknown'}; renderRuntime(); notice(`Monitoring paused: ${error.message}`, true); } } }, 2000);
