/* Persistent product workspace. All rendered messages and artifacts are untrusted text. */
export function init({api, state, load, action, notice, checkedTools, renderTools, extraDefinition, fillEditor}) {
  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; };
  const button = (label, fn) => { const b=el('button',label); b.type='button'; b.onclick=()=>action(fn); return b; };
  const json = (id) => JSON.parse($(id).value);
  const bench = () => $('asset').value;
  let saveQueue=Promise.resolve(), generation=0, conflicted=false, switching=false, standaloneDirty=false;
  let lastRender="", current=null, data={drafts:[],tasks:[],tools:[],analyses:[],profiles:[],evidence:[],replays:[],projects:[]}, loading=false, saveTimer, dirty=false;
  function pane(name) { document.querySelector('.workspace-grid').dataset.pane=name; document.querySelectorAll('[data-pane].pane-tabs button, .pane-tabs [data-pane]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.pane===name))); }
  document.querySelectorAll('.pane-tabs button').forEach(b=>b.onclick=()=>pane(b.dataset.pane));
  matchMedia('(max-width:760px)').addEventListener('change',()=>{document.querySelector('.pane-tabs [aria-pressed="true"]')?.focus();});
  document.querySelectorAll('[data-inspector]').forEach(b=>b.onclick=()=>{const target=b.dataset.inspector;$('inspect-panel').dataset.view=target;document.querySelectorAll('[data-inspector]').forEach(n=>n.setAttribute('aria-pressed',String(n===b)));});
  const headerObserver=new ResizeObserver(([entry])=>document.documentElement.style.setProperty('--header-height',`${entry.contentRect.height+24}px`));headerObserver.observe(document.querySelector('.top'));
  const fitWorkspace=()=>{const grid=document.querySelector('.workspace-grid');if(innerWidth>1150)grid.style.setProperty('--workspace-height',`${Math.max(280,innerHeight-grid.getBoundingClientRect().top-20)}px`);};
  addEventListener('resize',fitWorkspace);setTimeout(fitWorkspace,0);
  const strip=el('div');strip.id='revoke-strip';$('notice').after(strip);
  function editorDefinition() { return {name:$('agent-name').value.trim(),instructions:$('instructions').value,asset_id:bench(),connection_id:$('connection').value,tools:checkedTools(),...extraDefinition()}; }
  function showDraft(value) {
    current=value; dirty=false; standaloneDirty=false; conflicted=false; state.selected=null;generation++;
    if(document.body.classList.contains('journal-app'))history.replaceState(null,'',`#/sessions/${value.id}`);
    $('agent-form').querySelectorAll('input,textarea,select,button').forEach(n=>n.disabled=value.owner_id!==state.me.user_id);
    const d=value.definition; $('agent-name').value=d.name;$('instructions').value=d.instructions;$('connection').value=d.connection_id;renderTools(d.tools);
    const limits=d.limits||{model_calls:8,max_assessments:10,interval_s:30,lease_s:900};
    for(const [id,key] of [['limit-calls','model_calls'],['limit-assessments','max_assessments'],['limit-interval','interval_s'],['limit-lease','lease_s']])$(id).value=limits[key];
    document.querySelectorAll('input[name="analysis-tools"]').forEach(b=>b.checked=(d.analysis_tools||[]).includes(b.value));
    $('version-label').textContent=`Draft · revision ${value.revision}${value.base_version_id?' · base '+value.base_version_id:''}`;
    renderDraft();
  }
  function renderDraft() {
    const standalone=Boolean(state.selected&&!current);$('draft-form').hidden=Boolean(current)||standalone;
    $('persist-draft').hidden=standalone||Boolean(current&&current.status!=='draft');$('commit-draft').hidden=standalone||Boolean(current&&current.status!=='draft');
    $('conversation').replaceChildren(...(current?.messages||[]).map(m=>{const row=el('article',undefined,'conversation-message');row.append(el('strong',m.role==='user'?'You':'Drafting assistant · deterministic fixture'),el('p',m.text));return row;}));
    if(standalone)$('conversation').append(el('p','No originating conversation recorded for this saved version.','muted'));
    const editable=current?.status==='draft' && current.owner_id===state.me.user_id;
    $('message-form').hidden=!editable;$('persist-draft').disabled=!editable;$('commit-draft').disabled=!editable || Boolean(current?.blockers?.length);
    $('draft-status').textContent=current ? `${dirty?'Unsaved changes':'Saved'} · revision ${current.revision} · ${current.status}` : 'Start with a task';
    $('draft-blockers').textContent=(current?.blockers||[]).join('. ');
    $('draft-diff').textContent=current ? JSON.stringify(current.diff||current.definition,null,2) : 'No proposal selected.';
  }
  function persist(message) {
    const id=current?.id;
    const operation=saveQueue.catch(()=>{}).then(async()=>{
      if(!current || current.id!==id || current.status!=='draft')return;if(conflicted){await conflictDialog(id);throw Error('Resolve the draft conflict before saving again.');}
      const token=generation, definition=editorDefinition();
      const body={expected_revision:current.revision,definition,...(message?{message}:{})};
      const changed=await api(`drafts/${id}`,body), fresh=await api(`drafts/${changed.id}`);
      if(generation!==token||current?.id!==id)return;
      const changedDuringSave=JSON.stringify(editorDefinition())!==JSON.stringify(definition);
      current=fresh;
      if(message&&!changedDuringSave)$('instructions').value=current.definition.instructions;
      dirty=changedDuringSave;renderDraft();
    });
    const result=operation.catch(async e=>{if(e.status===409&&current?.id===id&&!conflicted){conflicted=true;await conflictDialog(id);}throw e;});saveQueue=result;return result;
  }
  async function conflictDialog(id){
    const local=editorDefinition(),remote=await api(`drafts/${id}`);if(current?.id!==id)return;
    const dialog=el('dialog');dialog.setAttribute('aria-label','Resolve draft conflict');const body=el('div',undefined,'dialog-content');
    body.append(el('h2','This draft changed elsewhere'),el('p','Your local edits are retained. Compare the server revision before choosing what to keep.'),el('h3','Your local definition'),el('pre',JSON.stringify(local,null,2)),el('h3',`Server revision ${remote.revision}`),el('pre',JSON.stringify(remote.definition,null,2)));
    body.append(button('Keep editing locally',async()=>{dialog.close();}),button('Load server revision',async()=>{showDraft(remote);dialog.close();}),button('Save local as a new draft',async()=>{const created=await api('drafts',{asset_id:local.asset_id,template:current.template,goal:local.instructions.slice(0,2000)});const changed=await api(`drafts/${created.id}`,{expected_revision:created.revision,definition:local});showDraft(await api(`drafts/${changed.id}`));dialog.close();notice('Local edits saved as a separate draft. No version or authority was created.');}));
    dialog.append(body);dialog.addEventListener('close',()=>dialog.remove(),{once:true});document.body.append(dialog);dialog.showModal();
  }
  async function saveAdvancedDraft(){
    const definition=editorDefinition(),base=state.versions.find(v=>v.id===state.selected);const controls=[...$('agent-form').querySelectorAll('input,textarea,select,button')];const disabled=controls.map(n=>n.disabled);controls.forEach(n=>n.disabled=true);
    try{const d=await api('drafts',{asset_id:definition.asset_id,goal:definition.instructions.slice(0,2000),template:'commissioning',...(base?{base_version_id:base.id}:{})});const changed=await api(`drafts/${d.id}`,{expected_revision:d.revision,definition});showDraft(await api(`drafts/${changed.id}`));notice('Advanced definition saved as a resumable draft. No execution authority granted.');}
    catch(e){controls.forEach((n,i)=>n.disabled=disabled[i]);throw e;}
  }
  const saveAdvanced=el('button','Save as resumable draft');saveAdvanced.type='button';saveAdvanced.id='save-advanced-draft';saveAdvanced.onclick=()=>action(async()=>{if(current?.status==='draft')await persist();else await saveAdvancedDraft();});$('save-agent').before(saveAdvanced);
  function guardSwitch(event,proceed){
    if((!dirty&&!standaloneDirty)||switching)return false;
    event.preventDefault();event.stopImmediatePropagation();clearTimeout(saveTimer);
    const dialog=el('dialog');dialog.setAttribute('aria-label','Unsaved agent changes');const body=el('div',undefined,'dialog-content');body.append(el('h2','Keep your draft changes?'),el('p','Save this draft before changing the bench or selected definition.'));
    const complete=async(save)=>{if(save){if(current?.status==='draft')await persist();else await saveAdvancedDraft();}else{dirty=false;standaloneDirty=false;conflicted=false;}dialog.close();switching=true;try{proceed();}finally{switching=false;}};
    body.append(button('Save draft and switch',()=>complete(true)),button('Discard local changes and switch',()=>complete(false)),button('Keep editing',async()=>dialog.close()));dialog.append(body);dialog.addEventListener('close',()=>dialog.remove(),{once:true});document.body.append(dialog);dialog.showModal();return true;
  }
  for(const id of ['asset','project'])$(id).addEventListener('change',event=>{const field=$(id),requested=field.value,previous=id==='asset'?(current?.asset_id||state.toolAsset):(current?.project_id||'');if((!dirty&&!standaloneDirty)||switching)return;field.value=previous||'';guardSwitch(event,()=>{field.value=requested;field.dispatchEvent(new Event('change'));});},true);
  $('versions').addEventListener('click',event=>{const target=event.target.closest('button');if(target)guardSwitch(event,()=>target.click());},true);
  $('new-agent').addEventListener('click',event=>guardSwitch(event,()=>$('new-agent').click()),true);
  $('draft-form').onsubmit=e=>{e.preventDefault();action(async()=>{if(dirty)await persist();const created=await api('drafts',{asset_id:bench(),project_id:$('project').value||null,template:$('template').value,goal:$('goal').value});showDraft(await api(`drafts/${created.id}`));notice('Draft saved. Select a model and inspect the proposed definition.');});};
  $('message-form').onsubmit=e=>{e.preventDefault();const message=$('message').value;action(async()=>{clearTimeout(saveTimer);await persist(message);if($('message').value===message)$('message').value='';notice('Requirement saved in the proposal.');});};
  $('persist-draft').onclick=()=>action(async()=>{clearTimeout(saveTimer);await persist();notice('Draft changes saved.');});
  $('commit-draft').onclick=()=>action(async()=>{clearTimeout(saveTimer);await persist();if(current.blockers.length)throw Error(current.blockers.join('. '));const v=await api(`drafts/${current.id}/commit`,{expected_revision:current.revision});current=await api(`drafts/${current.id}`);state.selected=v.id;if(document.body.classList.contains('journal-app'))history.replaceState(null,'',`#/sessions/${v.id}`);$('version-label').textContent=`Version ${v.revision} · ${v.id}`;renderDraft();$('agent-builder')?.close();notice('Draft saved as an immutable version. Evaluate it before review.');});
  const saveStandalone=$('agent-form').onsubmit;$('agent-form').onsubmit=e=>{if(current?.status==='draft'){e.preventDefault();$('commit-draft').click();}else saveStandalone(e);};
  $('agent-form').addEventListener('input',()=>{if(!current||current.status!=='draft'){standaloneDirty=true;$('draft-status').textContent='Unsaved advanced changes';return;}dirty=true;renderDraft();clearTimeout(saveTimer);saveTimer=setTimeout(()=>{if(!state.busy&&!conflicted)persist().catch(e=>notice(`Draft not saved: ${e.message}. Reload the draft to resolve a conflict.`,true));},800);});
  $('connection').addEventListener('change',()=>{if(current?.status==='draft')persist().catch(e=>notice(e.message,true));});
  $('project-form').onsubmit=e=>{e.preventDefault();action(async()=>{const p=await api('projects',{name:$('project-name').value,asset_ids:[...$('project-benches').selectedOptions].map(o=>o.value).length?[...$('project-benches').selectedOptions].map(o=>o.value):[bench()]});await refresh();$('project').value=p.id;notice('Project saved. Bench permissions remain explicit.');});};
  $('project').onchange=()=>{const p=data.projects.find(v=>v.id===$('project').value);for(const o of $('asset').options)o.hidden=Boolean(p&&!p.asset_ids.includes(o.value));if(p&&!p.asset_ids.includes(bench())){$('asset').value=p.asset_ids[0]||'';$('asset').dispatchEvent(new Event('change'));}render();};
  $('asset').addEventListener('change',()=>{generation++;current=null;dirty=false;clearTimeout(saveTimer);renderDraft();render();});
  document.addEventListener('versionselected',async(event)=>{generation++;current=null;dirty=false;standaloneDirty=false;renderDraft();$('draft-status').textContent='No originating conversation recorded';pane('commission');const id=event.detail.versionId;try{const records=await api('drafts');const draft=records.drafts.find(d=>d.version_id===id);if(draft&&state.selected===id){const restored=await api(`drafts/${draft.id}`);if(state.selected===id){current=restored;renderDraft();}}}catch(e){notice(`Conversation unavailable: ${e.message}`,true);}});
  $('new-agent').addEventListener('click',()=>{generation++;current=null;dirty=false;standaloneDirty=false;renderDraft();$('goal').focus();});
  async function submit(kind,id) {const t=await api('tasks',{kind,target_id:id});notice(`Task ${t.id} queued. You can continue working or cancel it.`);await refresh();}
  $('evaluate').onclick=()=>action(()=>submit(state.versions.find(v=>v.id===state.selected)?.team_members?'team_evaluate':'evaluate',state.selected));
  $('qualify').onclick=()=>action(()=>submit('qualify',state.evaluations.filter(e=>e.version_id===state.selected).at(-1).id));
  $('team-form').onsubmit=e=>{e.preventDefault();action(async()=>{const ids=[...$('specialists').selectedOptions].map(o=>o.value);const team=await api('teams',{name:$('team-name').value,supervisor_id:$('supervisor').value,specialist_ids:ids});state.versions.push(team);state.selected=team.id;fillEditor();document.dispatchEvent(new CustomEvent('versionselected',{detail:{versionId:team.id}}));$('team-state').textContent='Team saved. Evaluate this exact team before independent review.';notice('Team version saved with one shared budget.');});};
  $('analysis-form').onsubmit=e=>{e.preventDefault();action(async()=>{await api('tools',{name:$('analysis-name').value,asset_id:bench(),kind:$('analysis-kind').value,source:$('analysis-source').value,input_schema:json('analysis-input'),output_schema:json('analysis-output'),dependencies:[],tests:json('analysis-tests')});await refresh();notice('Tool version saved. Run declared tests before independent review.');});};
  $('replay-form').onsubmit=e=>{e.preventDefault();action(async()=>{await api('replays',{asset_id:bench(),name:$('replay-name').value,csv:$('replay-csv').value,source:$('replay-source').value});await refresh();notice('Recording imported for analysis. Its origin is not independently authenticated.');});};
  $('connector-profile-form').onsubmit=e=>{e.preventDefault();action(async()=>{await api('connector-profiles',{asset_id:bench(),name:$('connector-profile-name').value,transport:$('transport').value,channels:json('connector-channels')});await refresh();notice('Mapping proposal saved for independent review and operator installation.');});};
  const mappingExample=()=>{const transport=$('transport').value;return [{channel_id:'temperature',unit:'degC',calibration_id:'replace-with-evidence-id',valid_min:0,valid_max:60,safe_min:5,safe_max:40,max_age_s:1,source:transport==='mqtt'?{topic:'bench/temperature'}:transport==='serial_jsonl'?{channel_id:'temperature'}:{register:0,device_id:1,function:4,data_type:'uint16',gain:0.1,offset:0,byte_order:'big',word_order:'big'}}];};
  $('transport').onchange=()=>{$('connector-channels').value=JSON.stringify(mappingExample(),null,2);};$('transport').onchange();
  $('evidence-filter').oninput=()=>renderEvidence();
  function selectOptions(id,rows,label){const select=$(id),previous=[...select.selectedOptions].map(o=>o.value);select.replaceChildren(...rows.map(r=>{const o=el('option',label(r));o.value=r.id;o.selected=previous.includes(r.id);return o;}));}
  function renderEvidence(){
    const query=$('evidence-filter').value.toLowerCase();
    const rows=data.evidence.filter(v=>v.asset_id===bench()&&JSON.stringify(v).toLowerCase().includes(query));
    $('evidence-list').replaceChildren(...rows.map(v=>{const row=el('article');row.append(el('h3',`${v.version_id} · ${v.status}`),el('p',`${v.backend==='fixture'?'Deterministic fixture':v.backend} · ${v.observations} observations`));const deployment=state.deployments.find(d=>d.id===v.id);const latest=deployment?.observations?.at(-1);if(latest){row.append(el('p',`${latest.output.status}: ${latest.output.reason}`));const raw=el('details');raw.append(el('summary','Inspect raw observation and tool trace'),el('pre',JSON.stringify(latest,null,2)));row.append(raw);}row.append(button('Verify exported evidence',async()=>{const result=await api(`evidence/${v.id}/verify`,{});notice(`Evidence integrity verified: ${result.format}. This does not prove physical commissioning.`);}));const a=el('a','Download bundle');a.href=`/v1/deployments/${v.id}/export`;a.download='certarig-agent-evidence.zip';row.append(a);return row;}));
    if(!rows.length)$('evidence-list').append(el('p','No evidence matches this bench and filter.','muted'));
  }
  function render(){
    const focused=document.activeElement;const focusTool=focused?.dataset?.toolId;const selection=focusTool?[focused.selectionStart,focused.selectionEnd]:null;
    const project=data.projects.find(p=>p.id===$('project').value);
    selectOptions('project-benches',state.assets,a=>a.name);
    const matches=v=>v.asset_id===bench()&&(!project||v.project_id===project.id);
    $('draft-list').replaceChildren(...data.drafts.filter(matches).map(d=>button(`${d.definition.name} · ${d.status}`,async()=>{if(dirty)await persist();showDraft(await api(`drafts/${d.id}`));pane('commission');})));
    if(!$('draft-list').children.length)$('draft-list').append(el('p','No conversations yet. Start with a commissioning task.','muted'));
    const versions=state.versions.filter(v=>v.asset_id===bench()&&!v.team_members&&v.author_id===state.me.user_id);
    const asset=state.assets.find(a=>a.id===bench());
    const eligible=v=>state.evaluations.some(e=>e.version_id===v.id&&e.status==='passed'&&e.trusted&&e.binding.version_hash===v.hash&&e.binding.profile_hash===asset?.profile_hash&&(e.binding.profile_revision??1)===(asset?.profile_revision??1)&&state.connections.some(c=>c.id===v.connection_id&&c.enabled&&c.revision===e.binding.connection_revision));
    for(const id of ['supervisor','specialists']){selectOptions(id,versions,v=>`${v.name} · v${v.revision} · ${eligible(v)?'evaluated':'evaluation required'}`);for(const option of $(id).options)option.disabled=!eligible(versions.find(v=>v.id===option.value));}
    const teamReady=()=>{const ids=[$('supervisor').value,...[...$('specialists').selectedOptions].map(o=>o.value)];const valid=ids.length>=2&&ids.length<=4&&new Set(ids).size===ids.length&&ids.every(id=>{const v=versions.find(v=>v.id===id);return v&&eligible(v);});$('team-form').querySelector('button[type=submit],button:not([type])').disabled=!valid;$('team-state').textContent=valid?'Exact evaluated members selected. The team must pass evaluation and independent review. Shared maximum: 8 model calls, 10 assessments, 15 minutes.':'Choose a distinct evaluated supervisor and one to three evaluated specialists. Unevaluated or stale members cannot participate.';};
    $('supervisor').onchange=teamReady;$('specialists').onchange=teamReady;teamReady();
    $('task-list').replaceChildren(...data.tasks.filter(t=>t.asset_id===bench()).slice(-12).reverse().map(t=>{const row=el('article');row.append(el('h3',`${t.kind.replaceAll('_',' ')} · ${t.status}`));if(t.error)row.append(el('p',t.error,'warn'));row.append(button('Inspect activity',async()=>{const events=await api(`tasks/${t.id}/events`,{after:0});const pre=el('pre',events.events.map(e=>`${e.cursor} · ${e.event}${e.case?' · '+e.case:''}`).join('\n'));row.append(pre);}));if(['queued','running'].includes(t.status))row.append(button('Cancel task',async()=>{await api(`tasks/${t.id}/cancel`,{});await refresh();}));return row;}));
    if(!$('task-list').children.length)$('task-list').append(el('p','Evaluation and experiment activity appears here.','muted'));
    const active=state.deployments.filter(d=>['running','approved','paused'].includes(d.status));
    strip.replaceChildren(...active.flatMap(d=>[el('p',`${d.status} · observation only · ${d.assessments}/10 assessments`),button('Revoke active access',async()=>{await api(`deployments/${d.id}/revoke`,{});notice('Access revoked. Late outputs will be discarded.');})]));
    const selectedTools=new Set((dirty?[...document.querySelectorAll('input[name="analysis-tools"]:checked')].map(b=>b.value):current?.definition.analysis_tools||state.versions.find(v=>v.id===state.selected)?.analysis_tools||[]));
    $('analysis-permissions').replaceChildren(...data.tools.filter(t=>t.asset_id===bench()&&t.status==='reviewed'&&t.owner_id===state.me.user_id).map(t=>{const label=el('label',undefined,'check');const box=el('input');box.type='checkbox';box.name='analysis-tools';box.value=t.id;box.checked=selectedTools.has(t.id);label.append(box,document.createTextNode(t.name));return label;}));
    if(!$('analysis-permissions').children.length)$('analysis-permissions').append(el('p','No independently reviewed analysis tools on this bench.','muted'));
    const recordingCache=new Map([...$('analysis-tools').querySelectorAll('select[data-replay-tool]')].map(n=>[n.dataset.replayTool,n.value]));
    const inputCache=new Map([...$('analysis-tools').querySelectorAll('textarea[data-tool-id]')].map(n=>[n.dataset.toolId,n.value]));
    $('analysis-tools').replaceChildren(...data.tools.filter(t=>t.asset_id===bench()).map(t=>{const row=el('article');row.append(el('h3',`${t.name} · ${t.kind} · ${t.status}`));row.append(button('Run declared tests',async()=>{const result=await api(`tools/${t.id}/test`,{});notice(`Tool tests started: ${result.id}`);await refresh();}));if(state.me.role==='reviewer'&&t.owner_id!==state.me.user_id)row.append(button('Review completed tool tests',async()=>{const tests=await api(`tools/${t.id}/tests`);const test=tests.tests.at(-1);if(!test)throw Error('The author must run declared tests first.');await api(`tools/${t.id}/review`,{test_id:test.id});await refresh();notice('Exact tool source and tested image reviewed for analysis only.');}));if(t.status==='reviewed'&&t.owner_id===state.me.user_id){const input=el('textarea');input.dataset.toolId=t.id;input.value=inputCache.get(t.id)||'{}';input.setAttribute('aria-label',`${t.name} inputs JSON`);const recording=el('select');recording.dataset.replayTool=t.id;recording.setAttribute('aria-label',`${t.name} recording`);const live=el('option','Current bench snapshot');live.value='';recording.append(live);for(const replay of data.replays.filter(r=>r.asset_id===bench())){const option=el('option',`${replay.name} · ${replay.kind}`);option.value=replay.id;recording.append(option);}recording.value=recordingCache.get(t.id)||'';row.append(input,recording,button('Run analysis',async()=>{await api(`tools/${t.id}/run`,{inputs:JSON.parse(input.value),...(recording.value?{replay_id:recording.value}:{})});await refresh();}));}return row;}));
    $('analysis-runs').replaceChildren(...data.analyses.filter(a=>a.asset_id===bench()).slice(-8).map(a=>{
      const row=el('article');
      row.append(el('h3',`Analysis · ${a.status}`),button('Inspect results',async()=>{
        const result=await api(`analyses/${a.id}`);
        row.append(el('pre',JSON.stringify(result,null,2)));
        for(const name of Object.keys(result.artifacts||{})){
          if(!/\.(json|txt|csv|png|log)$/.test(name))continue;
          row.append(button(`Open ${name}`,async()=>{
            const artifact=await api(`analyses/${a.id}/artifact`,{name});
            if(name.endsWith('.png')){
              const image=el('img');image.src=`data:image/png;base64,${artifact.data}`;image.alt=name;image.style.maxWidth='100%';row.append(image);
            } else {
              row.append(el('pre',new TextDecoder().decode(Uint8Array.from(atob(artifact.data),c=>c.charCodeAt(0)))));
            }
          }));
        }
      }));
      if(!['completed','cancelled','failed','interrupted','timed_out'].includes(a.status))row.append(button('Cancel analysis',async()=>{await api(`analyses/${a.id}/cancel`,{});await refresh();}));
      return row;
    }));
    $('connector-profiles').replaceChildren(...data.profiles.filter(c=>c.asset_id===bench()).map(c=>{const row=el('article');row.append(el('h3',`${c.name} · ${c.transport}`),el('p',c.status),el('pre',JSON.stringify(c.channels,null,2)));if(state.me.role==='reviewer'&&c.owner_id!==state.me.user_id&&c.status==='proposed')row.append(button('Review observation mappings',async()=>{await api(`connector-profiles/${c.id}/review`,{});await refresh();notice('Mappings reviewed. An operator must install them; physical commissioning remains separate.');}));return row;}));
    $('replay-list').replaceChildren(...data.replays.filter(r=>r.asset_id===bench()).map(r=>el('p',`${r.name} · ${r.samples} recorded samples · ${r.kind}`)));
    renderEvidence();fitWorkspace();if(focusTool){const replacement=[...$('analysis-tools').querySelectorAll('textarea[data-tool-id]')].find(n=>n.dataset.toolId===focusTool);replacement?.focus({preventScroll:true});if(selection&&replacement)replacement.setSelectionRange(...selection);}document.dispatchEvent(new Event('journalupdated'));
  }
  async function refresh(){if(loading||!state.me)return;loading=true;try{const results=await Promise.all(['projects','drafts','tasks','tools','analyses','connector-profiles','evidence','replays'].map(p=>api(p)));const pending=results[4].analyses.filter(a=>a.asset_id===bench()&&!['completed','failed','cancelled','interrupted','timed_out'].includes(a.status)).slice(0,8);const refreshed=await Promise.all(pending.map(a=>api(`analyses/${a.id}`)));results[4].analyses=results[4].analyses.map(a=>refreshed.find(v=>v.id===a.id)||a);const before=JSON.stringify(data.tasks);data={projects:results[0].projects,drafts:results[1].drafts,tasks:results[2].tasks,tools:results[3].tools,analyses:results[4].analyses,profiles:results[5].profiles,evidence:results[6].evidence,replays:results[7].replays};const selectedProject=$('project').value;selectOptions('project',[{id:'',name:'All permitted benches'},...data.projects],r=>r.name);$('project').value=selectedProject;if(current&&!state.assets.some(a=>a.id===current.asset_id)){generation++;current=null;dirty=false;renderDraft();}
      const signature=JSON.stringify([data, state.versions, state.assets, state.connections,state.evaluations])+bench();if(signature!==lastRender){render();lastRender=signature;}if(before!==JSON.stringify(data.tasks)){const latest=data.tasks.at(-1);if(latest&&$('notice').textContent.includes(latest.id)&&['completed','failed','cancelled','interrupted'].includes(latest.status))notice(`Task ${latest.id} ${latest.status}${latest.error?': '+latest.error:''}.`,latest.status==='failed');await load();render();}}catch(e){notice(`Workspace unavailable: ${e.message}`,true);}finally{loading=false;}}
  document.addEventListener('assetpermissionlost',()=>{generation++;current=null;dirty=false;standaloneDirty=false;conflicted=false;clearTimeout(saveTimer);renderDraft();document.querySelectorAll('dialog[open]').forEach(d=>d.close());});
  document.addEventListener('platformloaded',()=>refresh());
  setInterval(()=>{if(!document.hidden&&!state.busy)refresh();},2000);
  window.addEventListener('beforeunload',e=>{if(dirty||standaloneDirty){e.preventDefault();e.returnValue='';}});
  async function restore(){if(!document.body.classList.contains('journal-app'))return;const requestedHash=location.hash;const id=location.hash.split('/')[2];if(!id||current?.id===id||state.selected===id)return;try{const drafts=await api('drafts');const draft=drafts.drafts.find(d=>d.id===id);if(draft){const restored=await api(`drafts/${id}`);if(location.hash===requestedHash)showDraft(restored);return;}const version=state.versions.find(v=>v.id===id);if(version){const btn=[...$('versions').children].find(b=>b.textContent===`${version.name} · v${version.revision}`);btn?.click();}}catch(e){notice(`Session unavailable: ${e.message}`,true);}}
  document.addEventListener('journalnavigate',restore);document.addEventListener('platformloaded',restore);restore();refresh();
}
