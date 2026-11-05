import {qs,type Runtime} from './dom';

// The Worker behind contact@ takes the form too and posts it to the same Discord channel.
// The endpoint lives here, not in the page's HTML, so form-spam crawlers don't find it.
const endpoint=import.meta.env.PUBLIC_CONTACT_ENDPOINT||'https://api.autorelabel.dpdns.org/contact';
const later='Not sent. Please try again later, or write to the address below.';
const failed='Couldn’t send it. Please try again, or write to the address below.';

export function contactForm(ctx:Runtime){
  const form=qs<HTMLFormElement>('[data-contact-form]');if(!form)return;
  const opened=performance.now(),status=qs('[data-form-status]',form)!,send=qs<HTMLButtonElement>('button[type="submit"]',form)!;
  const show=(text:string,kind='')=>{status.textContent=text;status.dataset.kind=kind;};
  ctx.on(form,'input',()=>{if(!send.disabled)show('');});
  ctx.on(form,'submit',async(event:SubmitEvent)=>{
    event.preventDefault();if(send.disabled)return;
    const body=new URLSearchParams();for(const [key,value] of new FormData(form))body.append(key,String(value));
    body.set('elapsed',String(Math.round((performance.now()-opened)/1000)));
    send.disabled=true;show('Sending…');
    try{
      const response=await fetch(endpoint,{method:'POST',body,signal:ctx.signal});
      const answer=await response.json().catch(()=>({})) as {error?:string};
      if(response.ok){form.reset();show('Sent. Thank you: it’s on its way to the author.','ok');}
      else show(response.status===429?later:response.status===400&&answer.error?answer.error:failed,'bad');
    }catch{if(!ctx.signal.aborted)show(failed,'bad');}
    finally{send.disabled=false;}
  });
}
