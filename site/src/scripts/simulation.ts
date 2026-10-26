import {qs,type Runtime} from './dom';
export function simulation(ctx:Runtime){
  const box=qs('[data-simulation]');if(!box)return;
  const log=qs('[data-sim-log]',box)!,prompt=qs('[data-sim-prompt]',box)!,actions=qs('[data-sim-actions]',box)!,status=qs('[data-sim-status]',box)!;
  const stages=[['e','Edit boot entry'],['rd.break','Add rd.break'],['Ctrl+X','Boot with Ctrl+X'],['mount -o remount,rw /sysroot','Remount /sysroot'],['chroot /sysroot','Enter sysroot'],['passwd root','Set root password'],['touch /.autorelabel','Create relabel marker'],['exit','Leave chroot'],['reboot','Reboot node2']];
  const commandForm=qs<HTMLFormElement>('[data-sim-form]',box)!,commandInput=qs<HTMLInputElement>('[data-sim-command]',box)!;
  let stage=0,relabelled=false,showing=false,run=0;
  const line=(value:string)=>{const p=document.createElement('p');p.textContent=value;log.append(p);log.scrollTop=log.scrollHeight;};
  const draw=()=>{
    actions.replaceChildren();commandInput.value='';commandForm.hidden=stage===0||stage===2||stage>=stages.length;if(stage>=stages.length){prompt.textContent='Login after the reboot.';const pass=relabelled;line(pass?'node2 login: root. Login successful.':'node2 login: root. Permission denied. SELinux labels were not restored.');status.textContent=pass?'Relabelled. You can log in.':'Forgot touch /.autorelabel? Reset the exercise and try again.';return;}
    prompt.textContent=`Next: ${stages[stage][0]}`;
    const button=document.createElement('button');button.type='button';button.className='btn btn--secondary';button.textContent=stages[stage][1];button.addEventListener('click',()=>advance(),{once:true});actions.append(button);
    if(stage===6){const skip=document.createElement('button');skip.type='button';skip.className='btn btn--quiet';skip.textContent='Skip the relabel marker';skip.addEventListener('click',()=>{line('Skipped touch /.autorelabel.');stage++;draw();},{once:true});actions.append(skip);}
  };
  function advance(){if(stage>=stages.length)return;const command=stages[stage][0];line(`${stage<3?'GRUB':'switch_root:/#'} ${command}`);if(stage===6)relabelled=true;stage++;draw();}
  const reset=()=>{run++;stage=0;relabelled=false;showing=false;log.replaceChildren();line('GRUB menu. Interrupt the boot to reset root’s password.');status.textContent='';draw();};
  ctx.on(commandForm,'submit',(event:SubmitEvent)=>{event.preventDefault();if(commandInput.value.trim()===stages[stage]?.[0]){status.textContent='';advance();commandInput.focus();}else status.textContent='Use the command shown above, or choose its button.';});
  ctx.on(qs('[data-sim-reset]',box),'click',reset);
  ctx.on(qs('[data-sim-show]',box),'click',()=>{reset();showing=true;const current=run;const play=()=>{if(!showing||ctx.signal.aborted||current!==run)return;advance();if(stage<stages.length)ctx.later(play,ctx.reduce()?100:650);else showing=false;};play();});
  ctx.on(window,'keydown',(event:KeyboardEvent)=>{if((event.target as Element).closest('input,textarea,select,dialog')||stage>=stages.length)return;const rect=box.getBoundingClientRect();if(rect.top>innerHeight||rect.bottom<0)return;if((stage===0&&event.key==='e')||(stage===2&&event.ctrlKey&&event.key.toLowerCase()==='x')){event.preventDefault();advance();}});
  reset();ctx.cleanup(()=>{showing=false;});
}
