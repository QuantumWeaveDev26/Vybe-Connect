'use strict';
const AR={scope:null,start:null,end:null,data:null,error:'',pending:false,request:0};
const reportStates=['accepted','sent','delivered','read','failed','unknown','sending'];
function clearAnalyticsReport(){AR.scope=null;AR.data=null;AR.pending=false;AR.error='';AR.request++}
function reportScope(){return S.data?S.data.context.tenant_id+':'+S.data.context.user.id:null}
function reportCurrent(scope,request){return AR.scope===scope&&AR.request===request&&reportScope()===scope}
function outboundCount(row){return reportStates.reduce((sum,key)=>sum+(row[key]||0),0)}
async function fetchAnalyticsReport(scope,request,start,end){
  if(!reportCurrent(scope,request))return;
  try{
    const report=await api('/api/analytics?from='+encodeURIComponent(start)+'&to='+encodeURIComponent(end));
    if(!reportCurrent(scope,request))return;AR.data=report;AR.error='';
  }catch(error){if(!reportCurrent(scope,request))return;AR.error=error.message}
  if(!reportCurrent(scope,request))return;AR.pending=false;if(S.route==='analytics')render();
}
function loadAnalyticsReport(start,end){
  AR.scope=reportScope();AR.start=start;AR.end=end;AR.data=null;AR.error='';AR.pending=true;const request=++AR.request;
  if(S.route==='analytics')render();return fetchAnalyticsReport(AR.scope,request,start,end);
}
function trafficChart(days){
  const maximum=Math.max(1,...days.map(day=>Math.max(day.inbound,outboundCount(day)))),step=880/Math.max(1,days.length),width=Math.max(.5,Math.min(14,step/2-1));
  return `<svg viewBox="0 0 960 220" role="img" aria-label="Daily recorded inbound and outbound messages" style="width:100%;max-height:260px"><title>Recorded real traffic, UTC dates</title><line x1="40" y1="180" x2="930" y2="180" stroke="#cbd5e1"/>${days.map((day,index)=>{const inbound=day.inbound/maximum*150,outbound=outboundCount(day)/maximum*150,x=44+index*step;return `<g><title>${esc(day.day)} UTC: ${day.inbound} inbound, ${outboundCount(day)} outbound attempts</title><rect x="${x}" y="${180-inbound}" width="${width}" height="${inbound}" fill="#13a474"/><rect x="${x+width+1}" y="${180-outbound}" width="${width}" height="${outbound}" fill="#64748b"/></g>`}).join('')}<text x="40" y="205" fill="#64748b" font-size="12">${esc(days[0]?.day||'')}</text><text x="930" y="205" text-anchor="end" fill="#64748b" font-size="12">${esc(days.at(-1)?.day||'')}</text></svg>`;
}
function realAnalyticsPage(){
  if(S.data.permissions?.reports===false){clearAnalyticsReport();return pagehead('Analytics','')+'<p>Reporting access is restricted by your administrator.</p>'}
  const scope=reportScope();
  if(AR.scope!==scope){AR.scope=scope;AR.data=null;AR.error='';AR.pending=false;AR.request++}
  if(!AR.start){const end=new Date();AR.end=end.toISOString().slice(0,10);AR.start=new Date(end.getTime()-13*86400000).toISOString().slice(0,10)}
  if(!AR.data&&!AR.pending&&!AR.error){AR.pending=true;const request=++AR.request;Promise.resolve().then(()=>fetchAnalyticsReport(scope,request,AR.start,AR.end))}
  const report=AR.data,totals=report?.totals,d=S.data;
  return pagehead('Workspace analytics','Messages, calls and team activity · UTC dates.',btn('Export report CSV','analytics-export',!report||AR.pending||S.data.permissions?.exports===false?'disabled':'','small'))+`<section class="card"><div class="cardbody"><div class="buttons"><div class="field"><label for="analytics-from">From date · UTC</label><input id="analytics-from" type="date" value="${esc(AR.start)}"></div><div class="field"><label for="analytics-to">Through date · UTC</label><input id="analytics-to" type="date" value="${esc(AR.end)}"></div>${btn('Load report','analytics-load',AR.pending?'disabled':'','primary')}</div><details class="report-details"><summary>About this report</summary><p>Choose up to 366 days. Messages are grouped by creation date, using their latest recorded status. Later delivery updates can change earlier totals.</p></details>${AR.pending?'<p>Loading recorded message totals…</p>':''}${AR.error?`<p class="error">${esc(AR.error)}</p>`:''}</div></section>`+(report?`<div class="stats">${stat('Real inbound',totals.inbound,'Customer events recorded in this period','inbox')}${stat('Accepted or later',totals.accepted+totals.sent+totals.delivered+totals.read,'Provider acceptance is separate from delivery','check')}${stat('Delivery recorded',totals.delivered+totals.read,'Delivered or read status recorded','check')}${stat('Read recorded',totals.read,'Read status recorded','contacts')}</div><section class="card"><div class="cardhead"><h2>Daily traffic</h2>${badge(report.contacts+' distinct contacts','gray')}</div><div class="cardbody"><p class="hint">Green: inbound · Gray: outbound attempts</p>${trafficChart(report.days)}<p class="hint">Failed: ${totals.failed} · Unknown: ${totals.unknown} · In flight: ${totals.sending}. These states do not establish delivery.</p></div><div class="tablewrap" style="max-height:380px;overflow:auto"><table><caption>Latest recorded state by message date, UTC</caption><thead><tr><th>Date</th><th>Inbound</th>${reportStates.map(state=>`<th>${esc(state)}</th>`).join('')}</tr></thead><tbody>${report.days.map(day=>`<tr><td>${esc(day.day)}</td><td>${day.inbound}</td>${reportStates.map(state=>`<td>${day[state]}</td>`).join('')}</tr>`).join('')}</tbody></table></div></section>`:'')+(report?operationalAnalytics(report.operations):'')+`<section class="card"><div class="cardhead"><h2>Current operator workload</h2>${badge('Present-time snapshot','gray')}</div><div class="tablewrap"><table><thead><tr><th>Team member</th><th>Assigned</th><th>Open</th><th>Pending</th><th>Solved</th></tr></thead><tbody>${d.members.map(member=>{const contacts=d.contacts.filter(c=>c.assignee===member.id);return `<tr><td>${esc(member.name)}</td><td>${contacts.length}</td>${['open','pending','solved'].map(status=>`<td>${contacts.filter(c=>c.status===status).length}</td>`).join('')}</tr>`}).join('')}</tbody></table></div></section><details class="report-details"><summary>What these totals include</summary><p>Recorded customer messages only. Drafts, internal notes and simulations are excluded. These totals are not a provider reconciliation or revenue report.</p></details>`;
}
function analyticsCsv(report){
  const keys=['day','inbound',...reportStates],cell=value=>{let text=String(value??'');if(/^[=+@\-\t\r]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"'};
  return [keys,...report.days.map(day=>keys.map(key=>day[key]))].map(row=>row.map(cell).join(',')).join('\r\n');
}
async function analyticsAction(action){
  if(action==='analytics-load')return loadAnalyticsReport($('#analytics-from').value,$('#analytics-to').value);
  if(action==='analytics-export'){
    if(!AR.data||AR.pending||AR.scope!==reportScope())throw new Error('Load a report for this workspace first.');
    const scope=reportScope(),request=AR.request;const result=await api('/api/analytics?from='+encodeURIComponent(AR.start)+'&to='+encodeURIComponent(AR.end)+'&export=csv');
    if(scope!==reportScope()||AR.scope!==scope||request!==AR.request)throw new Error('Report changed. Export again.');
    const url=URL.createObjectURL(new Blob(['\ufeff'+result.csv],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download='teamwave-traffic-'+AR.data.start+'-'+AR.data.end+'.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
}

function operationalAnalytics(o){
 if(!o)return '';const duration=v=>v===null||v===undefined?'—':esc(v)+'s',c=o.calls;
 return `<section class="card"><div class="cardhead"><h2>Response and resolution</h2></div><div class="cardbody"><div class="tablewrap"><table><thead><tr><th>Reply cycles</th><th>Average response</th><th>Awaiting reply</th><th>Recorded resolutions</th><th>Average resolution</th><th>Timed resolution samples</th></tr></thead><tbody><tr><td>${o.responses}</td><td>${duration(o.average_response_seconds)}</td><td>${o.awaiting_response}</td><td>${o.resolved}</td><td>${duration(o.average_resolution_seconds)}</td><td>${o.resolution_samples}</td></tr></tbody></table></div><p class="hint">${esc(o.timing_basis)}</p></div></section><section class="card"><div class="cardhead"><h2>Call activity</h2></div><div class="cardbody"><p>${c.total} calls · ${c.inbound} inbound · ${c.outbound} outbound · ${c.connected} connected · ${c.connected_seconds}s recorded connected time (${c.duration_samples} completed samples)</p><p class="hint">Rejected: ${c.rejected} · Failed: ${c.failed} · Unknown: ${c.unknown}. Missing historical timestamps are excluded from durations.</p></div></section><section class="card"><div class="cardhead"><h2>Operator activity in this period</h2></div><div class="tablewrap"><table><thead><tr><th>Teammate</th><th>Assignments received</th><th>Resolutions recorded</th><th>Calls owned</th></tr></thead><tbody>${o.operators.map(m=>`<tr><td>${esc(m.name)}</td><td>${m.assignments}</td><td>${m.resolved}</td><td>${m.calls}</td></tr>`).join('')}</tbody></table></div></section>`;
}
