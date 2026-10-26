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
const report={};
try{
  for(const width of [1440,390])for(const route of ['', 'tasks/','docs/installing/','faq/']){
    const page=await open(route,width);const label=route?route.replaceAll('/','-').replace(/-$/,''):'home';
    await screenshot(page,'top-'+label+'-'+width,{full:false});
    if(!route&&width===390)await screenshot(page,'home-result-390',{selector:'.score-sheet'});
    if(route==='docs/installing/'&&width===1440)await screenshot(page,'docs-question',{selector:'.question-callout'});
    if(route==='tasks/'&&width===390){
      await evaluate(page,`document.querySelector('[data-main-search]').focus();true`);
      report.focus=await evaluate(page,`(()=>{const i=document.querySelector('[data-main-search]'),p=i.closest('.search-field');return{input:{outline:getComputedStyle(i).outline,shadow:getComputedStyle(i).boxShadow},parent:{outline:getComputedStyle(p).outline,shadow:getComputedStyle(p).boxShadow},focusWidth:getComputedStyle(i).getPropertyValue('--focus-width'),classes:i.className,sheets:[...document.styleSheets].map(s=>s.href)};})()`);
      await screenshot(page,'input-focus-390',{full:false});
    }
    if(route==='faq/'&&width===1440){await evaluate(page,`document.querySelector('.accordion summary').focus();true`);await key(page,'Enter');await delay(350);report.keyboardFaq=await evaluate(page,`({open:document.querySelector('.accordion details').open,active:document.activeElement.tagName})`);}
    if(!route&&width===1440){
      report.media=await evaluate(page,`({fine:matchMedia('(pointer:fine)').matches,hover:matchMedia('(hover:hover)').matches,reduced:matchMedia('(prefers-reduced-motion:reduce)').matches,paused:document.documentElement.dataset.motionPaused})`);
      await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:260,y:330},page.sessionId);await delay(120);
      report.cursorRest=await evaluate(page,`({visible:document.documentElement.dataset.cursorVisible,dot:document.querySelector('[data-cursor-dot]').style.transform,display:getComputedStyle(document.querySelector('[data-cursor-ring]')).display})`);
      await evaluate(page,`(()=>{const r=document.createRange();r.selectNodeContents(document.querySelector('.hero-copy>p'));getSelection().removeAllRanges();getSelection().addRange(r);return true;})()`);await delay(30);
      await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:470,y:350},page.sessionId);report.cursorSelection=await evaluate(page,`document.documentElement.dataset.cursorVisible`);
      await evaluate(page,`getSelection().removeAllRanges();true`);await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:500,y:360},page.sessionId);await delay(150);
      report.cursorRecovered=await evaluate(page,`({visible:document.documentElement.dataset.cursorVisible,dot:document.querySelector('[data-cursor-dot]').style.transform,pressed:document.querySelector('[data-cursor-ring]').classList.contains('is-pressed')})`);
    }
    await close(page);
  }
  const exam=await open('rhce/',1440);report.wide=await evaluate(exam,`[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+2).slice(0,14).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,text:e.textContent.slice(0,100)}))`);await close(exam);
  report.labCaptures=[];
  for(const width of [1440,390])for(const route of ['rhcsa/','rhce/']){
    const lab=await open(route,width);
    await evaluate(lab,`(()=>{const drawing=document.querySelector('.lab-drawing');document.querySelector('[data-vm]').focus({preventScroll:true});drawing.scrollLeft=0;scrollTo({top:0,behavior:'instant'});return true;})()`);
    await delay(650);
    report.labCaptures.push(await screenshot(lab,route.slice(0,-1)+'-lab-layout-'+width,{selector:'.lab-layout'}));
    if(width===390){
      await evaluate(lab,`(()=>{const node=[...document.querySelectorAll('[data-vm]')][2];node.focus({preventScroll:true});node.scrollIntoView({behavior:'instant',block:'nearest',inline:'nearest'});node.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));scrollTo({top:0,behavior:'instant'});return true;})()`);
      await delay(650);
      report.labCaptures.push(await screenshot(lab,route.slice(0,-1)+'-lab-focus-390',{selector:'.lab-layout'}));
    }
    await close(lab);
  }
  report.additions=[];
  for(const width of [1440,390]){
    const page=await open('',width);
    await evaluate(page,`scrollTo({top:0,behavior:'instant'});true`);
    const footer=await evaluate(page,`({text:document.querySelector('.footer-release').textContent,links:[...document.querySelectorAll('footer a')].map(a=>({text:a.textContent,href:a.href})),description:document.getElementById('demo-description').textContent,describedBy:document.querySelector('video').getAttribute('aria-describedby'),videoSourcesRemainLazy:[...document.querySelectorAll('video source')].every(s=>s.hasAttribute('data-src')&&!s.hasAttribute('src'))})`);
    report.additions.push({width,...footer,footerCapture:await screenshot(page,'footer-'+width,{selector:'.site-footer'}),demoCapture:await screenshot(page,'demo-description-'+width,{selector:'.demo-section'})});
    await close(page);
  }
  console.log(JSON.stringify(report,null,2));
  await writeFile(output+'/../probe-report.json',JSON.stringify(report,null,2)+'\n');
}finally{socket.close();chrome.kill('SIGTERM');await new Promise(r=>setTimeout(r,150));await rm(profile,{recursive:true,force:true});}

