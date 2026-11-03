'use strict';
// Directory filtering uses only the current authenticated page's rendered cards.
function agentDirectoryToolbar(id,label,statuses){
 return `<div class="agent-directory-toolbar"><label><span class="sr-only">Search ${esc(label)}</span><input type="search" data-agent-search="${id}" placeholder="Search ${esc(label)}" aria-label="Search ${esc(label)}"></label><label><span class="sr-only">Filter ${esc(label)} by status</span><select data-agent-filter="${id}" aria-label="Filter ${esc(label)} by status"><option value="all">All statuses</option>${statuses.map(([value,text])=>`<option value="${value}">${esc(text)}</option>`).join('')}</select></label><span data-agent-count="${id}" role="status" aria-live="polite"></span></div>`;
}
function agentDirectoryMatches(name,status,query,filter){return name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())&&(filter==='all'||filter===status)}
function filterAgentDirectory(id){
 const search=document.querySelector(`[data-agent-search="${id}"]`),filter=document.querySelector(`[data-agent-filter="${id}"]`);
 if(!search||!filter)return;
 const cards=[...document.querySelectorAll(`[data-agent-directory="${id}"]`)];let visible=0;
 for(const card of cards){card.hidden=!agentDirectoryMatches(card.dataset.agentName,card.dataset.agentStatus,search.value,filter.value);if(!card.hidden)visible++}
 const count=document.querySelector(`[data-agent-count="${id}"]`);if(count)count.textContent=`${visible} of ${cards.length} agents`;
 const empty=document.querySelector(`[data-agent-empty="${id}"]`);if(empty)empty.hidden=visible>0||cards.length===0;
}
function agentCopyDraft(agent){
 if(!agent)throw new Error('Agent is unavailable. Refresh the directory.');
 return {name:(agent.name+' (copy)').slice(0,100),instructions:agent.instructions,allowed_actions:[...(agent.allowed_actions??Object.keys(agentActionLabels))]};
}
function agentConnectionState(agent){return !agent.enabled?'disabled':agent.connection.enabled&&agent.connection.configured?'configured':'setup'}
document.addEventListener('input',event=>{if(event.target.dataset.agentSearch)filterAgentDirectory(event.target.dataset.agentSearch)});
document.addEventListener('change',event=>{if(event.target.dataset.agentFilter)filterAgentDirectory(event.target.dataset.agentFilter)});
