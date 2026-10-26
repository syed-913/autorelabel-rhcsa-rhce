import {qs,qsa,type Runtime} from './dom';
import {href} from '../lib/urls';
let searchModule:Promise<any>|undefined;
export function docsSearch(ctx:Runtime){
  const dialog=qs<HTMLDialogElement>('[data-search-dialog]')!,input=qs<HTMLInputElement>('[data-docs-search]')!,results=qs('[data-search-results]')!,status=qs('[data-search-status]')!;
  let opener:HTMLElement|null=null,sequence=0,timer:ReturnType<typeof setTimeout>|undefined;
  const open=(trigger?:HTMLElement)=>{if(dialog.open)return;opener=trigger||document.activeElement as HTMLElement;dialog.showModal();document.body.classList.add('has-dialog');input.focus();};
  const close=()=>{dialog.close();document.body.classList.remove('has-dialog');opener?.focus({preventScroll:true});};
  qsa('[data-open-search]').forEach(button=>ctx.on(button,'click',()=>open(button)));
  ctx.on(qs('[data-close-search]'),'click',close);ctx.on(dialog,'cancel',(event:Event)=>{event.preventDefault();close();});
  ctx.on(qs('[data-docs-search-form]'),'submit',(event:Event)=>{event.preventDefault();input.dispatchEvent(new Event('input',{bubbles:true}));});
  ctx.on(input,'input',()=>{
    const request=++sequence;clearTimeout(timer);
    timer=ctx.later(async()=>{
      const query=input.value.trim();results.replaceChildren();if(!query){status.textContent='Search the user guide and frequently asked questions.';return;}
      status.textContent='Searching…';
      try{
        const modulePath=href('/pagefind/pagefind.js');searchModule ||= import(modulePath);
        const pagefind=await searchModule;const response=await pagefind.search(query);const found=await Promise.all(response.results.slice(0,12).map((result:any)=>result.data()));
        if(request!==sequence||ctx.signal.aborted)return;
        status.textContent=`${response.results.length} result${response.results.length===1?'':'s'} for “${query}”`;
        for(const result of found){const link=document.createElement('a');link.href=result.url;link.className='search-result';const heading=document.createElement('strong');heading.textContent=result.meta.title||'User guide';const excerpt=document.createElement('span');excerpt.innerHTML=result.excerpt;link.append(heading,excerpt);results.append(link);}
        if(!found.length)status.textContent='No matching pages. Try a shorter phrase or browse the guide.';
      }catch{searchModule=undefined;if(request===sequence&&!ctx.signal.aborted)status.textContent='Search could not load. Try again, or browse the guide below.';}
    },130);
  });
  ctx.on(dialog,'click',(event:MouseEvent)=>{if((event.target as Element).closest('a')){dialog.close();document.body.classList.remove('has-dialog');}});
  ctx.cleanup(()=>{clearTimeout(timer);if(dialog.open)dialog.close();});
  return open;
}
