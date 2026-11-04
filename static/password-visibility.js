'use strict';
function passwordControlMarkup(input,id,label){
 return `<div class="password-control">${input}<button type="button" class="password-visibility" data-password-target="${esc(id)}" data-password-label="${esc(label)}" aria-controls="${esc(id)}" aria-label="Show ${esc(label)}" aria-pressed="false">Show</button></div>`;
}
document.addEventListener('click',event=>{
 const button=event.target.closest?.('[data-password-target]');if(!button)return;
 const input=document.getElementById(button.dataset.passwordTarget);
 if(!input||input.tagName!=='INPUT'||!['password','text'].includes(input.type)||input.closest('.password-control')!==button.closest('.password-control'))return;
 event.preventDefault();const visible=input.type==='password';input.type=visible?'text':'password';button.textContent=visible?'Hide':'Show';button.setAttribute('aria-pressed',String(visible));button.setAttribute('aria-label',(visible?'Hide ':'Show ')+(button.dataset.passwordLabel||'password'));
});
