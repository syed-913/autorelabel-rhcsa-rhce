import {qs,qsa,type Runtime} from './dom';

// Feature recordings: muted, looping, and playing only while they are on screen. Nothing is
// downloaded before that (preload="none"). Anyone who prefers reduced motion starts them by hand
// with the controls, which are there for everyone, so a loop can always be paused. A pause by
// hand sticks: scrolling away and back doesn't start that video again.
export function loopVideos(ctx:Runtime){
  const videos=qsa('[data-loop]').map(frame=>qs<HTMLVideoElement>('video',frame)).filter((v):v is HTMLVideoElement=>!!v);
  if(!videos.length||ctx.reduce()||!('IntersectionObserver' in window))return;
  const held=new WeakSet<HTMLVideoElement>(),ours=new WeakSet<HTMLVideoElement>();
  const seen=new IntersectionObserver(entries=>entries.forEach(entry=>{
    const video=entry.target as HTMLVideoElement;
    if(entry.isIntersecting){if(!held.has(video))video.play().catch(()=>{});}
    else if(!video.paused){ours.add(video);video.pause();}
  }),{threshold:.45});
  videos.forEach(video=>{
    seen.observe(video);
    ctx.on(video,'pause',()=>{if(ours.has(video))ours.delete(video);else if(!document.hidden)held.add(video);});
    ctx.on(video,'play',()=>held.delete(video));
  });
  ctx.cleanup(()=>{seen.disconnect();videos.forEach(video=>{ours.add(video);video.pause();});});
}
