'use strict';
// Network-only app: never cache accounts, conversations, API responses or old builds.
const OFFLINE=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#6037d6"><title>VYBE Connect · Offline</title><style>body{margin:0;padding:28px;font:16px/1.6 system-ui,sans-serif;background:#f7f7fa;color:#292735;min-height:80vh;display:grid;place-content:center}main{max-width:420px;background:white;padding:28px;border:1px solid #e8e6ee;border-radius:18px}h1{font-size:26px;line-height:1.2}a{display:inline-block;padding:12px 18px;background:#6037d6;color:white;border-radius:10px;text-decoration:none}p{color:#777280}</style><main><strong>VYBE Connect</strong><h1>You're offline</h1><p>Reconnect to open your workspace. Messages, changes and AI requests are not sent while offline.</p><a href="/">Try again</a></main></html>`;
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);
 if(request.method!=='GET'||request.mode!=='navigate'||url.origin!==self.location.origin)return;
 event.respondWith(fetch(request,{cache:'no-store'}).catch(()=>new Response(OFFLINE,{status:503,headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"}})));
});
