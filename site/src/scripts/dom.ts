export const qs = <T extends HTMLElement = HTMLElement>(selector:string, scope:ParentNode=document) => scope.querySelector<T>(selector);
export const qsa = <T extends HTMLElement = HTMLElement>(selector:string, scope:ParentNode=document) => [...scope.querySelectorAll<T>(selector)];
export interface Runtime {
  on:(target:EventTarget|null,type:string,handler:(event:any)=>void,options?:AddEventListenerOptions)=>void;
  cleanup:(fn:()=>void)=>void;
  later:(fn:()=>void,ms:number)=>ReturnType<typeof setTimeout>;
  reduce:()=>boolean;
  announce:(message:string,error?:boolean)=>void;
  signal:AbortSignal;
}
