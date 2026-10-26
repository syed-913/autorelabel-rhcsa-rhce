import {qs,qsa,type Runtime} from './dom';
export function accordions(ctx:Runtime){
  qsa<HTMLDetailsElement>('.accordion details').forEach(details=>{
    const summary=qs('summary',details)!, answer=qs('.answer',details);
    let expanded=details.open,animation:Animation|null=null;
    const sync=()=>{details.dataset.expanded=String(expanded);summary.setAttribute('aria-expanded',String(expanded));if(answer)answer.inert=!expanded;};
    const settle=()=>{animation?.cancel();animation=null;details.open=expanded;details.style.removeProperty('overflow');sync();};
    sync();
    ctx.on(summary,'click',(event:MouseEvent)=>{
      event.preventDefault();
      const start=details.getBoundingClientRect().height;
      animation?.cancel();animation=null;
      expanded=!expanded;sync();
      if(ctx.reduce()){settle();return;}
      details.open=true;
      const border=parseFloat(getComputedStyle(details).borderBottomWidth)||0;
      const end=expanded?details.scrollHeight+border:summary.getBoundingClientRect().height+border;
      details.style.overflow='clip';
      const current=details.animate([{height:`${start}px`},{height:`${end}px`}],{duration:expanded?320:240,easing:'cubic-bezier(.16,1,.3,1)'});
      animation=current;
      current.finished.then(()=>{if(animation===current)settle();}).catch(()=>{});
    });
    ctx.on(details,'toggle',()=>{if(!animation){expanded=details.open;sync();}});
    ctx.cleanup(()=>{animation?.cancel();});
  });
}
