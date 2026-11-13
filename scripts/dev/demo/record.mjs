// Records a scripted tour of a page in headless Chrome as a video, for the website.
//
//   node scripts/dev/demo/record.mjs <scene.mjs> <output prefix> [url]
//
// The scene module exports {width, height, scheme, async run(page)}; `page` offers goto, wait,
// moveTo, scrollTo, click and type, with a drawn pointer, because a headless browser shows none.
// Frames come from Chrome's screencast with their timestamps, so pauses keep their real length;
// ffmpeg turns them into <prefix>.mp4 (H.264), <prefix>.webm (VP9) and <prefix>-poster.webp.
// Nothing is uploaded anywhere: the page is whatever runs on this computer.
import {spawn, spawnSync} from 'node:child_process';
import {mkdtemp, mkdir, readFile, rm, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const [sceneFile, prefix, url] = process.argv.slice(2);
if (!sceneFile || !prefix) {
  console.error('usage: record.mjs <scene.mjs> <output prefix> [url]');
  process.exit(2);
}
const scene = await import(pathToFileURL(resolve(sceneFile)).href);
const width = scene.width || 1280, height = scene.height || 800;
const profile = await mkdtemp(join(tmpdir(), 'autorelabel-record-'));
const frames = join(profile, 'frames');
await mkdir(frames);

const browserPath = process.env.CHROME_PATH ||
  ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'].find(name => spawnSync('which', [name]).status === 0);
if (!browserPath) throw new Error('no Chrome or Chromium found: set CHROME_PATH');
const chrome = spawn(browserPath, [
  '--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--hide-scrollbars',
  '--mute-audio', `--user-data-dir=${profile}`, '--remote-debugging-port=0', `--window-size=${width},${height}`,
  'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
const endpoint = await new Promise((done, fail) => {
  let seen = '';
  chrome.stderr.on('data', chunk => {
    seen += chunk;
    const m = seen.match(/DevTools listening on (ws:\/\/\S+)/);
    if (m) done(m[1]);
  });
  chrome.on('exit', code => fail(new Error(`chrome exited (${code})`)));
});
chrome.on('error', () => {});                               // a snap-confined browser may refuse a kill
// Close the whole browser through DevTools: works for a snap-confined Chromium too, where a kill is refused.
async function closeBrowser() {
  try {
    const browser = new WebSocket(endpoint);
    await new Promise(done => browser.addEventListener('open', done, {once: true}));
    browser.send(JSON.stringify({id: 1, method: 'Browser.close'}));
    await sleep(400);
    browser.close();
  } catch { /* already gone */ }
  try { chrome.kill(); } catch { /* the snap keeps its own processes */ }
}
const targets = await (await fetch(endpoint.replace('ws://', 'http://').replace(/\/devtools\/browser\/.*/, '/json/list'))).json();
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(done => ws.addEventListener('open', done, {once: true}));
let id = 0;
const pending = new Map(), listeners = [];
ws.addEventListener('message', ({data}) => {
  const msg = JSON.parse(data);
  if (msg.id && pending.has(msg.id)) {
    const {done, fail} = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? fail(new Error(msg.error.message)) : done(msg.result);
  } else if (msg.method) listeners.forEach(fn => fn(msg));
});
const send = (method, params = {}) => new Promise((done, fail) => {
  pending.set(++id, {done, fail});
  ws.send(JSON.stringify({id, method, params}));
});
const sleep = ms => new Promise(done => setTimeout(done, ms));

await send('Page.enable');
await send('Runtime.enable');
await send('Page.setBypassCSP', {enabled: true});         // only to draw the pointer; the page itself is unchanged
await send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: false});
await send('Emulation.setEmulatedMedia', {features: [{name: 'prefers-color-scheme', value: scene.scheme || 'dark'},
                                                     {name: 'prefers-reduced-motion', value: 'no-preference'}]});

const shots = [];
let recording = false;
listeners.push(async msg => {
  if (msg.method !== 'Page.screencastFrame') return;
  const {data, metadata, sessionId} = msg.params;
  send('Page.screencastFrameAck', {sessionId}).catch(() => {});
  if (!recording) return;
  const file = join(frames, `${String(shots.length).padStart(6, '0')}.jpg`);
  shots.push({file, t: metadata.timestamp});
  await writeFile(file, Buffer.from(data, 'base64'));
});

const pointer = {x: width * 0.6, y: height * 0.55};
function drawPointerIn(x, y) {               // runs in the page
  if (document.getElementById('__rec_pointer')) return;
  const p = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  p.id = '__rec_pointer'; p.setAttribute('viewBox', '0 0 24 24'); p.setAttribute('width', '26'); p.setAttribute('height', '26');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  for (const [k, v] of Object.entries({d: 'M3 2 L3 19 L8 14.5 L11.5 22 L14.5 20.6 L11 13.4 L17.5 13.4 Z', fill: '#fff', stroke: '#111',
                                       'stroke-width': '1.4', 'stroke-linejoin': 'round'})) path.setAttribute(k, v);
  p.append(path);
  Object.assign(p.style, {position: 'fixed', left: '0', top: '0', zIndex: 2147483647, pointerEvents: 'none',
                          filter: 'drop-shadow(0 2px 3px rgba(0,0,0,.45))', transform: `translate(${x}px, ${y}px)`});
  document.documentElement.appendChild(p);
}
function placePointerIn(x, y) {              // runs in the page
  const p = document.getElementById('__rec_pointer');
  if (p) p.style.transform = `translate(${x}px, ${y}px)`;
}
const drawPointer = () => call(drawPointerIn, pointer.x, pointer.y);
listeners.push(msg => { if (msg.method === 'Page.loadEventFired') drawPointer().catch(() => {}); });
const placePointer = (x, y) => call(placePointerIn, x, y);
// Runs a fixed function in the page with the scene's values as arguments: no code is built from them.
const call = async (fn, ...args) => {
  const {result: global} = await send('Runtime.evaluate', {expression: 'globalThis'});
  const {result} = await send('Runtime.callFunctionOn', {objectId: global.objectId, functionDeclaration: fn.toString(),
                                                         arguments: args.map(value => ({value})), returnByValue: true});
  return result.value;
};
const centre = async selector => {
  const at = await call(function (s) {
    const e = document.querySelector(s);
    if (!e) return null;
    const r = e.getBoundingClientRect();
    return {x: r.x + r.width / 2, y: r.y + r.height / 2};
  }, selector);
  if (!at) throw new Error(`not found: ${selector}`);
  return at;
};
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

const page = {
  async goto(target) {
    const loaded = new Promise(done => listeners.push(function once(msg) {
      if (msg.method === 'Page.loadEventFired') { listeners.splice(listeners.indexOf(once), 1); done(); }
    }));
    await send('Page.navigate', {url: target});
    if (target !== 'about:blank') recording = true;        // the take starts with the first real page
    await loaded;
    await drawPointer();
  },
  wait: sleep,
  async moveTo(selector, ms = 700, dx = 0, dy = 0) {
    let to = await centre(selector);
    if (to.y < 70 || to.y > height - 50) {                // off screen: bring it into view first
      await this.scrollTo(selector, 800, Math.round(height / 3));
      to = await centre(selector);
    }
    const from = {...pointer}, steps = Math.max(2, Math.round(ms / 16));
    for (let i = 1; i <= steps; i++) {
      const k = ease(i / steps);
      pointer.x = from.x + (to.x + dx - from.x) * k;
      pointer.y = from.y + (to.y + dy - from.y) * k;
      await send('Input.dispatchMouseEvent', {type: 'mouseMoved', x: pointer.x, y: pointer.y});
      await placePointer(pointer.x, pointer.y);
      await sleep(16);
    }
  },
  async scrollTo(selector, ms = 900, offset = 80) {
    const target = await call(function (s, o) { return document.querySelector(s).getBoundingClientRect().top + scrollY - o; },
                              selector, offset);
    const start = await call(function () { return scrollY; });
    const steps = Math.max(2, Math.round(ms / 16));
    for (let i = 1; i <= steps; i++) {
      await call(function (y) { scrollTo(0, y); }, start + (target - start) * ease(i / steps));
      await sleep(16);
    }
    await send('Input.dispatchMouseEvent', {type: 'mouseMoved', x: pointer.x, y: pointer.y});
  },
  async click(selector, ms = 600) {
    if (selector) await this.moveTo(selector, ms);
    for (const type of ['mousePressed', 'mouseReleased'])
      await send('Input.dispatchMouseEvent', {type, x: pointer.x, y: pointer.y, button: 'left', clickCount: 1});
  },
  async type(text, ms = 55) {
    for (const ch of text) { await send('Input.insertText', {text: ch}); await sleep(ms); }
  },
  async key(key, code = key, keyCode = 0) {
    for (const type of ['keyDown', 'keyUp'])
      await send('Input.dispatchKeyEvent', {type, key, code, windowsVirtualKeyCode: keyCode});
  },
  send,
};

await page.goto('about:blank');
await send('Page.startScreencast', {format: 'jpeg', quality: 92, maxWidth: width, maxHeight: height, everyNthFrame: 1});
try {
  await scene.run(page, url);
} finally {
  await sleep(300);
  recording = false;
  await send('Page.stopScreencast').catch(() => {});
  ws.close();
  await closeBrowser();
}
if (shots.length < 2) throw new Error('no frames were recorded');
// a concat list with each frame's real duration, so the video keeps the tour's own timing
const list = shots.map((s, i) => `file '${s.file}'\nduration ${((shots[i + 1]?.t ?? s.t + 0.6) - s.t).toFixed(4)}`);
await writeFile(join(profile, 'list.txt'), list.join('\n') + `\nfile '${shots.at(-1).file}'\n`);
const ff = (...args) => {
  const r = spawnSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...args], {stdio: 'inherit'});
  if (r.status) throw new Error(`ffmpeg failed: ${args.at(-1)}`);
};
const input = ['-f', 'concat', '-safe', '0', '-i', join(profile, 'list.txt')];
const vf = `fps=30,scale=${scene.outWidth || width}:-2:flags=lanczos,format=yuv420p`;
ff(...input, '-vf', vf, '-c:v', 'libx264', '-preset', 'slow', '-crf', '24', '-movflags', '+faststart', '-an', `${prefix}.mp4`);
ff(...input, '-vf', vf, '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '36', '-row-mt', '1', '-an', `${prefix}.webm`);
ff('-sseof', '-0.5', '-i', `${prefix}.mp4`, '-frames:v', '1', '-c:v', 'libwebp', '-quality', '82', `${prefix}-poster.webp`);
await rm(profile, {recursive: true, force: true});
console.log(`${shots.length} frames, ${(shots.at(-1).t - shots[0].t).toFixed(1)} s: ${prefix}.mp4, ${prefix}.webm, ${prefix}-poster.webp`);
