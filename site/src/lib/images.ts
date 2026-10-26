import {getImage} from 'astro:assets';
import home from '../../../docs/media/home.png';
import exam from '../../../docs/media/exam.png';
import results from '../../../docs/media/results.png';
export {home,exam,results};
let imageMap:Promise<Record<string,{src:string;width:number;height:number}>>;
export function guideImages(){
  imageMap ||= Promise.all(Object.entries({home,exam,results}).map(async([name,src])=>{
    const image=await getImage({src,width:1280,format:'webp'});
    return [`${name}.png`,{src:image.src,width:1280,height:Math.round(1280*src.height/src.width)}] as const;
  })).then(entries=>Object.fromEntries(entries));
  return imageMap;
}
