import {qs,type Runtime} from './dom';
export function cursor(ctx:Runtime){
  const ring=qs('[data-cursor-ring]'),dot=qs('[data-cursor-dot]');
  if(!ring||!dot)return;
  const root=document.documentElement,fine=matchMedia('(pointer:fine)');
  let frame=0,x=0,y=0,ringX=0,ringY=0,started=false,held=false,room:Element|null=null,theme='';
  const selected=()=>Boolean(getSelection()?.toString());
  const stop=()=>{root.dataset.cursorVisible='false';cancelAnimationFrame(frame);frame=0;started=false;ring.classList.remove('is-pressed');};
  const draw=()=>{ringX+=(x-ringX)*.18;ringY+=(y-ringY)*.18;ring.style.transform=`translate3d(${ringX}px,${ringY}px,0) translate(-50%,-50%)`;frame=Math.abs(x-ringX)>.05||Math.abs(y-ringY)>.05?requestAnimationFrame(draw):0;};
  ctx.on(document,'pointermove',(event:PointerEvent)=>{
    const target=event.target as Element;
    if(event.pointerType!=='mouse'||!fine.matches||ctx.reduce()||document.hidden||document.documentElement.dataset.motionPaused==='true'||held||event.buttons||selected()||target.closest('input,textarea,select,[contenteditable="true"]')){stop();return;}
    x=event.clientX;y=event.clientY;
    dot.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%)`;
    if(!started){ringX=x;ringY=y;started=true;}
    const currentRoom=target.closest('.room--night,.room--paper')||document.body;
    const currentTheme=root.dataset.theme||String(matchMedia('(prefers-color-scheme:dark)').matches);
    if(room!==currentRoom||theme!==currentTheme){room=currentRoom;theme=currentTheme;const styles=getComputedStyle(room),color=styles.getPropertyValue('--cursor').trim();ring.style.color=color;dot.style.color=color;ring.style.backgroundColor=styles.getPropertyValue('--bg').trim();}
    const label=(target.closest('[data-cursor]') as HTMLElement|null)?.dataset.cursor||'';
    if(ring.textContent!==label)ring.textContent=label;
    ring.classList.toggle('has-label',Boolean(label));root.dataset.cursorVisible='true';
    if(!frame)frame=requestAnimationFrame(draw);
  },{passive:true});
  ctx.on(document,'pointerdown',(event:PointerEvent)=>{held=true;if((event.target as Element).closest('button,a,summary,[role="button"]')&&!selected())ring.classList.add('is-pressed');else stop();});
  ctx.on(window,'pointerup',()=>{held=false;ring.classList.remove('is-pressed');if(selected())stop();});
  ctx.on(window,'pointercancel',()=>{held=false;stop();});
  ctx.on(window,'blur',()=>{held=false;stop();});
  ctx.on(document,'selectionchange',()=>{if(selected())stop();});
  ctx.on(document,'mouseout',(event:MouseEvent)=>{if(!event.relatedTarget)stop();});
  ctx.on(document,'focusin',(event:FocusEvent)=>{if((event.target as Element).matches('input,textarea,select'))stop();});
  ctx.on(window,'scroll',stop,{passive:true});ctx.on(fine,'change',stop);ctx.cleanup(stop);
}
