import {readFile,readdir,stat,writeFile,mkdir} from 'node:fs/promises';
import {resolve,join,extname} from 'node:path';
import {gzipSync} from 'node:zlib';
import assert from 'node:assert/strict';
import {unified} from 'unified';
import remarkParse from 'remark-parse';
import yaml from 'js-yaml';
import {parse as parseToml} from 'smol-toml';

const directory=resolve('dist'),base='/autorelabel-rhcsa-rhce';
const walk=async path=>(await Promise.all((await readdir(path,{withFileTypes:true})).map(entry=>entry.isDirectory()?walk(join(path,entry.name)):join(path,entry.name)))).flat();
const files=await walk(directory),pages=files.filter(file=>extname(file)==='.html');
const decode=value=>value.replace(/&(?:amp|quot|apos|lt|gt|#39|#x27|#\d+|#x[\da-f]+);/gi,entity=>({'&amp;':'&','&quot;':'"','&apos;':"'",'&#39;':"'",'&#x27;':"'",'&lt;':'<','&gt;':'>'}[entity.toLowerCase()]||String.fromCodePoint(entity.toLowerCase().startsWith('&#x')?parseInt(entity.slice(3,-1),16):parseInt(entity.slice(2,-1),10))));
const text=html=>decode(html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,'').replace(/<\/?(?:p|div|li|br|h[1-6]|section|td|th|tr|dt|dd)\b[^>]*>/g,' ').replace(/<[^>]*>/g,'')).replace(/\s+/g,' ').trim();
const documents=new Map();
for(const page of pages){const html=await readFile(page,'utf8');const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>decode(match[1]));assert.equal(ids.length,new Set(ids).size,`Duplicate IDs: ${page}`);assert.equal((html.match(/<h1\b/g)||[]).length,1,`One H1: ${page}`);assert(!/[—–]|\b(?:instead|rather)\b/i.test(text(html)),`Copy style: ${page}`);documents.set(page,{html,ids:new Set(ids)});}
let links=0;
for(const [page,{html}] of documents){
  const route=page.slice(directory.length).replace(/index\.html$/,'');
  for(const match of html.matchAll(/\b(href|src|poster|data-src)="([^"]+)"/g)){
    const value=decode(match[2]);if(/^(mailto:|tel:|data:)/.test(value))continue;
    const url=new URL(value,`https://syed-913.github.io${base}${route}`);
    if(url.origin!=='https://syed-913.github.io'){assert.equal(match[1],'href',`External runtime resource: ${value}`);continue;}
    assert(url.pathname.startsWith(base+'/'),`Missing base: ${value} in ${page}`);
    let target=join(directory,decodeURIComponent(url.pathname.slice(base.length)));
    const info=await stat(target).catch(()=>null);assert(info,`Missing local file: ${value} in ${page}`);
    if(info.isDirectory())target=join(target,'index.html');
    assert(await stat(target).catch(()=>null),`Missing index: ${value}`);
    if(url.hash&&extname(target)==='.html')assert(documents.get(target)?.ids.has(decodeURIComponent(url.hash.slice(1))),`Missing anchor: ${value} in ${page}`);
    links++;
  }
}
const bank=documents.get(join(directory,'tasks/index.html')).html;
const payload=JSON.parse(bank.match(/<script[^>]+id="task-data"[^>]*>([\s\S]*?)<\/script>/)[1]);
const expected=[];
for(const exam of ['rhcsa','rhce'])for(const file of (await walk(resolve(`../banks/${exam}/tasks`))).filter(file=>file.endsWith('/task.yaml'))){const task=yaml.load(await readFile(file,'utf8'));expected.push({exam,title:task.title,practice_only:Boolean(task.practice_only),objectives:task.objectives});}
assert.equal(payload.length,expected.length);
for(const exam of ['rhcsa','rhce'])assert.equal(payload.filter(t=>t.exam===exam).length,expected.filter(t=>t.exam===exam).length);
assert.equal(payload.filter(t=>t.practice_only).length,expected.filter(t=>t.practice_only).length);
assert(expected.every(task=>payload.some(item=>item.exam===task.exam&&item.title===task.title&&item.practice_only===task.practice_only)),'Task metadata matches the bank');
assert(!/Inspect task metadata|(?:href|src)="[^"]*banks\/[^"#]*tasks\/|solution\.md/.test(bank),'Task bank exposes titles and metadata only');
assert(payload.every(task=>!('prompt'in task)&&!('solution'in task)),'No task prompts or solutions in payload');
const readme=await readFile('../README.md','utf8');
const disclaimer=readme.split('\n').find(line=>/^>.*not affiliated/i.test(line)).replace(/^>\s*/,'').replace(/\[([^\]]+)\]\([^)]+\)/g,'$1').replace(/\*\*/g,'');
for(const [page,{html}]of documents){const footer=html.match(/class="affiliation"[^>]*>([\s\S]*?)<\/div>/);assert(footer,`Footer: ${page}`);assert.equal(text(footer[1]),disclaimer.replace(/\s+/g,' ').trim(),`Verbatim disclaimer: ${page}`);}
const version=parseToml(await readFile('../pyproject.toml','utf8')).project.version;
assert.equal(typeof version,'string','Project version is a string');
const repository='https://github.com/syed-913/autorelabel-rhcsa-rhce';
const footerDestinations=['/issues/new/choose','/discussions','/blob/main/SECURITY.md','/blob/main/docs/TASK-AUTHORING.md',`/releases/tag/v${encodeURIComponent(version)}`];
for(const [page,{html}]of documents){
  const footer=html.match(/<footer\b[^>]*>([\s\S]*?)<\/footer>/)[1];
  for(const path of footerDestinations)assert(footer.includes(`href="${repository}${path}"`),`Footer destination ${path}: ${page}`);
  assert(text(footer).includes(`v${version} · release notes ↗`),`Source version: ${page}`);
}
const home=documents.get(join(directory,'index.html')).html;
assert(/<video\b[^>]*aria-describedby="demo-description"/.test(home),'Video references its text alternative');
const description=home.match(/<p\b[^>]*id="demo-description"[^>]*>([\s\S]*?)<\/p>/)?.[1];
assert(description&&text(description).includes('silent demo')&&text(description).includes('touch /.autorelabel'),'Visible text alternative describes the silent demo');
const markdown=unified().use(remarkParse).parse(readme),headings=markdown.children;
const start=headings.findIndex(node=>node.type==='heading'&&node.depth===2&&node.children.map(n=>n.value||'').join('')==='Getting started');
const sourceCommand=headings.slice(start+1).find(node=>node.type==='code').value;
const started=documents.get(join(directory,'start/index.html')).html;
const copied=decode(started.match(/id="quick-start-all"[^>]+data-command="([^"]+)"/)[1]);
assert.equal(copied,sourceCommand,'Getting started commands match README');
const js=files.filter(file=>file.includes('/_astro/')&&file.endsWith('.js'));let gzip=0;
for(const file of js)gzip+=gzipSync(await readFile(file)).length;
assert(gzip<=50*1024,`Home JavaScript budget: ${gzip} bytes gzip`);
for(const file of await walk(resolve('src'))){if(/\.(?:astro|ts|css)$/.test(file)){const source=await readFile(file,'utf8');assert(!/\b[\w-]+-disable(?:-next-line|-line)?\b/.test(source),`Tool suppression comment in ${file}`);}}
const guideCount=((await readFile('../docs/guide/README.md','utf8')).match(/^\d+\. \*\*\[/gm)||[]).length;
assert.equal(pages.length,guideCount+8);assert(await stat(join(directory,'pagefind/pagefind.js')));assert(await stat(join(directory,'media/demo-poster.avif')));
const objectiveLines={};
for(const exam of ['rhcsa','rhce']){const bank=yaml.load(await readFile(`../banks/${exam}/objectives.yaml`,'utf8'));const lines=bank.domains.flatMap(domain=>domain.objectives);objectiveLines[exam]=lines.length;for(const line of lines)assert(expected.filter(task=>task.exam===exam&&task.objectives.includes(line.id)).length>=2,`Objective coverage: ${line.id}`);}
const report={pages:pages.length,localReferences:links,taskMetadata:payload.length,counts:{rhcsa:payload.filter(t=>t.exam==='rhcsa').length,rhce:payload.filter(t=>t.exam==='rhce').length,practiceOnly:payload.filter(t=>t.practice_only).length},objectiveLines,scriptGzipBytes:gzip,version,footer:'Release and support links verified on every page',video:'Visible text alternative linked to the silent demo',disclaimer:'All pages match README',copy:'Style checks passed',anchors:'All local anchors resolve',taskBoundary:'Titles and metadata only',source:'No tool suppression comments in src',search:'Local Pagefind index present'};
await mkdir('qa',{recursive:true});await writeFile('qa/static-checks.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
