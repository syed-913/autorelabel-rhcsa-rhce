import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import yaml from 'js-yaml';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkRehype from 'remark-rehype';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import rehypeSlug from 'rehype-slug';
import rehypeStringify from 'rehype-stringify';
import { guideSlug, href, sourceLink } from './urls';

const root = resolve(process.cwd(), '..');
export const read = (path: string) => readFileSync(resolve(root, path), 'utf8');
export const readme = read('README.md');
export const cloneCommands = section(readme,'Getting started').match(/```(?:bash|sh)?\n([\s\S]*?)```/)![1].trimEnd().split('\n');
export type Exam = 'rhcsa' | 'rhce';
export type Difficulty = 'easy' | 'medium' | 'hard';
export interface Task { id: string; key: string; exam: Exam; domain: string; domainTitle: string; title: string; difficulty: Difficulty; node: string; estimated_minutes: number; practice_only: boolean; objectives: string[]; }
export interface Objective { id: string; text: string; tasks: Task[]; }
export interface Domain { id: string; title: string; objectives: Objective[]; }
export interface Blueprint { tasks: number; duration_minutes: number; total_points: number; pass_mark: number; points: Record<Difficulty, number>; difficulty_mix: Record<Difficulty, number>; domains: Record<string, [number,number]>; }

export const domains = {} as Record<Exam, Domain[]>;
export const blueprints = {} as Record<Exam, Blueprint>;
export const examSources = {} as Record<Exam,string>;
export const tasks: Task[] = [];
for (const exam of ['rhcsa','rhce'] as Exam[]) {
  const bank = yaml.load(read(`banks/${exam}/objectives.yaml`)) as { domains: Domain[]; source_url:string };
  examSources[exam]=bank.source_url;
  domains[exam] = bank.domains.map(domain => ({...domain, objectives: domain.objectives.map(o => ({id:o.id,text:o.text,tasks:[]}))}));
  blueprints[exam] = yaml.load(read(`banks/${exam}/blueprint.yaml`)) as Blueprint;
  for (const directory of readdirSync(resolve(root, `banks/${exam}/tasks`), {withFileTypes:true}).filter(d=>d.isDirectory())) {
    for (const entry of readdirSync(resolve(root, `banks/${exam}/tasks/${directory.name}`), {withFileTypes:true}).filter(d=>d.isDirectory())) {
      const data = yaml.load(read(`banks/${exam}/tasks/${directory.name}/${entry.name}/task.yaml`)) as Omit<Task,'id'|'key'|'exam'|'domain'|'domainTitle'>;
      const task: Task = { id:entry.name, key:`${exam}-${entry.name}`, exam, domain:directory.name, domainTitle:domains[exam].find(d=>d.id===directory.name)?.title || directory.name, title:data.title, difficulty:data.difficulty, node:data.node, estimated_minutes:data.estimated_minutes, practice_only:Boolean(data.practice_only), objectives:data.objectives || [] };
      tasks.push(task);
    }
  }
  for (const domain of domains[exam]) for (const objective of domain.objectives) objective.tasks=tasks.filter(t=>t.exam===exam && t.objectives.includes(objective.id));
}
tasks.sort((a,b)=>a.title.localeCompare(b.title));
export const counts = {total:tasks.length,rhcsa:tasks.filter(t=>t.exam==='rhcsa').length,rhce:tasks.filter(t=>t.exam==='rhce').length,practice:tasks.filter(t=>t.practice_only).length,eligible:tasks.filter(t=>!t.practice_only).length};
export const objectiveText = Object.fromEntries(Object.values(domains).flat().flatMap(d=>d.objectives).map(o=>[o.id,o.text]));

export const tidy = (text: string) => text.replaceAll('✅','✔').replaceAll('⬜','✘').replaceAll('❌','✘').replace(/\s*[—]\s*/g, ': ').replace(/\s*[–]\s*/g, ' to ').replace(/\binstead of\b/gi,'in place of').replace(/\brather than\b/gi,'in place of').replace(/\binstead\b/gi,'in its place').replace(/\brather\b/gi,'quite');
export function section(markdown: string, title: string, level=2): string {
  const nodes=unified().use(remarkParse).parse(markdown).children as any[];
  const start=nodes.findIndex(node=>node.type==='heading'&&node.depth===level&&node.children.map((child:any)=>child.value||'').join('')===title);
  if(start<0)throw new Error(`Missing source section: ${title}`);
  const next=nodes.slice(start+1).find(node=>node.type==='heading'&&node.depth<=level);
  return markdown.slice(nodes[start].position.end.offset,next?.position.start.offset).trim();
}
export const disclaimer = readme.split('\n').find(line=>/^>.*not affiliated/i.test(line))!.replace(/^>\s*/,'');
export interface Guide { title: string; file: string; slug: string; url: string; }
export const guides: Guide[]=[...read('docs/guide/README.md').matchAll(/^\d+\. \*\*\[([^\]]+)\]\(([^)]+)\)/gm)].map(match=>({title:match[1],file:match[2],slug:guideSlug(match[2]),url:match[2]==='11-faq.md'?href('/faq/'):href(`/docs/${guideSlug(match[2])}/`)}));
export interface Faq { id:string; question:string; answer:string; group:string; }
export const faqs: Faq[]=[];
let faqGroup='';
for(const node of unified().use(remarkParse).parse(read('docs/guide/11-faq.md')).children as any[]) {
  if(node.type==='heading' && node.depth===2) faqGroup=node.children.map((n:any)=>n.value||'').join('');
  if(node.type==='heading' && node.depth===3) {
    const question=node.children.map((n:any)=>n.value||'').join('');
    const tail=read('docs/guide/11-faq.md').slice(node.position.end.offset).replace(/^\s+/, '');
    const answer=tail.split(/\n#{2,3} /)[0].trim();
    faqs.push({id:question.toLowerCase().replace(/[^\w\s-]/g,'').trim().replace(/\s+/g,'-'),question,answer,group:faqGroup});
  }
}

type Node = {type:string;tagName?:string;value?:string;properties?:Record<string,any>;children?:Node[]};
const element=(tagName:string,properties:Record<string,any>={},children:Node[]=[]):Node=>({type:'element',tagName,properties,children});
const text=(value:string):Node=>({type:'text',value});
const nodeText=(node:Node):string=>node.value || node.children?.map(nodeText).join('') || '';
export interface Heading { id:string; text:string; depth:number; }
export async function markdown(source:string, path='README.md', images:Record<string,{src:string;width:number;height:number}>={}):Promise<{html:string;headings:Heading[]}> {
  const headings:Heading[]=[];
  let block=0,tableNumber=0;
  const transform=()=> (tree:Node)=>{
    const visit=(node:Node,inCode=false):void=>{
      const code=inCode || node.tagName==='code' || node.tagName==='pre';
      if(node.properties)delete node.properties.align;
      if(node.type==='text' && !code)node.value=tidy(node.value || '');
      if(node.tagName==='th'&&!nodeText(node).trim())node.tagName='td';
      if(node.tagName==='th')node.properties={...node.properties,scope:'col'};
      if(node.tagName==='h1'){node.tagName='div';node.properties={hidden:true};}
      if(node.tagName==='a'){
        node.properties ||= {};
        node.properties.href=sourceLink(String(node.properties.href || ''),path);
        node.properties.className=['text-link'];
      }
      if(node.tagName==='img'){
        node.properties ||= {};
        const name=String(node.properties.src || '').split('/').pop() || '';
        if(images[name])Object.assign(node.properties,images[name],{loading:'lazy',decoding:'async'});
        else node.properties.src=sourceLink(String(node.properties.src||''),path);
      }
      if(['h2','h3'].includes(node.tagName || ''))headings.push({id:String(node.properties?.id||''),text:tidy(nodeText(node)),depth:node.tagName==='h2'?2:3});
      node.children?.forEach(child=>visit(child,code));
      if(!code&&node.children&&['li','td','p'].includes(node.tagName||''))node.children=node.children.flatMap(child=>{
        if(child.type!=='text'||!/^\s*[✔✘]/.test(child.value||''))return [child];
        const value=child.value!.trimStart(),mark=value[0];
        return [element('span',{className:['check-mark',...(mark==='✘'?['check-mark--bad']:[])],ariaHidden:'true','data-pagefind-ignore':'all'},[text(mark)]),text(value.slice(1))];
      });
      if(node.tagName==='blockquote'){
        const first=node.children?.find(n=>n.tagName==='p');
        const strong=first?.children?.find(n=>n.tagName==='strong');
        if(strong && /\?/.test(nodeText(strong))) {
          const title=nodeText(strong), id='question-'+title.toLowerCase().replace(/[^\w\s-]/g,'').trim().replace(/\s+/g,'-');
          const rest=node.children?.filter(n=>n!==first)||[];
          const trailing=first?.children?.filter(n=>n!==strong && (n.type!=='text'||n.value?.trim()))||[];
          if(trailing.length)rest.unshift(element('p',{},trailing));
          node.tagName='aside';node.properties={className:['question-callout'],id,role:'note',ariaLabelledBy:`${id}-title`};
          node.children=[element('span',{className:['question-mark'],ariaHidden:'true'},[text('?')]),element('div',{},[element('p',{className:['question-title'],id:`${id}-title`},[element('a',{href:`#${id}`,className:['text-link']},[text(title)])]),...rest])];
        }
      }
      if(node.tagName==='pre'){
        const code=node.children?.find(n=>n.tagName==='code');
        if(code){const id=`command-${path.replace(/\W/g,'-')}-${++block}`;code.properties={...code.properties,id};node.tagName='div';node.properties={className:['source-command','room--night']};node.children=[element('pre',{tabIndex:0},[code]),element('button',{type:'button',className:['copy-button'],'data-copy-target':id,'data-pagefind-ignore':'all',ariaLabel:'Copy command'},[text('Copy')])];}
      }
      if(node.children)node.children=node.children.map(child=>child.tagName==='table'?element('section',{className:['table-scroll'],tabIndex:0,ariaLabel:`Table ${++tableNumber}: ${nodeText(child.children?.find(n=>n.tagName==='thead')||child).slice(0,100)}. Scroll horizontally on small screens`},[child]):child);
    };
    visit(tree);
  };
  const result=await unified().use(remarkParse).use(remarkGfm).use(remarkRehype,{allowDangerousHtml:true}).use(rehypeRaw).use(rehypeSanitize).use(rehypeSlug).use(transform).use(rehypeStringify).process(source);
  return {html:String(result),headings};
}
