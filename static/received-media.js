'use strict';
function receivedAttachment(message){
  const item=(S.data.received_media||[]).find(record=>record.message_id===message.id);if(!item)return '';
  const url=item.asset_id?'/api/media?id='+encodeURIComponent(item.asset_id)+'&workspace='+encodeURIComponent(S.data.context.tenant_id):'';
  let preview='';
  if(url&&item.status==='downloaded'){
    if(item.kind==='image')preview=`<img src="${esc(url)}" alt="${esc(item.filename)}" loading="lazy" style="max-width:100%;max-height:240px;display:block">`;
    else if(item.kind==='audio')preview=`<audio controls preload="none" src="${esc(url)}" aria-label="${esc(item.filename)}"></audio>`;
    else if(item.kind==='video')preview=`<video controls preload="none" src="${esc(url)}" aria-label="${esc(item.filename)}" style="max-width:100%;max-height:260px"></video>`;
    preview+=`<a href="${esc(url)}" target="_blank" rel="noopener">Open private file · ${esc(item.filename)}</a>`;
  }
  return `<div class="received-attachment"><p class="hint">${esc(item.filename)} · ${esc(item.mime||item.kind)} · ${esc(item.status)}</p>${preview}${item.error?`<p class="error">${esc(item.error)}</p>`:''}${item.status!=='unavailable'?btn(item.status==='downloaded'?'Retrieve attachment':item.status==='failed'?'Retry retrieval':'Retrieve from Meta','received-media-fetch',`data-id="${esc(item.id)}" ${item.status==='downloading'||!S.data.media_status?.configured?'disabled':''}`,'small'):''}<p class="hint">Retrieval contacts Meta and stores a private copy. AI content inspection is not enabled.</p></div>`;
}
async function receivedMediaAction(action,el){
  if(action!=='received-media-fetch')return;
  const tenant=S.data.context.tenant_id,user=S.data.context.user.id;
  const same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user;
  el.disabled=true;
  try{await act('media.receive.download',{id:el.dataset.id});if(!same())return;await refresh();if(same())toast('Private attachment is ready. No message was sent.')}
  finally{if(el.isConnected)el.disabled=false}
}
