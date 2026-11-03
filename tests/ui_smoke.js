// Renderer smoke checks in Node, not a substitute for real-browser visual QA.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../static');
const node={addEventListener(){},remove(){},innerHTML:'',open:false};
const context=vm.createContext({console,Intl,Date,JSON,Number,String,Math,Map,Set,Array,Object,Promise,URL,URLSearchParams,
  document:{querySelector(){return node},addEventListener(){}},window:{addEventListener(){}},location:{hash:''},
  localStorage:{getItem(){return ''},removeItem(){}},setInterval(){},setTimeout(){},clearTimeout(){},fetch(){return new Promise(()=>{})}});
for(const name of ['received-media.js','analytics-report.js','team-operations.js','team-invitations.js','rule-actions.js','graph.js','knowledge-documents.js','assistant.js','shell.js','template-editor.js','business.js','integrations.js','drip-sequences.js','external-agents.js','contact-segments.js','customer-assistant.js','account-recovery.js','account.js','help-widget.js','app.js'])vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),context,{filename:name});
context.actualRefresh=vm.runInContext('refresh',context);
context.fixture={context:{tenant_id:'business-one',user:{id:'owner',name:'Owner'},workspace:{name:'Acme'},role:'admin',workspaces:[]},meta:{live:false},ai:{enabled:false,configured:false},sandbox:false,
  contacts:[{id:'contact',name:'<img src=x onerror=alert(1)>',phone:'919000000001',tags:[],attributes:{},source:'manual',status:'pending',assignee:'owner',automation_hold:true}],
  members:[{id:'owner',name:'Owner'}],deals:[{id:'deal',title:'Real opportunity',contact_id:'contact',owner:'owner',stage:'qualified',amount_minor:129900,currency:'INR'}],tasks:[],messages:[],findings:[],airuns:[],aiagents:[],aichats:[],knowledges:[]};
vm.runInContext('S.data=fixture;S.route="pipeline";S.chat="contact"',context);
let html=vm.runInContext('page()',context);
assert.match(html,/Real opportunity/);assert.match(html,/Qualified/);assert.match(html,/1,299/);assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img src=x/);
html=vm.runInContext('S.route="findings";page()',context);
assert.match(html,/No findings in this view/);assert.match(html,/AI not connected/);assert.match(html,/data-do="review-run" disabled/);
context.fixture.findings=[{id:'finding',run_id:'run',agent_name:'Triage',title:'<script>bad()</script>',details:'Review this inquiry',status:'pending',contact_id:'contact',evidence_ids:[],action:{type:'tag',tag:'Lead'},created:1}];
html=vm.runInContext('page()',context);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>bad/);assert.match(html,/data-decision="approve"/);
vm.runInContext('S.data.context.role="agent"',context);html=vm.runInContext('page()',context);assert.doesNotMatch(html,/data-decision="approve"/);
html=vm.runInContext('S.route="inbox";page()',context);assert.match(html,/Human handling/);assert.match(html,/handoff-resume/);assert.match(html,/crm-contact-task/);
vm.runInContext('S.data.context.role="admin";ensureAIScope();A.tab="agents"',context);
html=vm.runInContext('aiAgentsPage()',context);assert.match(html,/Hire Inbox Triage/);assert.match(html,/Hire Account Health Checker/);assert.match(html,/Your agents/);
vm.runInContext('const originalRenderAI=renderAI;renderAI=()=>{};A.scope=null;showAI("agents");renderAI=originalRenderAI',context);
assert.equal(vm.runInContext('A.tab',context),'agents');
context.fixture.aiagents=[{id:'agent',name:'Scheduled Triage',instructions:'<script>bad()</script>',schedule_enabled:true,next_run:2000000000,last_status:'completed'}];
html=vm.runInContext('aiAgentsPage()',context);assert.match(html,/Pause schedule/);assert.match(html,/&lt;script&gt;/);assert.match(html,/ai-edit-agent/);
vm.runInContext('S.data.context.role="agent"',context);html=vm.runInContext('aiAgentsPage()',context);assert.doesNotMatch(html,/ai-edit-agent/);
async function chatRaceCheck(){
  const fields={'#workspace-ai':{innerHTML:'',remove(){},classList:{toggle(){}}},'#ai-form':{},'#ai-question':{value:'An earlier question'},'#ai-mode':{value:'ask'}};
  context.document.querySelector=s=>fields[s]||node;
  context.fixture.ai={enabled:true,configured:true};context.fixture.aiagents=[];
  vm.runInContext('A.scope=null;ensureAIScope();S.route="campaigns";renderAI()',context);
  let resolve;context.pendingAnswer=new Promise(r=>resolve=r);
  vm.runInContext('act=()=>pendingAnswer;refresh=async()=>{}',context);
  const waiting=fields['#ai-form'].onsubmit({preventDefault(){}});
  await vm.runInContext('aiAction("ai-new",{dataset:{}})',context);
  resolve({id:'job',chat_id:'answer-to-old-chat'});await waiting;
  assert.equal(vm.runInContext('A.chat',context),null,'An old answer must not replace a new chat.');
}
async function sourceLogoutCheck(){
  let resolve,modals=0;context.pendingSource=new Promise(r=>resolve=r);context.recordModal=()=>modals++;
  vm.runInContext('api=()=>pendingSource;showModal=recordModal',context);
  const waiting=vm.runInContext('aiExecutionAction("ai-open-source",{dataset:{contact:"contact",ids:"message"}})',context);
  vm.runInContext('S.data=null',context);
  resolve({contact:{id:'contact',name:'Private customer'},messages:[{body:'Private content',ts:1,direction:'in'}]});
  await waiting;assert.equal(modals,0,'A delayed source response must not show private content after logout.');
}
async function agentBuilderCheck(){
  vm.runInContext('S.data=fixture;S.data.context.role="admin";ensureAIScope();renderAI=()=>{}',context);
  await vm.runInContext('aiAction("ai-mode-agent",{dataset:{}})',context);
  assert.equal(vm.runInContext('A.purpose',context),'agent_builder');assert.equal(vm.runInContext('A.tab',context),'ask');
  const html=vm.runInContext('aiMessage({id:"proposal",role:"assistant",content:"Review",agent_draft:{name:"Question watcher",instructions:"Review questions",cadence:"daily"}})',context);
  assert.match(html,/Review agent/);assert.match(html,/Question watcher/);assert.match(html,/ai-review-proposal/);
  assert.match(vm.runInContext('aiKnowledgePage()',context),/Upload document/);
  assert.match(vm.runInContext('aiMessage({role:"assistant",content:"Policy",knowledge_references:[{label:"Returns",document_id:"doc",chunk_id:"chunk"}]})',context),/Open document passage/);
}
async function documentLogoutCheck(){
  let resolve,modals=0;context.pendingDocument=new Promise(r=>resolve=r);context.recordModal=()=>modals++;
  vm.runInContext('S.data=fixture;api=()=>pendingDocument;showModal=()=>recordModal()',context);
  const waiting=vm.runInContext('documentKnowledgeAction("ai-document-source",{dataset:{document:"doc",chunk:"chunk"}})',context);
  vm.runInContext('S.data=null',context);resolve({title:'Private policy',passage:1,text:'Private text'});
  await waiting;assert.equal(modals,0,'Document sources must not appear after logout.');
}
async function websiteLogoutCheck(){
  let resolve,modals=0;context.pendingWebsite=new Promise(r=>resolve=r);context.recordModal=()=>modals++;
  vm.runInContext('S.data=fixture;act=()=>pendingWebsite;showModal=()=>recordModal()',context);
  const waiting=vm.runInContext('documentKnowledgeAction("ai-document-website-preview",{dataset:{id:"website"}})',context);
  vm.runInContext('S.data=null',context);resolve({title:'Website',url:'https://example.test',text:'Private snapshot'});
  await waiting;assert.equal(modals,0,'Delayed website snapshots must not open after logout.');
}
async function forbiddenWorkspaceCheck(){
  let authScreens=0;context.recordAuth=()=>authScreens++;
  vm.runInContext('S.data=fixture;S.workspace="removed";refresh=actualRefresh;api=async()=>{const error=new Error("Access denied");error.status=403;throw error};renderAuth=()=>recordAuth();toast=()=>{}',context);
  await vm.runInContext('refresh()',context);
  assert.equal(vm.runInContext('S.data',context),null,'Forbidden workspace data must be cleared from the UI.');assert.equal(authScreens,1);
}
async function analyticsScopeCheck(){
  let resolve;context.pendingAnalytics=new Promise(r=>resolve=r);
  vm.runInContext('S.data=fixture;S.route="analytics";render=()=>{};api=()=>pendingAnalytics',context);
  const waiting=vm.runInContext('loadAnalyticsReport("2026-10-01","2026-10-03")',context);
  vm.runInContext('S.data={context:{tenant_id:"other",user:{id:"other-user"}}}',context);resolve({days:[],totals:{inbound:123}});
  await waiting;assert.equal(vm.runInContext('AR.data',context),null,'A delayed report must not populate another workspace.');
}
async function securityLogoutCheck(){
  let resolve,modals=0;context.pendingSecurity=new Promise(r=>resolve=r);context.recordSecurityModal=()=>modals++;
  vm.runInContext('S.data=fixture;api=()=>pendingSecurity;showModal=()=>recordSecurityModal()',context);
  const waiting=vm.runInContext('accountSecurityForm()',context);
  vm.runInContext('S.data=null',context);resolve({enabled:false,recovery_remaining:0});
  await waiting;assert.equal(modals,0,'A delayed security response must not open a dialog after logout.');
}
chatRaceCheck().then(sourceLogoutCheck).then(agentBuilderCheck).then(documentLogoutCheck).then(websiteLogoutCheck).then(analyticsScopeCheck).then(forbiddenWorkspaceCheck).then(securityLogoutCheck).then(()=>console.log('UI renderer, agent builder, chat race and source privacy checks passed. Visual QA remains pending.')).catch(e=>{console.error(e);process.exitCode=1});

vm.runInContext('S.route="commerce"',context);html=vm.runInContext('page()',context);assert.match(html,/No synced products/);assert.match(html,/Sync first page/);assert.doesNotMatch(html,/ENTER_LOCALLY.*value=/);
context.orderFixture={orders:[{id:'order',name:'<script>order</script>',synced:1}],order_links:[{id:'link',order_id:'order',contact_id:'contact'}]};
html=vm.runInContext('customerOrderLinks(orderFixture,true)',context);assert.match(html,/Unlink customer/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>order/);
html=vm.runInContext('customerOrderLinks(orderFixture,false)',context);assert.doesNotMatch(html,/integration-order-unlink/);
context.handoffFixture={handoff:{active:true,reason:'<script>private</script>',created:1,task_id:'task'}};
html=vm.runInContext('customerHandoffInfo(handoffFixture)',context);assert.match(html,/Awaiting human review/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>private/);assert.match(html,/follow-up task/);
vm.runInContext('S.data.context.role="admin";S.data.knowledge_documents=[{id:"web",title:"Website",format:"website",enabled:false,characters:10,chunks:1,url:"https://example.test/<script>",last_success:1,refresh_error:"<script>error</script>"}]',context);
html=vm.runInContext('knowledgeDocumentsPanel()',context);assert.match(html,/Review snapshot/);assert.match(html,/Refresh page/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>error/);
vm.runInContext('S.data.context.role="agent"',context);html=vm.runInContext('knowledgeDocumentsPanel()',context);assert.doesNotMatch(html,/ai-document-website-refresh/);
assert.equal(vm.runInContext('canEditRuleActions([{type:"tag"},{type:"draft"},{type:"handoff"}])',context),true);
assert.equal(vm.runInContext('canEditRuleActions([{type:"draft"},{type:"tag"},{type:"draft"}])',context),false,'The form must retain custom ordering rather than silently rewriting it.');
context.ruleFixture={actions:[{type:'<script>bad</script>'}]};html=vm.runInContext('ruleActionSummary(ruleFixture)',context);assert.doesNotMatch(html,/<script>/);assert.match(html,/&lt;script&gt;/);
context.invitationFixture={workspace:'<script>Workspace</script>',email:'new@example.test',role:'agent',expires:2000000000,existing_account:true};
html=vm.runInContext('invitationMarkup(invitationFixture)',context);assert.match(html,/current password/i);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>Workspace/);assert.doesNotMatch(html,/name="token"/);
context.trafficFixture={days:[{day:'2026-10-01',inbound:2,accepted:1,sent:0,delivered:0,read:0,failed:0,unknown:1,sending:0}]};
html=vm.runInContext('trafficChart(trafficFixture.days)',context);assert.match(html,/2 inbound, 2 outbound attempts/);assert.match(vm.runInContext('analyticsCsv(trafficFixture)',context),/"unknown"/);
vm.runInContext('S.data.received_media=[{id:"received",message_id:"message",filename:"<script>file</script>",kind:"image",mime:"image/png",status:"downloaded",asset_id:"asset"}];S.data.media_status={configured:true}',context);
html=vm.runInContext('receivedAttachment({id:"message"})',context);assert.match(html,/api\/media\?id=asset/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>file/);assert.doesNotMatch(html,/lookaside|Bearer/);
context.ruleTriggerFixture={event:'attribute_changed',trigger_attribute:'<script>field</script>'};html=vm.runInContext('ruleTriggerSummary(ruleTriggerFixture)',context);assert.match(html,/Custom attribute changed/);assert.doesNotMatch(html,/<script>/);

html=vm.runInContext('dripSequencePage()',context);assert.match(html,/Run history/);assert.match(html,/New sequence/);assert.doesNotMatch(html,/Background scheduling and delivery are not enabled/);

vm.runInContext('S.data.sequence_runs=[{id:"run",name:"Stopped journey",status:"active",finished:true,audience:1,created:1,counts:{skipped:1,cancelled:1}}]',context);
html=vm.runInContext('dripSequencePage()',context);assert.match(html,/>Stopped</);assert.doesNotMatch(html,/>Submitted</);

html=vm.runInContext('externalAgentPage()',context);assert.match(html,/Astra \/ Custom AI/);assert.match(html,/New agent/);assert.match(html,/custom agent/);html=vm.runInContext('developerPage()',context);assert.match(html,/unsent reply drafts/);

vm.runInContext('S.data.segments=[{id:"segment",name:"Buyer audience",criteria:{mode:"all",rules:[{field:"tags",operator:"contains",value:"Buyer"}]},updated:1}]',context);html=vm.runInContext('segmentsPage()',context);assert.match(html,/Contact segments/);assert.match(html,/Preview audience/);

html=vm.runInContext('customerAssistantPage()',context);assert.match(html,/Customer support AI/);assert.match(html,/Approved knowledge/);assert.match(html,/No generated replies yet/);

context.noResponseFixture={event:"customer_no_response",wait_seconds:60};html=vm.runInContext("ruleTriggerSummary(noResponseFixture)",context);assert.match(html,/Customer has not replied/);assert.match(html,/60 seconds/);
html=vm.runInContext("noResponseHistoryPanel()",context);assert.match(html,/No-response evaluations/);

context.poolFixture={handoff_strategy:'least_busy',handoff_pool:['removed-member']};
html=vm.runInContext('customerRoutingFields(poolFixture)',context);assert.match(html,/Least-busy member/);assert.match(html,/no longer have workspace access/);assert.match(html,/not browser presence/);
html=vm.runInContext('customerRoutingSummary(poolFixture)',context);assert.match(html,/1 configured members/);
context.routedHandoff={handoff:{active:true,reason:'Needs help',created:1,routing:{strategy:'least_busy',assigned_load:'<script>bad</script>'}}};html=vm.runInContext('customerHandoffInfo(routedHandoff)',context);assert.match(html,/Least-busy team routing/);assert.doesNotMatch(html,/<script>/);

html=vm.runInContext('agentActionFields({allowed_actions:[]})',context);assert.match(html,/information-only findings/);assert.doesNotMatch(html,/ checked/);
html=vm.runInContext('agentActionFields({allowed_actions:["tag"]})',context);assert.equal((html.match(/ checked/g)||[]).length,1);assert.match(html,/data-agent-action="tag" checked/);
assert.equal(vm.runInContext('agentActionSummary({allowed_actions:[]})',context),'Information-only findings');

vm.runInContext('G.graph={start:"attribute",nodes:[{id:"attribute",type:"attribute",field:"service",value:"<script>bad</script>"},{id:"assign",type:"assign",member_id:"removed"},{id:"remove",type:"untag",tag:"Old"}]}',context);
html=vm.runInContext('graphMarkup()',context);assert.match(html,/Set a custom attribute/);assert.match(html,/Assign a teammate/);assert.match(html,/Remove a tag/);assert.match(html,/Unavailable teammate/);assert.doesNotMatch(html,/<script>/);

context.flowDeliveryFixture={id:'test-flow',delivery_mode:'live'};vm.runInContext('S.data.flow_sends=[{flow_id:"test-flow",status:"unknown",updated:1,late_outcome:"<script>bad</script>"}]',context);html=vm.runInContext('flowDeliveryPanel(flowDeliveryFixture)',context);assert.match(html,/Chatbot delivery activity/);assert.match(html,/Acceptance means submission/);assert.doesNotMatch(html,/<script>/);

context.mediaNodeFixture={type:'media',asset_id:'missing',caption:'<script>caption</script>'};html=vm.runInContext('flowResourceFields(mediaNodeFixture)',context);assert.match(html,/Unavailable file/);assert.match(html,/5 MiB/);assert.doesNotMatch(html,/<script>/);
context.templateNodeFixture={type:'template',template_id:'missing'};html=vm.runInContext('flowResourceFields(templateNodeFixture)',context);assert.match(html,/Unavailable template/);assert.match(html,/Meta-approved/);
vm.runInContext('G.graph={start:"media",nodes:[{id:"media",type:"media",asset_id:"missing"},{id:"template",type:"template",template_id:"missing"}]}',context);html=vm.runInContext('graphMarkup()',context);assert.match(html,/Send an attachment/);assert.match(html,/Template message/);assert.doesNotMatch(html,/Template: undefined/);

context.resourceLabelFixture={resource:{kind:'template',template:{name:'<script>bad</script>',language:'en'}}};html=vm.runInContext('flowSendResourceLabel(resourceLabelFixture)',context);assert.match(html,/Template/);assert.doesNotMatch(html,/<script>/);
context.resourceLabelFixture={resource:{kind:'media',asset_id:'removed',media_kind:'document',filename:'<script>file</script>'}};html=vm.runInContext('flowSendResourceLabel(resourceLabelFixture)',context);assert.doesNotMatch(html,/<script>/);assert.doesNotMatch(html,/provider_id|Bearer/);

vm.runInContext('S.initialized=false;S.setupTokenRequired=true;S.deployment="hosted";renderAuth()',context);html=node.innerHTML;assert.match(html,/Deployment setup token/);assert.match(html,/name="setup_token" type="password"/);assert.match(html,/Hosted workspace/);assert.doesNotMatch(html,/value="test-only/);vm.runInContext('S.initialized=true;S.setupTokenRequired=false;S.deployment="local"',context);

vm.runInContext('S.data=fixture;S.data.context.role="admin";S.data.pipeline={stages:[{id:"new",label:"<script>New</script>"},{id:"demo",label:"Demo scheduled"},{id:"won",label:"Won"},{id:"lost",label:"Lost"}],events:[],closure_days:10};S.pipelineOverdue=false',context);html=vm.runInContext('pipelinePage()',context);assert.match(html,/Demo scheduled/);assert.doesNotMatch(html,/<script>/);assert.match(html,/Pipeline settings/);
context.roundRobinFixture={handoff_strategy:'round_robin',handoff_pool:['owner']};html=vm.runInContext('customerRoutingSummary(roundRobinFixture)',context);assert.match(html,/Round-robin team pool/);
vm.runInContext('S.data.knowledge_usage={window_days:30,drafts:2,accepted_submissions:1,handoffs:1,sources:[{title:"<script>Policy</script>",enabled:true,referenced_replies:2}],manual_source_count:1}',context);html=vm.runInContext('knowledgeUsagePanel()',context);assert.match(html,/2 drafts/);assert.match(html,/validated document references/);assert.doesNotMatch(html,/<script>/);

context.pipelineNames="Demo\nNegotiation\r\n";assert.deepEqual(Array.from(vm.runInContext("pipelineNewStageNames(pipelineNames)",context)),["Demo","Negotiation"]);

html=vm.runInContext("accountPasswordFields()",context);assert.match(html,/Current password/);assert.match(html,/all workspaces/);assert.equal((html.match(/type="password"/g)||[]).length,3);assert.doesNotMatch(html,/value="long-enough/);
const navigationContext=vm.createContext({console,S:{route:'flows'},esc:v=>String(v).replace(/&/g,'&amp;'),icon:n=>`<i data-icon="${n}"></i>`});
vm.runInContext(fs.readFileSync(path.join(root,'shell.js'),'utf8'),navigationContext);
html=vm.runInContext('primaryNavigation()',navigationContext);
assert.equal((html.match(/class="navlink/g)||[]).length,13);
assert.equal((html.match(/aria-current="page"/g)||[]).length,1);
assert.match(html,/<a[^>]*href="#rules"[^>]*aria-current="page"/);
assert.match(html,/<button(?=[^>]*data-do="ai-agents-open")(?=[^>]*aria-label="AI Agents)[^>]*>/);
assert.match(html,/title="Commerce &amp; Integrations/);
assert.match(html,/data-icon="pipeline"/);
assert.match(html,/data-icon="developers"/);
for(const label of ['Team Inbox','AI Agents','Sales Pipeline','Settings'])assert.ok(html.includes(`class="nav-text">${label}</span>`));
console.log('Navigation destinations, active section and accessible names passed.');
html=vm.runInContext('mfaCodeField()',context);assert.match(html,/autocomplete="one-time-code"/);assert.doesNotMatch(html,/ required/);
vm.runInContext('S.initialized=true;renderAuth()',context);assert.match(node.innerHTML,/Authenticator or recovery code/);
html=vm.runInContext('invitationMarkup({workspace:"Acme",email:"a@example.test",role:"agent",existing_account:true})',context);assert.match(html,/name="code"/);
html=vm.runInContext('mfaRecoveryMarkup(["<script>bad</script>"])',context);assert.doesNotMatch(html,/<script>/);assert.match(html,/&lt;script&gt;/);

const sensitiveDialog={dataset:{accountSecurity:'true'},innerHTML:'private setup key'};
const securityContext=vm.createContext({$:()=>sensitiveDialog,formSubmit:()=>{}});
vm.runInContext(fs.readFileSync(path.join(root,'account.js'),'utf8'),securityContext);
vm.runInContext('clearSecurityDialog()',securityContext);
assert.equal(sensitiveDialog.innerHTML,'');assert.equal(sensitiveDialog.dataset.accountSecurity,undefined);
assert.equal(vm.runInContext('formSubmit',securityContext),null);

context.publishedFlowFixture={id:'flow',version:2,draft:{revision:3,base_version:2},published_versions:[{version:2,actor:'<script>name</script>',published_at:1}]};
html=vm.runInContext('flowPublishingPanel(publishedFlowFixture)',context);assert.match(html,/Published v2/);assert.match(html,/Draft r3/);assert.match(html,/graph-restore/);assert.doesNotMatch(html,/<script>/);

context.structuredClone=structuredClone;
vm.runInContext('S.data=fixture;S.data.context.role="admin";S.route="flows";S.preview=null;S.data.flows=[{id:"versioned",name:"Versioned",keyword:"help",reply:"Active text",enabled:true,delivery_mode:"draft",version:1,graph:{start:"message",nodes:[{id:"message",type:"message",text:"Active graph text"}]},draft:{revision:2,base_version:1,graph:{start:"message",nodes:[{id:"message",type:"message",text:"My saved draft"}]}},published_versions:[]}];G.id=null;G.dirty=false',context);
html=vm.runInContext('graphPage()',context);assert.match(html,/My saved draft/);assert.match(html,/Save draft/);assert.match(html,/data-do="graph-publish"/);assert.doesNotMatch(html,/Active graph text/);
vm.runInContext('G.dirty=true;S.data.flows[0].version=2;S.data.flows[0].draft.revision=3',context);
vm.runInContext('graphPage()',context);assert.equal(vm.runInContext('G.baseVersion',context),1);assert.equal(vm.runInContext('G.draftRevision',context),2);

context.teamOperationsFixture={teams:[{id:'team',name:'<script>Team</script>',members:['owner'],enabled:true,version:1}],availability:[{user:'owner',status:'available',until:2000000000}],workload:[{user:'owner',assigned:2}],assignments:[{contact_id:'contact',from:'',to:'owner',created:1,source:'team_route'}]};
vm.runInContext('S.data=fixture;S.data.context.role="admin";S.data.team_operations=teamOperationsFixture',context);
html=vm.runInContext('teamOperationsPanel()',context);assert.match(html,/New team/);assert.match(html,/Available/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);
html=vm.runInContext('teamOperationsContact({id:"contact",assignee:""})',context);assert.match(html,/team-route/);assert.match(html,/Recent assignments/);
vm.runInContext('S.data.context.role="agent"',context);html=vm.runInContext('teamOperationsPanel()',context);assert.doesNotMatch(html,/team-edit|team-new/);assert.match(html,/Set my availability/);

vm.runInContext('S.data=fixture;S.data.internal_comments=[{message_id:"note",author:"owner",mentions:["owner"]}];S.data.mention_notifications=[{id:"notice",owner:"owner",contact_id:"contact",author:"owner",read:false,created:1}]',context);
html=vm.runInContext('commentAttribution({id:"note",direction:"note"})',context);assert.match(html,/Owner/);assert.match(html,/@Owner/);assert.equal(vm.runInContext('commentAttribution({id:"note",direction:"in"})',context),'');
html=vm.runInContext('mentionNotificationsMarkup()',context);assert.match(html,/team-mention-open/);assert.match(html,/Unread/);assert.doesNotMatch(html,/<img src=x/);

vm.runInContext('RECOVERY.token="private-test-token"',context);
html=vm.runInContext('passwordRecoveryMarkup("reset")',context);assert.match(html,/Confirm new password/);assert.doesNotMatch(html,/private-test-token/);assert.doesNotMatch(html,/name="token"/);
html=vm.runInContext('passwordRecoveryMarkup("request",false)',context);assert.match(html,/not configured/);assert.doesNotMatch(html,/Send reset link/);
html=vm.runInContext('passwordRecoveryMarkup("request",true)',context);assert.match(html,/Send reset link/);assert.match(html,/type="email"/);

html=vm.runInContext('helpPanel()',context);assert.match(html,/VYBE Connect/);assert.match(html,/guided tour/);assert.match(html,/Astra/);
vm.runInContext('HELP.tab="feedback";HELP.draft="<script>bad</script>"',context);html=vm.runInContext('helpPanel()',context);assert.match(html,/help-feedback-form/);assert.doesNotMatch(html,/<script>/);assert.match(html,/&lt;script&gt;/);
assert.ok(fs.readFileSync(path.join(root,'index.html'),'utf8').includes('<title>VYBE Connect'));
assert.ok(fs.readFileSync(path.join(root,'index.html'),'utf8').includes('/vybe-theme.css'));

vm.runInContext('HELP.draft="private feedback";HELP.rating=5;clearHelpWidget()',context);assert.equal(vm.runInContext('HELP.draft',context),'');assert.equal(vm.runInContext('HELP.rating',context),0);
