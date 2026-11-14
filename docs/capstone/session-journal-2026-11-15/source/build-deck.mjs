import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const build=path.dirname(fileURLToPath(import.meta.url)),workspace=path.dirname(build);
const template=process.env.CERTARIG_CAPSTONE_TEMPLATE;if(!template)throw Error('Set CERTARIG_CAPSTONE_TEMPLATE to the supplied ten-slide PPTX.');
const skill=process.env.CERTARIG_PRESENTATIONS_SKILL;if(!skill)throw Error('Load the installed presentations skill and set CERTARIG_PRESENTATIONS_SKILL.');
const presentation=await PresentationFile.importPptx(await FileBlob.load(template));
const replacements=[
 {'Capstone Project Title':'CertaRig','Team Members':'Chintan Dedhia','Supervisor Name':'Current supervisor to confirm','BSc CS (Academic Year)':'BSc CS · Year to confirm'},
 {'Background of the problem':'Bench data, configuration and review evidence are often separated.','Gap in existing system':'A connection or plausible agent answer does not establish readiness.','Importance of the problem':'Engineers need scoped decisions and reproducible evidence.'},
 {'Objective 1':'Create, evaluate and independently review engineering agents.','Objective 2':'Explain supported bench data and retain complete evidence.','In-scope items':'Local observation; known simulators; bounded analysis and support reports.'},
 {'Existing approach 1':'Manual configuration and separate experiment scripts.','Existing approach 2':'General coding assistants without equipment authorization.','Limitations':'Neither approach alone establishes exact-profile qualification.'},
 {},
 {'Programming Language':'Python 3 and modular browser JavaScript','Frameworks':'Existing AgentSession, JSON Schema and deterministic controls','Database':'SQLite for identities, revisions, tasks and reviews','Tools':'Playwright, pytest, Docker/Colima and ngspice interfaces'},
 {'Feature 1':'Persistent Session Journal and exact-version authoring','Feature 2':'Refusal, independent review, observation and revocation','Screenshots / Flow':'Live demonstration · five minutes · fixture status disclosed'},
 {'Output':'Journal, bench descriptions and support reports implemented.','Performance metrics':'90.63% coverage; 11 platform and 10 Edge browser checks passed.','Comparison':'40 new description and draft tests; live-provider comparison remains unrun.'},
 {'Technical challenges':'Genuine Dex/Codex qualification remains open.\nPinned image and seven real-container cases remain unrun.\nPhysical results and native mobile keyboard checks are pending.'},
 {'Summary':'Locally tested commissioning software with explicit authority boundaries.','Enhancements ( if any)':'Qualify identity, containers and connectors; resolve physical mission evidence.'}
];
const timing=[30,60,60,45,75,45,300,120,105,60];
const notes=[
 'Introduce the software product and its reference bench. Current supervisor, institution metadata and academic year require confirmation; this is a draft.',
 'Explain that signal identity, units, calibration and permissions are separate facts. Do not describe the platform as universal equipment recognition.',
 'Scope is local observation and known simulation. An unfamiliar experiment receives an analysis-only support report until an exact procedure/model pack is qualified.',
 'These are design categories, not measured competitive comparisons. T3 Code inspired persistent conversations and inline review: https://t3.codes/.',
 'Studio uses the authenticated platform; Edge acquisition and Sandbox execution are separate. Human review controls deployment authority. No model can install an arbitrary connector or issue a receipt.',
 'Reuse the existing modular stack, tools, AgentSession, SQLite and schemas. No framework migration, training run or paid model call was needed for this coding increment.',
 'Five-minute live sequence: 0:00 select thermal task and inspect exact definition; 0:50 show a stale-source refusal; 1:30 inspect corrected fixture evaluation; 2:10 show independent review; 3:00 start observation and inspect source/evidence; 4:00 revoke from another view; 4:30 export/verify evidence if genuine runtime prerequisites passed, otherwise show the explicit isolation refusal and label fixture evidence. Never pass a fixture off as a real container or login qualification.',
 'Sources: docs/product/validation/session-journal local regression, bench-description and browser records. Coverage is software coverage, not system accuracy. UI identities/providers/engines are labelled test dependencies. No latency, physical response or general bench-recognition accuracy was measured.',
 'Resource preflight requires normal memory pressure and at least 8 GiB free. Do not weaken isolation. Genuine sign-in and real equipment checks require their attended environment. The under-INR-3000 demonstration direction must be reconciled with signed physical missions.',
 'The software checkpoint is 20 November 2026; the university deadline is unconfirmed. Complete the genuine qualification gates and physical evidence or supervisor-approved amendment before final submission. No supervisor remarks or attendance were fabricated.'
];
for(const [index,slide]of presentation.slides.items.entries()){
 for(const shape of slide.shapes.items){if(index>0&&String(shape.text).trim()==='Tools & Technologies')continue;for(const [from,to]of Object.entries(replacements[index]))shape.text?.replace(from,to);}
 slide.speakerNotes.text=`Target duration ${timing[index]} seconds. ${notes[index]}\nSources: signed Phase 3 report and institutional ten-slide template; CertaRig source branch product/session-journal-2026-11-14 and validation records dated 15 November 2026.`;
}
const architecture=presentation.slides.items[4];
for(const shape of architecture.shapes.items)if(String(shape.text).includes('System overview'))shape.text='';
function text(slide,value,x,y,w,h,size=24,boxed=false){const shape=slide.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:boxed?'#777777':'none',width:boxed?1:0}});shape.text=value;shape.text.style={fontFamily:'Aptos',fontSize:size,color:'#000000',alignment:boxed?'center':'left'};return shape;}
text(architecture,'Observation path',42,175,850,36,22);
text(architecture,'Studio',50,230,230,80,26,true);text(architecture,'→',293,245,50,50,32);text(architecture,'Platform API',350,230,230,80,26,true);text(architecture,'→',593,245,50,50,32);text(architecture,'Local Edge',650,230,230,80,26,true);
text(architecture,'Analysis path',42,365,850,36,22);
text(architecture,'Platform API',50,420,230,80,26,true);text(architecture,'→',293,435,50,50,32);text(architecture,'Sandbox broker',350,420,230,80,26,true);text(architecture,'→',593,435,50,50,32);text(architecture,'Isolated workers',650,420,230,80,26,true);
text(architecture,'Independent review controls the observation lease.\nEdge acquisition remains separate from agent activity.',42,575,850,80,24);
await fs.mkdir(path.join(build,'deck-render'),{recursive:true});
for(const [i,slide]of presentation.slides.items.entries()){const png=await presentation.export({slide,format:'png',scale:1});await fs.writeFile(path.join(build,'deck-render',`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));}
const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(presentation)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir:workspace,candidatePath:candidate,finalPath:path.join(workspace,'files','CertaRig_Demo_Draft_2026-11-15.pptx'),explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],pythonExecutable:process.env.CERTARIG_ARTIFACT_PYTHON,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','9144000,6858000','--validate-bullet-geometry','--validate-heading-fit'],fontPolicy:{basis:'reference',families:['Aptos','Aptos SemiBold','Arial Narrow'],referencePath:template,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(template)).digest('hex')},verifyArtifactToolImport:true,receiptPath:path.join(build,'presentation-validation-2026-11-15.json')});
await fs.writeFile(path.join(build,'deck-timing.json'),JSON.stringify({seconds:timing,total_seconds:timing.reduce((a,b)=>a+b,0),live_demo_seconds:timing[6],status:'planned timing; not an attended rehearsal'},null,2));
console.log(JSON.stringify(result));
