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

await mkdir(output,{recursive:true});
const report={captures:[],accessibility:[],interactions:{}};
const routes=['','start/','rhcsa/','rhce/','tasks/','how-it-works/','faq/','docs/','docs/installing/','docs/first-exam/','docs/exam-screen/','docs/the-lab/','docs/grading-and-results/','docs/practice/','docs/commands/','docs/settings/','docs/troubleshooting/','docs/files-and-uninstall/','docs/objectives/','404.html'];
const mobileRoutes=['','start/','rhcsa/','rhce/','tasks/','how-it-works/','faq/','docs/','docs/installing/','docs/commands/'];
const labelFor=route=>(route||'home').replace(/\/$/,'').replaceAll('/','-').replace('.html','');
try{
  for(const width of [1440,390])for(const route of width===1440?routes:mobileRoutes){
    const page=await open(route,width),label=`${labelFor(route)}-${width}`;
    const before=await metrics(page),a11y=await accessibility(page);
    report.accessibility.push({page:label,...a11y});
    const capture=await screenshot(page,label);report.captures.push({...capture,...before,trace:traces.get(page.sessionId)});
    console.log(JSON.stringify({page:label,overflow:before.scrollWidth>before.clientWidth,violations:a11y.violations.map(v=>v.id),errors:traces.get(page.sessionId).errors}));
    await close(page);
  }
  const faq=await open('faq/',1440);
  await evaluate(faq,`document.querySelector('.accordion details:not([open]) summary').scrollIntoView({behavior:'instant',block:'center'});true`);
  const faqInitial=await evaluate(faq,`(()=>{const d=document.querySelector('.accordion details:not([open])');window.faqTarget=d;return{height:d.getBoundingClientRect().height,icon:getComputedStyle(d.querySelector('.icon')).transform};})()`);
  await evaluate(faq,`window.faqTarget.querySelector('summary').click();true`);await delay(100);
  const faqMid=await evaluate(faq,`({height:faqTarget.getBoundingClientRect().height,icon:getComputedStyle(faqTarget.querySelector('.icon')).transform,expanded:faqTarget.dataset.expanded})`);
  await delay(350);const faqOpen=await evaluate(faq,`({height:faqTarget.getBoundingClientRect().height,icon:getComputedStyle(faqTarget.querySelector('.icon')).transform,open:faqTarget.open,animations:faqTarget.getAnimations().length})`);
  report.captures.push(await screenshot(faq,'faq-open',{full:false}));
  await evaluate(faq,`faqTarget.querySelector('summary').click();true`);await delay(90);
  const faqClosing=await evaluate(faq,`({height:faqTarget.getBoundingClientRect().height,icon:getComputedStyle(faqTarget.querySelector('.icon')).transform,open:faqTarget.open})`);
  await evaluate(faq,`faqTarget.querySelector('summary').click();true`);await delay(400);
  const faqReversed=await evaluate(faq,`({height:faqTarget.getBoundingClientRect().height,open:faqTarget.open,expanded:faqTarget.dataset.expanded,overflow:faqTarget.style.overflow})`);
  await evaluate(faq,`faqTarget.querySelector('summary').focus();true`);await key(faq,'Enter');await delay(350);
  const faqKeyboard=await evaluate(faq,`({open:faqTarget.open,expanded:faqTarget.dataset.expanded})`);
  await evaluate(faq,`const i=document.querySelector('[data-faq-search]');i.value='no-such-question-9385';i.dispatchEvent(new Event('input',{bubbles:true}));true`);
  report.interactions.faq={initial:faqInitial,middle:faqMid,open:faqOpen,closing:faqClosing,reversed:faqReversed,keyboard:faqKeyboard,empty:await evaluate(faq,`!document.querySelector('[data-faq-empty]').hidden`)};
  await evaluate(faq,`document.querySelector('[data-faq-clear]').click();true`);
  report.interactions.faq.clearRestores=await evaluate(faq,`[...document.querySelectorAll('[data-faq-item]')].every(i=>!i.hidden)`);
  await close(faq);

  const home=await open('',1440);
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:260,y:330},home.sessionId);await delay(200);
  const resting=await evaluate(home,`({visible:document.documentElement.dataset.cursorVisible,dot:document.querySelector('[data-cursor-dot]').style.transform})`);
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:260,y:330,button:'left',buttons:1,clickCount:1},home.sessionId);
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:470,y:330,button:'left',buttons:1},home.sessionId);
  const dragging=await evaluate(home,`document.documentElement.dataset.cursorVisible`);
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:470,y:330,button:'left',buttons:0,clickCount:1},home.sessionId);
  await evaluate(home,`(()=>{const r=document.createRange();r.selectNodeContents(document.querySelector('.hero-copy>p'));const s=getSelection();s.removeAllRanges();s.addRange(r);return true;})()`);await delay(40);
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:480,y:350},home.sessionId);
  const selecting=await evaluate(home,`document.documentElement.dataset.cursorVisible`);
  await evaluate(home,`getSelection().removeAllRanges();true`);await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:500,y:360},home.sessionId);await delay(180);
  const recovered=await evaluate(home,`({visible:document.documentElement.dataset.cursorVisible,dot:document.querySelector('[data-cursor-dot]').style.transform,pressed:document.querySelector('[data-cursor-ring]').classList.contains('is-pressed')})`);
  report.interactions.cursor={resting,dragging,selecting,recovered};
  await evaluate(home,`document.querySelector('[data-reboot-state=before]').click();true`);
  const before=await evaluate(home,`document.querySelector('[data-task-score]').textContent`);
  await evaluate(home,`document.querySelector('[data-reboot-state=after]').click();true`);
  const after=await evaluate(home,`document.querySelector('[data-task-score]').textContent`);
  await evaluate(home,`document.querySelector('[data-motion-toggle]').click();true`);
  const paused=await evaluate(home,`getComputedStyle(document.querySelector('.ink-trace')).animationPlayState`);
  await evaluate(home,`document.querySelector('[data-motion-toggle]').click();true`);
  report.interactions.rebootAndMotion={before,after,paused,resumed:await evaluate(home,`getComputedStyle(document.querySelector('.ink-trace')).animationPlayState`)};
  await evaluate(home,`document.querySelector('[data-copy-target=home-clone]').click();true`);await delay(100);
  report.interactions.copy=await evaluate(home,`(async()=>({clipboard:await navigator.clipboard.readText(),expected:document.getElementById('home-clone').textContent}))()`);
  await evaluate(home,`document.querySelector('[data-theme-toggle]').click();true`);
  report.interactions.theme=await evaluate(home,`({choice:document.documentElement.dataset.theme,saved:localStorage.getItem('autorelabel-theme')})`);
  report.captures.push(await screenshot(home,'home-night'));
  await evaluate(home,`document.querySelector('[data-theme-toggle]').click();document.querySelector('[data-open-search]').click();const i=document.querySelector('[data-docs-search]');i.value='firewall';i.dispatchEvent(new Event('input',{bubbles:true}));true`);await delay(1700);
  report.interactions.search=await evaluate(home,`({status:document.querySelector('[data-search-status]').textContent,results:[...document.querySelectorAll('.search-result')].map(a=>({title:a.querySelector('strong').textContent,href:a.href})),open:document.querySelector('[data-search-dialog]').open})`);
  report.captures.push(await screenshot(home,'docs-search',{full:false}));
  report.accessibility.push({page:'docs-search',...await accessibility(home)});
  await key(home,'Escape');
  await evaluate(home,`document.querySelector('a[href="/autorelabel-rhcsa-rhce/faq/"]').click();true`);await delay(650);
  report.interactions.transition=await evaluate(home,`({path:location.pathname,heading:document.querySelector('h1').textContent,active:[...document.querySelectorAll('.primary-nav a[aria-current]')].map(a=>a.textContent)})`);
  await evaluate(home,`document.querySelector('.accordion summary').click();true`);await delay(400);
  report.interactions.transition.faqWorks=await evaluate(home,`document.querySelector('.accordion details').open`);
  await close(home);

  const bank=await open('tasks/',390);
  await evaluate(bank,`document.querySelector('[data-main-search]').focus();true`);
  report.interactions.inputFocus=await evaluate(bank,`(()=>{const i=document.querySelector('[data-main-search]'),p=i.closest('.search-field');return{inputOutlineStyle:getComputedStyle(i).outlineStyle,parentOutlineStyle:getComputedStyle(p).outlineStyle,inputOutline:getComputedStyle(i).outlineWidth,parentOutline:getComputedStyle(p).outlineWidth,parentShadow:getComputedStyle(p).boxShadow,inputShadow:getComputedStyle(i).boxShadow};})()`);
  await evaluate(bank,`document.querySelector('[data-exam-filter=rhcsa]').click();const e=document.querySelector('[name=eligibility-eligible]');e.checked=false;e.dispatchEvent(new Event('change',{bubbles:true}));true`);await delay(200);
  report.interactions.bankPractice=await evaluate(bank,`({count:document.querySelector('[data-bank-count]').textContent,visible:[...document.querySelectorAll('[data-task]')].filter(r=>!r.hidden).map(r=>r.dataset.task),query:location.search})`);
  report.captures.push(await screenshot(bank,'tasks-practice-390'));
  const shared=await evaluate(bank,'location.href');await send('Page.navigate',{url:shared},bank.sessionId);await delay(750);
  report.interactions.bankShared=await evaluate(bank,`({count:document.querySelector('[data-bank-count]').textContent,checked:document.querySelector('[name=eligibility-eligible]').checked})`);
  await evaluate(bank,`document.querySelector('[data-clear-filters]').click();const input=document.querySelector('[data-main-search]');input.value='no-such-task-9385';input.dispatchEvent(new Event('input',{bubbles:true}));true`);await delay(200);
  report.interactions.bankEmpty=await evaluate(bank,`({count:document.querySelector('[data-bank-count]').textContent,empty:!document.querySelector('[data-bank-empty]').hidden})`);
  await evaluate(bank,`document.querySelector('[data-clear-filters]').click();const sort=document.querySelector('[name=sort]');sort.value='minutes';sort.dispatchEvent(new Event('change',{bubbles:true}));true`);await delay(300);
  report.interactions.bankSort=await evaluate(bank,`({first:[...document.querySelectorAll('[data-task]:not([hidden]) td:nth-child(5)')].slice(0,8).map(c=>parseInt(c.textContent)),count:document.querySelector('[data-bank-count]').textContent})`);
  await close(bank);

  const start=await open('start/',1440);
  await evaluate(start,`document.getElementById('tab-ubuntu').focus();true`);await key(start,'ArrowRight');
  report.interactions.distro=await evaluate(start,`({active:document.querySelector('[role=tab][aria-selected=true]').textContent,focus:document.activeElement.id,saved:localStorage.getItem('autorelabel-distro'),visible:[...document.querySelectorAll('[role=tabpanel]')].filter(p=>!p.hidden).map(p=>p.id)})`);
  await evaluate(start,`document.querySelector('[data-copy-target=install-fedora-all]').click();true`);await delay(100);
  report.interactions.distro.copy=await evaluate(start,`(async()=>({matches:await navigator.clipboard.readText()===document.getElementById('install-fedora-all').dataset.command}))()`);
  await close(start);

  const mobile=await open('',390);
  await evaluate(mobile,`document.querySelector('[data-open-menu]').click();true`);await delay(300);
  const focus=[];for(let i=0;i<20;i++){await key(mobile,'Tab');focus.push(await evaluate(mobile,`Boolean(document.activeElement.closest('[data-site-menu]'))`));}
  report.captures.push(await screenshot(mobile,'mobile-navigation',{full:false}));report.accessibility.push({page:'mobile-navigation',...await accessibility(mobile)});
  await key(mobile,'Escape');
  report.interactions.menu={contained:focus.every(Boolean),closed:await evaluate(mobile,`!document.querySelector('[data-site-menu]').open`),focusReturned:await evaluate(mobile,`document.activeElement.matches('[data-open-menu]')`)};
  await close(mobile);

  const reduced=await open('faq/',390,{reduced:true});
  await evaluate(reduced,`document.querySelector('.accordion summary').click();true`);
  report.interactions.reducedFaq=await evaluate(reduced,`({open:document.querySelector('.accordion details').open,animations:document.querySelector('.accordion details').getAnimations().length,iconTransition:getComputedStyle(document.querySelector('.accordion .icon')).transitionDuration})`);
  await close(reduced);
  const reducedHome=await open('',390,{reduced:true});
  report.interactions.reducedHome=await evaluate(reducedHome,`({animation:getComputedStyle(document.querySelector('.ink-trace')).animationName,cursor:getComputedStyle(document.querySelector('[data-cursor-ring]')).display,scroll:getComputedStyle(document.documentElement).scrollBehavior})`);
  report.captures.push(await screenshot(reducedHome,'home-reduced-motion'));await close(reducedHome);
  const tablet=await open('',1024);report.captures.push({...await screenshot(tablet,'home-1024'),...await metrics(tablet)});await close(tablet);
  await writeFile(output+'/../browser-report.json',JSON.stringify(report,null,2)+'\n');
  const overflow=report.captures.filter(c=>c.scrollWidth>c.clientWidth);
  const violations=report.accessibility.reduce((n,r)=>n+r.violations.length,0);
  if(overflow.length||violations)throw new Error(`Browser checks failed: ${overflow.length} page overflows, ${violations} accessibility violations. See qa/browser-report.json.`);
  if(report.interactions.faq.keyboard.open || report.interactions.cursor.recovered.visible!=='true' || report.interactions.cursor.selecting!=='false' || !report.interactions.menu.contained || !report.interactions.menu.focusReturned)throw new Error('An interaction check failed. See qa/browser-report.json.');

  console.log(JSON.stringify({checks:report.accessibility.length,violations:report.accessibility.reduce((n,r)=>n+r.violations.length,0),interactions:report.interactions},null,2));
}finally{socket.close();chrome.kill('SIGTERM');await new Promise(r=>setTimeout(r,150));await rm(profile,{recursive:true,force:true});}

