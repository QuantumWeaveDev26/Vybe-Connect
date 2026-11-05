'use strict';
function knowledgeDocumentsPanel(){
  const admin=S.data.context.role==='admin';
  return `<h3>Documents and website pages</h3><p class="hint">TXT, Markdown, CSV, DOCX and text-based PDF, or an approved public UTF-8 website page · 1 MiB each · up to 20 indexed sources. Relevant excerpts are retrieved locally. Full-site crawling and semantic search remain pending.</p>${admin?btn('Upload document','ai-document-upload','','primary small')+btn('Add website page','ai-document-website-add','','small'):''}${(S.data.knowledge_documents||[]).map(d=>`<article class="ai-agent"><strong>${esc(d.title)}</strong> ${badge(d.enabled?'Indexed and available':'Disabled',d.enabled?'':'gray')}<p class="hint">${esc(d.format.toUpperCase())} · ${d.characters.toLocaleString()} characters · ${d.chunks} passages</p>${d.format==='website'?`<p class="hint">${esc(d.url)}<br>Last successful fetch: ${esc(new Date(d.last_success*1000).toLocaleString())} · manual refresh</p>${d.refresh_error?`<p class="error">${esc(d.refresh_error)}</p>`:''}`:''}${admin?(d.format==='website'?btn('Review snapshot','ai-document-website-preview',`data-id="${esc(d.id)}"`,'small')+btn('Refresh page','ai-document-website-refresh',`data-id="${esc(d.id)}"`,'small'):'')+btn(d.enabled?'Disable':'Enable','ai-document-toggle',`data-id="${esc(d.id)}"`,'small')+btn('Delete','ai-document-delete',`data-id="${esc(d.id)}"`,'small'):''}</article>`).join('')||'<p class="hint">No indexed documents or pages yet.</p>'}`;
}
function knowledgeReferenceCards(message){return (message.knowledge_references||[]).map(r=>`<div class="ai-source"><strong>${esc(r.label)}</strong>${btn('Open document passage','ai-document-source',`data-document="${esc(r.document_id)}" data-chunk="${esc(r.chunk_id)}"`,'small')}</div>`).join('')}
async function documentKnowledgeAction(action,el){
  const id=el.dataset.id,tenant=S.data.context.tenant_id,user=S.data.context.user.id;
  const same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user;
  if(action==='ai-document-website-add'){
    const prefix='TW_KNOWLEDGE_WEB_'+tenant.toUpperCase()+'_';
    const selfService=S.data.knowledge_web_self_service===true;
    return showModal('Add website knowledge page',field('title','Source title')+field('url','Public HTTPS page URL','','url')+(selfService?'<label class="api-token-scope"><input type="checkbox" id="allow-page-fetch" name="allow_fetch" required> Allow this public page to be fetched for my workspace.</label><p class="hint">One public page, without login, cookies, scripts or redirects. Review its snapshot before enabling. Delete the source to revoke its page permission.</p>':`<p class="hint">One approved public page. Ask your operator to allow its exact origin in <code>${esc(prefix)}ALLOWED_ORIGINS</code>.</p>`),async data=>{
      if(!same())throw new Error('Workspace changed. Reopen this form.');if(selfService&&data.allow_fetch!==true)throw new Error('Confirm permission to fetch this page.');await act('knowledge.website.add',data);if(!same())return;$('#modal').close();await refresh();renderAI();toast('Page indexed but disabled. Review the snapshot before enabling.');
    },'Fetch and index page');
  }
  if(action==='ai-document-website-refresh')return showModal('Refresh website snapshot','<p>This fetches the same public page again. A successful refresh replaces its passages; previous citations may become unavailable. A failed refresh keeps the last successful snapshot. Existing enabled and customer-source approval settings are preserved.</p>',async()=>{
    if(!same())throw new Error('Workspace changed.');try{await act('knowledge.website.refresh',{id})}catch(error){if(same()){await refresh();renderAI()}throw error}if(!same())return;$('#modal').close();await refresh();renderAI();toast('Website snapshot refreshed.');
  },'Fetch fresh snapshot');
  if(action==='ai-document-website-preview'){
    const source=await act('knowledge.website.preview',{id});if(!same())return;
    return showModal(source.title,`<p class="hint">${esc(source.url)} · indexed snapshot${source.truncated?' · first three passages only':''}</p><p class="knowledge-content">${esc(source.text)}</p>`,()=>$('#modal').close(),'Close');
  }
  if(action==='ai-document-upload')return showModal('Upload business knowledge','<div class="field"><label for="knowledge-file">Document · TXT, MD, CSV, DOCX or PDF</label><input id="knowledge-file" type="file" accept=".txt,.md,.csv,.docx,.pdf" required></div><p class="hint">Text is extracted and indexed locally. PDFs must contain text, be unencrypted and have at most 40 pages. Uploading does not invoke an AI provider. Text in a source is reference material, never permission for an agent to act.</p>',async()=>{const file=$('#knowledge-file').files[0];if(!file||file.size>1048576)throw new Error('Choose a supported document up to 1 MiB.');if(!same())throw new Error('Workspace changed. Reopen the uploader.');await api('/api/knowledge-upload?name='+encodeURIComponent(file.name),{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});if(!same())return;$('#modal').close();await refresh();renderAI();toast('Document indexed locally.');},'Upload and index');
  if(action==='ai-document-toggle'){const document=S.data.knowledge_documents.find(d=>d.id===id);await act('knowledge.document.update',{id,enabled:!document.enabled});await refresh();return renderAI()}
  if(action==='ai-document-delete')return showModal('Delete indexed document','<p>This removes its passages from new requests. Earlier AI answers remain in chat history.</p>',async()=>{if(!same())throw new Error('Workspace changed. Reopen this document.');await act('knowledge.document.delete',{id});$('#modal').close();await refresh();renderAI()},'Delete document');
  if(action==='ai-document-source'){
    const passage=await api('/api/knowledge-source?document_id='+encodeURIComponent(el.dataset.document)+'&chunk_id='+encodeURIComponent(el.dataset.chunk));
    if(!same()||!$('#workspace-ai'))return;
    return showModal(passage.title,`<p class="hint">Passage ${passage.passage} · current indexed source</p><p class="knowledge-content">${esc(passage.text)}</p>`,()=>$('#modal').close(),'Close');
  }
}
