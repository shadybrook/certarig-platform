import { get, post, api, headers, refreshContract } from './api.mjs';
let selected = null;
let timer = null;
let code = `import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
snapshot = json.loads(Path('/scratch/snapshot.json').read_text())
thermal = snapshot['document']['hardware'].get('simulator', {}).get('thermal')
report = {'kind':'snapshot_model_analysis','qualification':False}
if thermal:
    x = np.linspace(0, 60, 121)
    capacity = thermal['capacity_j_per_c']; loss = thermal['loss_w_per_c']
    equilibrium = thermal['ambient_c'] + thermal['heat_input_w'] / loss
    y = equilibrium + (thermal['initial_c']-equilibrium)*np.exp(-loss*x/capacity)
    plt.plot(x, y); plt.xlabel('Time (s)'); plt.ylabel('Temperature (degC)')
    plt.title('Snapshot thermal model, not physical measurements')
    plt.savefig('analysis.png')
    report['equilibrium_c'] = equilibrium
recording = Path('/scratch/recording.csv')
if recording.exists():
    import csv
    report['copied_recording_rows'] = len(list(csv.DictReader(recording.open())))
Path('analysis.json').write_text(json.dumps(report))`;
const deck = `Inductive flyback protection exploration - behavioral model only
* 12 V source, 20 mH / 12 ohm load, ideal controlled switch, ordinary flyback diode.
* Does not model component SOA, wiring inductance, thermal rise or physical release time.
Vbus bus 0 12
Lload bus load 20m
Rload load drain 12
Spermit drain 0 gate 0 SWPERMIT
Vgate gate 0 PULSE(0 5 1m 1u 1u 10m 30m)
Dflyback drain bus DCLAMP
.model SWPERMIT SW(Ron=0.05 Roff=1e9 Vt=2.5 Vh=0.1)
.model DCLAMP D(Is=1e-14 N=1 Rs=0.2 Tt=20n)
.control
set wr_singlescale
set wr_vecnames
tran 10u 40m
wrdata /out/protection-trace.txt v(drain) i(Lload) v(gate)
quit
.endc
.end
`;
const esc = s => String(s ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const pretty = x => JSON.stringify(x,null,2);
const el = id => document.getElementById(id);
let blobs = [];

function error(e) { el('sb-error').textContent = e.message; }
async function download(url, name) {
  const r=await fetch(url,{headers:headers()});
  if(!r.ok) throw new Error((await r.json()).error || 'Download refused');
  const object=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=object;a.download=name;a.click();URL.revokeObjectURL(object);
}
async function showArtifact(sid,jid,name) {
  const r=await fetch(`/v1/sandboxes/${sid}/jobs/${jid}/artifacts/${encodeURIComponent(name)}`,{headers:headers()});
  if(!r.ok)throw new Error((await r.json()).error || 'Artifact unavailable');
  const host=el('sb-artifact');host.replaceChildren();
  if(r.headers.get('Content-Type')==='image/png') { const url=URL.createObjectURL(await r.blob());blobs.push(url);const img=document.createElement('img');img.src=url;img.alt='Untrusted experiment plot, not a qualification receipt';img.style.maxWidth='100%';host.append(img); }
  else {const text=(await r.text()).slice(0,200000);const pre=document.createElement('pre');pre.textContent=text;host.append(pre);}
}
export async function renderSandbox() {
  if(timer)clearTimeout(timer);
  for(const b of blobs)URL.revokeObjectURL(b);blobs=[];
  const host=el('view-sandbox');
  host.innerHTML=`<h1>Commissioning sandbox</h1><p>Disposable analysis and simulated rehearsal. Configuration review, physical commissioning and execution approval remain separate.</p><p id="sb-error" class="error" role="alert"></p><div id="sb-status"></div><div id="sb-work"></div>`;
  let check;
  try {check=await get('/v1/sandboxes/preflight');}catch(e){error(e);return;}
  el('sb-status').innerHTML=`<article class="card"><h2>${check.ready?'Runtime ready':'Runtime unavailable'}</h2><ul>${(check.blockers||[]).map(b=>`<li>${esc(b)}</li>`).join('')}</ul><p>Fixture agent path; no live-model qualification. No host execution fallback.</p><button id="sb-refresh">Refresh</button></article>`;
  el('sb-refresh').onclick=()=>renderSandbox().catch(error);
  if(!check.enabled)return;
  let list;
  try {list=await get('/v1/sandboxes');}catch(e){error(e);return;}
  let w=(list.workspaces||[]).find(x=>x.sandbox_id===selected);
  el('sb-work').innerHTML=`<article class="card"><h2>Workspace</h2><label>Snapshot source<select id="sb-source"><option value="active">Active rig profile</option><option value="thermal">Thermal simulator fixture</option><option value="pressure_flow">Pressure/flow fixture</option></select></label><label><input id="sb-recording" type="checkbox">Include completed latest recording (immutable copy)</label><button id="sb-create">Create disposable workspace</button><label>Existing workspace<select id="sb-select"><option value="">Choose a workspace</option>${(list.workspaces||[]).map(x=>`<option value="${esc(x.sandbox_id)}" ${x.sandbox_id===selected?'selected':''}>${esc(x.sandbox_id)} · ${esc(x.status)} · revision ${x.revision}</option>`).join('')}</select></label></article><div id="sb-details"></div>`;
  el('sb-create').onclick=async()=>{try {const result=await post('/v1/sandboxes',{source:el('sb-source').value,...(el('sb-recording').checked?{recording_id:'latest'}:{})});selected=result.sandbox_id;await renderSandbox();}catch(e){error(e);}};
  el('sb-select').onchange=()=>{selected=el('sb-select').value;renderSandbox().catch(error);};
  if(!w)return;
  const sid=w.sandbox_id;const active=w.status==='active';
  el('sb-details').innerHTML=`<article class="card"><h2>Snapshot revision ${w.revision}</h2><p>${esc(w.snapshot.evidence_kind)} · execution authority: none</p><details><summary>Snapshot / procedure / provenance</summary><pre>${esc(pretty(w.snapshot))}</pre></details><label>Candidate configuration<textarea id="sb-document" rows="12">${esc(pretty(w.snapshot.document))}</textarea></label><label>Candidate supported procedure<textarea id="sb-procedure" rows="10">${esc(pretty(w.snapshot.procedure))}</textarea></label><button id="sb-revise" ${active?'':'disabled'}>Save new immutable revision</button></article>
    <article class="card"><h2>Experiment source</h2><label>Python analysis<textarea id="sb-code" rows="12">${esc(code)}</textarea></label><button id="sb-python" ${active&&check.ready?'':'disabled'}>Run bounded Python</button><details><summary>SPICE deck preview</summary><pre>${esc(deck)}</pre></details><button id="sb-spice" ${active&&check.ready?'':'disabled'}>Run SPICE exploration</button><hr><h3>Trusted rehearsal</h3><p>Uses the fixed harness and mandatory fault suite in a separate container. Generated code cannot issue this receipt.</p><button id="sb-rehearse" ${active&&check.ready?'':'disabled'}>Rehearse this exact revision</button></article>
    <article class="card"><h2>Jobs and evidence</h2>${w.jobs.map(j=>`<section><h3>${esc(j.kind)} · ${esc(j.status)}</h3><p>${esc(j.error||'')}</p>${j.receipt?`<p>Trusted simulated rehearsal: ${j.receipt.verification.passed?'PASS':'REFUSED'}</p><pre>${esc(pretty(j.receipt.verification))}</pre>`:'<p>Experiment output only; no qualification receipt.</p>'}<details><summary>Source / execution record</summary><pre>${esc(pretty(j))}</pre></details>${Object.keys(j.artifacts).map(n=>`<button class="sb-art" data-job="${esc(j.job_id)}" data-name="${esc(n)}">${esc(n)}</button>`).join('')}${j.qualification&&j.revision===w.revision&&active?`<button class="sb-propose" data-job="${esc(j.job_id)}">Submit configuration for review</button><button class="sb-procedure-propose" data-job="${esc(j.job_id)}">Submit procedure for review</button>`:''}</section>`).join('')}<div id="sb-artifact"></div><button id="sb-export">Export verifiable bundle</button><button id="sb-close" ${active?'':'disabled'}>Close workspace / cancel workers</button></article>
    <article class="card"><h2>Human review</h2><div id="sb-review"></div>${w.proposals.map(p=>`<section><h3>${esc(p.kind)} · ${esc(p.status)}</h3><pre>${esc(pretty(p.kind==='configuration'?p.document:p.procedure))}</pre><button class="sb-review" data-proposal="${esc(p.proposal_id)}">Review exact diff and proposal</button></section>`).join('')}</article>`;
  el('sb-code').oninput=()=>{code=el('sb-code').value;};
  const run=async(kind,source='')=>{try {await post(`/v1/sandboxes/${sid}/jobs`,{kind,source});await renderSandbox();}catch(e){error(e);}};
  el('sb-python').onclick=()=>run('python',el('sb-code').value);
  el('sb-spice').onclick=()=>run('spice',deck);
  el('sb-rehearse').onclick=()=>run('rehearsal');
  el('sb-revise').onclick=async()=>{try{await post(`/v1/sandboxes/${sid}/revisions`,{expected_revision:w.revision,document:JSON.parse(el('sb-document').value),procedure:JSON.parse(el('sb-procedure').value)});await renderSandbox();}catch(e){error(e);}};
  for(const button of document.querySelectorAll('.sb-art'))button.onclick=()=>showArtifact(sid,button.dataset.job,button.dataset.name).catch(error);
  for(const button of document.querySelectorAll('.sb-propose,.sb-procedure-propose'))button.onclick=async()=>{try{await post(`/v1/sandboxes/${sid}/proposals`,{job_id:button.dataset.job,kind:button.classList.contains('sb-procedure-propose')?'procedure':'configuration'});await renderSandbox();}catch(e){error(e);}};
  for(const button of document.querySelectorAll('.sb-review'))button.onclick=async()=>{try {
    const proposal=w.proposals.find(p=>p.proposal_id===button.dataset.proposal);
    const preview=proposal.kind==='configuration'?await post('/v1/rig/propose',{document:proposal.document}):await post('/v1/procedures/validate',{procedure:proposal.procedure});
    const review=el('sb-review');review.innerHTML=`<pre>${esc(pretty(preview))}</pre><label><input type="checkbox" id="sb-reviewed">I reviewed this exact proposal and its evidence.</label><button id="sb-apply">${proposal.kind==='configuration'?'Apply reviewed configuration':'Approve reviewed procedure draft'}</button><p>This does not grant execution or physical commissioning authority.</p>`;
    el('sb-apply').onclick=async()=>{try {if(!el('sb-reviewed').checked)throw new Error('Review confirmation is required');const reference={sandbox_id:sid,sandbox_proposal_id:proposal.proposal_id};if(proposal.kind==='configuration')await post('/v1/rig/apply',{...reference,document:proposal.document,expected_current_hash:proposal.base_config_hash});else {const draft=await post('/v1/procedures/drafts',{procedure:proposal.procedure});await post(`/v1/procedures/drafts/${draft.procedure_hash}/approve`,reference);}await refreshContract();await renderSandbox();}catch(e){error(e);}};
  }catch(e){error(e);}};
  el('sb-export').onclick=()=>download(`/v1/sandboxes/${sid}/export`,`${sid}.zip`).catch(error);
  el('sb-close').onclick=async()=>{try {await api('DELETE',`/v1/sandboxes/${sid}`,{});await renderSandbox();}catch(e){error(e);}};
  if(w.jobs.some(j=>['queued','running'].includes(j.status)))timer=setTimeout(()=>{if(!host.classList.contains('hidden'))renderSandbox().catch(error);},1000);
}
