import {qs,qsa,type Runtime} from './dom';
interface Task {key:string;title:string;exam:string;domain:string;domainTitle:string;difficulty:string;estimated_minutes:number;practice_only:boolean;objectiveText:string[];}
export function taskBank(ctx:Runtime){
  const bank=qs('[data-task-bank]');if(!bank)return;
  const data=JSON.parse(qs('#task-data')!.textContent||'[]') as Task[];
  const rows=new Map(qsa('[data-task]',bank).map(row=>[row.dataset.task!,row]));
  const form=qs<HTMLFormElement>('[data-bank-form]',bank)!, search=qs<HTMLInputElement>('[name=q]',form)!,domain=qs<HTMLSelectElement>('[name=domain]',form)!,sort=qs<HTMLSelectElement>('[name=sort]',form)!;
  const difficulties=qsa<HTMLInputElement>('[name^=difficulty-]',form),eligibility=qsa<HTMLInputElement>('[name^=eligibility-]',form);
  let exam='all',timer:ReturnType<typeof setTimeout>|undefined;
  const readURL=()=>{
    const p=new URLSearchParams(location.search);exam=['rhcsa','rhce'].includes(p.get('exam')||'')?p.get('exam')!:'all';
    search.value=p.get('q')||'';domain.value=p.get('domain')||'all';if(!domain.value)domain.value='all';
    sort.value=p.get('sort')||'title';if(!sort.value)sort.value='title';
    for(const [items,key] of [[difficulties,'difficulty'],[eligibility,'eligibility']] as const){const values=p.has(key)?p.get(key)!.split(','):items.map(i=>i.value);items.forEach(i=>{i.checked=values.includes(i.value);});}
  };
  const apply=(write=true,animate=true)=>{
    const levels=difficulties.filter(i=>i.checked).map(i=>i.value),eligible=eligibility.filter(i=>i.checked).map(i=>i.value),words=search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    qsa('[data-exam-filter]',bank).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.examFilter===exam)));
    const selected=data.filter(t=>(exam==='all'||t.exam===exam)&&(domain.value==='all'||domain.value===`${t.exam}.${t.domain}`)&&levels.includes(t.difficulty)&&eligible.includes(t.practice_only?'practice':'eligible')&&words.every(word=>`${t.title} ${t.exam} ${t.domainTitle} ${t.objectiveText.join(' ')}`.toLowerCase().includes(word)));
    const rank:Record<string,number>={easy:0,medium:1,hard:2};
    selected.sort((a,b)=>{let order=0;if(sort.value==='difficulty')order=rank[a.difficulty]-rank[b.difficulty];if(sort.value.startsWith('minutes'))order=(a.estimated_minutes-b.estimated_minutes)*(sort.value==='minutes-desc'?-1:1);if(sort.value==='exam')order=a.exam.localeCompare(b.exam);return order||a.title.localeCompare(b.title);});
    const positions=new Map<string,number>();if(animate&&!ctx.reduce())rows.forEach((row,key)=>{if(!row.hidden){const rect=row.getBoundingClientRect();if(rect.bottom>=0&&rect.top<=innerHeight)positions.set(key,rect.top);}});
    rows.forEach(row=>{row.hidden=true;});const table=qs('table',bank)!;
    selected.forEach(task=>{const row=rows.get(task.key)!;row.hidden=false;table.append(row);const old=positions.get(task.key);if(old!==undefined){const delta=old-row.getBoundingClientRect().top;if(Math.abs(delta)>1)row.animate([{transform:`translateY(${delta}px)`},{transform:'translateY(0)'}],{duration:220,easing:'cubic-bezier(.16,1,.3,1)'});}});
    qs('[data-bank-count]',bank)!.textContent=`${selected.length} of ${data.length} tasks`;
    qs('[data-bank-empty]',bank)!.hidden=selected.length>0;
    if(write){const p=new URLSearchParams();if(exam!=='all')p.set('exam',exam);if(domain.value!=='all')p.set('domain',domain.value);if(levels.length!==3)p.set('difficulty',levels.join(','));if(eligible.length!==2)p.set('eligibility',eligible.join(','));if(search.value.trim())p.set('q',search.value.trim());if(sort.value!=='title')p.set('sort',sort.value);history.replaceState(history.state,'',`${location.pathname}${p.size?'?'+p:''}${location.hash}`);}
  };
  ctx.on(form,'submit',(event:SubmitEvent)=>{event.preventDefault();apply();});
  ctx.on(form,'input',(event:InputEvent)=>{if(event.target===search){clearTimeout(timer);timer=ctx.later(()=>apply(),100);}});
  ctx.on(form,'change',()=>apply());
  qsa('[data-exam-filter]',bank).forEach(button=>ctx.on(button,'click',()=>{exam=button.dataset.examFilter!;if(domain.value!=='all'&&exam!=='all'&&!domain.value.startsWith(exam+'.'))domain.value='all';apply();}));
  qsa('[data-clear-filters]',bank).forEach(button=>ctx.on(button,'click',()=>{exam='all';form.reset();domain.value='all';sort.value='title';search.value='';apply();}));
  ctx.on(window,'popstate',()=>{readURL();apply(false,false);});
  readURL();apply(false,false);ctx.cleanup(()=>clearTimeout(timer));
}
