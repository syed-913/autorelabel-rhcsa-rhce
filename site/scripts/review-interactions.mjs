import {assertInteractionReport} from './assert-interactions.mjs';
import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir,mkdtemp,rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {tmpdir} from 'node:os';

const output=fileURLToPath(new URL('../qa/renders/',import.meta.url));
const base=(process.env.SITE_PREVIEW_URL||'http://127.0.0.1:4321/autorelabel-rhcsa-rhce/').replace(/\/?$/,'/');
const previewOrigin=new URL(base).origin;
const profile=await mkdtemp(join(tmpdir(),'autorelabel-review-'));
const axe=await readFile(new URL('../node_modules/axe-core/axe.min.js',import.meta.url),'utf8');
const chrome=spawn(process.env.CHROME_PATH||'google-chrome',['--headless','--blink-settings=primaryPointerType=4,availablePointerTypes=4,primaryHoverType=2,availableHoverTypes=2','--no-sandbox','--disable-gpu','--disable-background-networking','--disable-default-apps','--disable-extensions','--disable-sync','--no-first-run','--hide-scrollbars','--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+profile],{stdio:['ignore','ignore','pipe']});
const endpoint=await new Promise((resolve,reject)=>{let log='';chrome.stderr.on('data',data=>{log+=data;const match=log.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(match)resolve(match[1]);});chrome.once('error',reject);chrome.once('exit',code=>reject(new Error(`Renderer exit ${code}: ${log.slice(-1000)}`)));});
const socket=new WebSocket(endpoint);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let sequence=0;
const pending=new Map();
const traces=new Map();
socket.addEventListener('message',event=>{
  const m=JSON.parse(event.data);
  if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);clearTimeout(p.timeout);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);}
  if(m.sessionId&&traces.has(m.sessionId)){
    const trace=traces.get(m.sessionId);
    if(m.method==='Network.requestWillBeSent'&&/^https?:/.test(m.params.request.url)&&!m.params.request.url.startsWith(previewOrigin+'/'))trace.external.push(m.params.request.url);
    if(m.method==='Runtime.exceptionThrown')trace.errors.push(m.params.exceptionDetails.text+' '+(m.params.exceptionDetails.exception?.description||''));
    if(m.method==='Network.responseReceived'&&m.params.response.status>=400)trace.responses.push({url:m.params.response.url,status:m.params.response.status});
  }
});
function send(method,params={},sessionId){return new Promise((resolve,reject)=>{const id=++sequence;const timeout=setTimeout(()=>{pending.delete(id);reject(new Error('Timed out: '+method));},30000);pending.set(id,{resolve,reject,timeout});socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));});}
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function evaluate(page,expression){const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true},page.sessionId);if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
async function open(name,width,{dark=false,reduced=false}={}){
  const {browserContextId}=await send('Target.createBrowserContext');
  await send('Browser.grantPermissions',{browserContextId,origin:previewOrigin,permissions:['clipboardReadWrite','clipboardSanitizedWrite']});
  const {targetId}=await send('Target.createTarget',{url:'about:blank',browserContextId});
  const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
  traces.set(sessionId,{external:[],errors:[],responses:[]});
  const page={sessionId,targetId,browserContextId,width,name};
  await send('Page.enable',{},sessionId);await send('Runtime.enable',{},sessionId);await send('Network.enable',{},sessionId);
  await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width===390,screenWidth:width,screenHeight:1000},sessionId);
  await send('Emulation.setTouchEmulationEnabled',{enabled:width===390,maxTouchPoints:1},sessionId);
  await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:dark?'dark':'light'},{name:'prefers-reduced-motion',value:reduced?'reduce':'no-preference'}]},sessionId);
  await send('Page.navigate',{url:base+name},sessionId);
  await evaluate(page,`(async()=>{if(document.readyState!=='complete')await new Promise(r=>addEventListener('load',r,{once:true}));document.body.getBoundingClientRect();document.images&&[...document.images].forEach(i=>i.loading='eager');await document.fonts.ready;await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await new Promise(r=>setTimeout(r,550));return true;})()`);
  return page;
}
async function close(page){await send('Target.closeTarget',{targetId:page.targetId});await send('Target.disposeBrowserContext',{browserContextId:page.browserContextId});}
async function metrics(page){return evaluate(page,`({width:innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,height:Math.ceil(document.documentElement.scrollHeight),h1:document.querySelectorAll('h1').length,fonts:document.fonts.status,brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src),theme:getComputedStyle(document.body).backgroundColor,navVisible:getComputedStyle(document.querySelector('.primary-nav')).display,menuVisible:getComputedStyle(document.querySelector('.menu-trigger')).display})`);}
async function screenshot(page,file,{full=true,selector=null}={}){
  await evaluate(page,`document.querySelectorAll('.ink-trace').forEach(p=>p.getAnimations().forEach(a=>{a.currentTime=4000;}));true`);
  let clip;
  if(selector){clip=await evaluate(page,`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return{x:Math.max(0,r.x+scrollX),y:Math.max(0,r.y+scrollY),width:Math.ceil(r.width),height:Math.ceil(r.height),scale:1};})()`);}
  else {const m=await metrics(page);clip={x:0,y:full?0:await evaluate(page,'scrollY'),width:page.width,height:full?m.height:1000,scale:1};}
  const result=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,fromSurface:true,clip},page.sessionId);
  const buffer=Buffer.from(result.data,'base64');await writeFile(output+'/'+file+'.png',buffer);
  return{file:file+'.png',width:buffer.readUInt32BE(16),height:buffer.readUInt32BE(20),bytes:buffer.length};
}
async function accessibility(page){await send('Runtime.evaluate',{expression:axe},page.sessionId);return evaluate(page,`(async()=>{const r=await axe.run(document);return{version:axe.version,violations:r.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,html:n.html,summary:n.failureSummary}))})),passes:r.passes.length,incomplete:r.incomplete.map(i=>({id:i.id,count:i.nodes.length}))};})()`);}
async function key(page,value){const vk={Enter:13,' ':32,Tab:9,Escape:27,ArrowRight:39,ArrowLeft:37,Home:36,End:35,t:84,'?':191,'/':191}[value];for(const type of ['keyDown','keyUp'])await send('Input.dispatchKeyEvent',{type,key:value,code:value===' '?'Space':value,...(vk?{windowsVirtualKeyCode:vk}:{}),...(type==='keyDown'&&(value==='Enter'||value===' ')?{text:value==='Enter'?'\r':' ',unmodifiedText:value==='Enter'?'\r':' '}:{} )},page.sessionId);}

async function tabUntil(page,predicate,limit=90){
  for(let n=0;n<limit;n++){if(await evaluate(page,predicate))return n;await key(page,'Tab');}
  throw new Error('Keyboard target was not reached: '+predicate);
}
async function waitFor(page,predicate){for(let n=0;n<80;n++){if(await evaluate(page,predicate))return;await delay(50);}throw new Error('Condition timed out: '+predicate);}
await mkdir(output,{recursive:true});
const report={};
try{
  const page=await open('',390);await send('Page.bringToFront',{},page.sessionId);
  await tabUntil(page,`document.activeElement.matches('[data-open-menu]')`);await key(page,'Enter');
  report.menuKeyboard=await evaluate(page,`({open:document.querySelector('[data-site-menu]').open,first:document.activeElement.textContent.trim()})`);
  await key(page,'Enter');await waitFor(page,`location.pathname.endsWith('/start/')&&Boolean(document.getElementById('tab-ubuntu'))`);await delay(350);
  await tabUntil(page,`document.activeElement.id==='tab-ubuntu'`);await key(page,'ArrowRight');await key(page,'Tab');
  report.distroKeyboard=await evaluate(page,`({selected:document.querySelector('[role=tab][aria-selected=true]').id,target:document.activeElement.dataset.copyTarget})`);
  await key(page,'Enter');await delay(100);
  report.distroKeyboard.copied=await evaluate(page,`navigator.clipboard.readText().then(t=>t===document.getElementById('install-fedora-all').dataset.command)`);
  await key(page,'g');await key(page,'t');await waitFor(page,`location.pathname.endsWith('/tasks/')&&Boolean(document.querySelector('[data-task-bank]'))`);await delay(350);
  await key(page,'/');report.localSearchShortcut=await evaluate(page,`document.activeElement.matches('[data-main-search]')`);
  await send('Input.insertText',{text:'systemd'},page.sessionId);await key(page,'Enter');await delay(200);
  report.taskKeyboard=await evaluate(page,`({query:location.search,count:document.querySelector('[data-bank-count]').textContent,historyState:history.state})`);
  await tabUntil(page,`document.activeElement.matches('[data-clear-filters]')`);
  await key(page,'g');await key(page,'h');await waitFor(page,`location.pathname===${JSON.stringify(new URL(base).pathname)}&&Boolean(document.querySelector('.hero-copy'))`);await delay(350);
  await evaluate(page,`history.back();true`);await waitFor(page,`location.pathname.endsWith('/tasks/')&&Boolean(document.querySelector('[data-task-bank]'))`);await delay(350);
  report.backPreservesFilter=await evaluate(page,`({query:location.search,value:document.querySelector('[data-main-search]').value,count:document.querySelector('[data-bank-count]').textContent,active:[...document.querySelectorAll('.primary-nav a[aria-current]')].map(a=>a.textContent)})`);
  await close(page);

  for(const reduced of [false,true]){
    const faq=await open('faq/',390,{reduced});await send('Page.bringToFront',{},faq.sessionId);
    await tabUntil(faq,`document.activeElement.matches('.accordion summary')`);
    const start=await evaluate(faq,`document.querySelector('.accordion details').open`);await key(faq,'Enter');await delay(400);
    const opened=await evaluate(faq,`document.querySelector('.accordion details').open`);await key(faq,' ');await delay(350);
    const closed=await evaluate(faq,`document.querySelector('.accordion details').open`);
    await key(faq,'Enter');await delay(70);await key(faq,' ');await delay(350);
    report['faqKeyboard'+(reduced?'Reduced':'')]=await evaluate(faq,`({start:${start},opened:${opened},closed:${closed},rapidClosed:!document.querySelector('.accordion details').open,expanded:document.querySelector('.accordion details').dataset.expanded,iconTransition:getComputedStyle(document.querySelector('.accordion .icon')).transitionDuration})`);
    await close(faq);
  }

  report.labs=[];
  for(const width of [1440,390])for(const route of ['rhcsa/','rhce/']){
    const page=await open(route,width);await send('Page.bringToFront',{},page.sessionId);
    await tabUntil(page,`document.activeElement.matches('[data-vm]')`);await key(page,'Tab');await key(page,'Enter');
    const enter=await evaluate(page,`({selected:document.activeElement.getAttribute('aria-pressed'),id:document.activeElement.dataset.vm,title:document.querySelector('[data-vm-title]').textContent})`);
    await key(page,'Tab');await key(page,' ');await delay(100);
    const space=await evaluate(page,`({selected:document.activeElement.getAttribute('aria-pressed'),id:document.activeElement.dataset.vm,title:document.querySelector('[data-vm-title]').textContent})`);
    const info=await evaluate(page,`(()=>{const v=document.querySelector('.lab-drawing'),svg=v.querySelector('svg'),label=svg.querySelector('.lab-node text'),address=svg.querySelector('.lab-address');return{width:innerWidth,pageWidth:document.documentElement.scrollWidth,viewport:v.clientWidth,drawing:svg.getBoundingClientRect().width,scrollLeft:v.scrollLeft,labelPixels:parseFloat(getComputedStyle(label).fontSize)*label.getScreenCTM().a,addressPixels:parseFloat(getComputedStyle(address).fontSize)*address.getScreenCTM().a};})()`);
    report.labs.push({route,width,enter,space,...info});
    if(width===390){await delay(600);await screenshot(page,route.slice(0,-1)+'-lab-focus-390',{full:false});}
    await close(page);
  }

  const home=await open('',1440);await send('Page.bringToFront',{},home.sessionId);
  await tabUntil(home,`document.activeElement.matches('[data-sim-log]')`);await delay(500);await key(home,'e');
  await tabUntil(home,`document.activeElement.matches('[data-sim-command]')`);await send('Input.insertText',{text:'rd.break'},home.sessionId);await key(home,'Enter');await delay(80);
  for(const type of ['keyDown','keyUp'])await send('Input.dispatchKeyEvent',{type,key:'x',code:'KeyX',windowsVirtualKeyCode:88,modifiers:type==='keyDown'?2:0},home.sessionId);
  await delay(80);await tabUntil(home,`document.activeElement.matches('[data-sim-command]')`);await delay(350);
  for(const command of ['mount -o remount,rw /sysroot','chroot /sysroot','passwd root','touch /.autorelabel','exit','reboot']){await send('Input.insertText',{text:command},home.sessionId);await key(home,'Enter');await delay(50);}
  report.consoleKeyboard=await evaluate(home,`({status:document.querySelector('[data-sim-status]').textContent,log:document.querySelector('[data-sim-log]').textContent})`);
  await evaluate(home,`document.querySelector('[data-sim-reset]').click();for(let i=0;i<6;i++)document.querySelector('[data-sim-actions] button').click();[...document.querySelectorAll('[data-sim-actions] button')].find(b=>b.textContent.includes('Skip')).click();for(let i=0;i<2;i++)document.querySelector('[data-sim-actions] button').click();true`);
  report.consoleSkip=await evaluate(home,`document.querySelector('[data-sim-status]').textContent`);
  await evaluate(home,`Object.defineProperty(navigator.clipboard,'writeText',{configurable:true,value:async()=>{throw new Error('Clipboard denied for fallback verification');}});document.querySelector('[data-copy-target=final-clone-all]').click();true`);await delay(100);
  report.clipboardFallback=await evaluate(home,`({selection:getSelection().toString(),toast:document.querySelector('[data-toast]').textContent})`);
  await close(home);

  const cursor=await open('',1440);
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:260,y:330},cursor.sessionId);await delay(100);
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:260,y:330,button:'left',buttons:1,clickCount:1},cursor.sessionId);
  const pressed=await evaluate(cursor,`({visible:document.documentElement.dataset.cursorVisible,pressed:document.querySelector('[data-cursor-ring]').classList.contains('is-pressed')})`);
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:260,y:330,button:'left',buttons:0,clickCount:1},cursor.sessionId);
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:500,y:360},cursor.sessionId);await delay(150);
  report.plainClick={pressed,recovered:await evaluate(cursor,`({visible:document.documentElement.dataset.cursorVisible,pressed:document.querySelector('[data-cursor-ring]').classList.contains('is-pressed')})`)};
  report.frameSample=await evaluate(cursor,`(async()=>{const d=[];let before;await new Promise(resolve=>{function frame(now){if(before!==undefined)d.push(now-before);before=now;if(d.length===120)resolve();else requestAnimationFrame(frame);}requestAnimationFrame(frame);});const s=[...d].sort((a,b)=>a-b);return{frames:120,medianMs:s[60],p95Ms:s[114],over34ms:d.filter(n=>n>34).length};})()`);
  await evaluate(cursor,`scrollTo({top:document.body.scrollHeight,behavior:'instant'});true`);await delay(150);
  report.offscreen=await evaluate(cursor,`({visible:document.querySelector('[data-ink-loop]').classList.contains('is-visible'),state:getComputedStyle(document.querySelector('.ink-trace')).animationPlayState})`);
  await close(cursor);
  assertInteractionReport(report);
  await writeFile(output+'/../keyboard-walkthrough.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}catch(error){report.failure=String(error);await writeFile(output+'/../keyboard-walkthrough.json',JSON.stringify(report,null,2)+'\n');throw error;}finally{socket.close();chrome.kill('SIGTERM');await new Promise(r=>setTimeout(r,150));await rm(profile,{recursive:true,force:true});}

