import"./kcc-soundlab-panel-0627.js?v=0.6.1";

const RESPONSE_TAG="kcc-measurement-response-0622";
const ResponseElement=customElements.get(RESPONSE_TAG);

if(ResponseElement&&!ResponseElement.prototype.__kccGuardResetVisibility0628){
 const proto=ResponseElement.prototype;
 proto.__kccGuardResetVisibility0628=true;
 const baseRender=proto.render;

 proto.guardResetVisibility=function(){
  const guardedRows=new Set();
  for(const badge of this.querySelectorAll("[data-eq-guard-badge],[data-null-boost-guard-badge]")){
   const row=badge.closest("tr");
   if(row)guardedRows.add(row);
  }
  for(const row of guardedRows){
   row.style.opacity="1";
   const cells=[...row.children];
   cells.forEach((cell,index)=>{cell.style.opacity=index===cells.length-1?"1":".34"});
   const reset=row.querySelector("[data-assistant-reset]");
   if(!reset)continue;
   const modified=!reset.disabled;
   reset.textContent=modified?"Reset tune":"Reset";
   if(modified){
    reset.style.background="#111a21";
    reset.style.borderColor="#4d7da8";
    reset.style.color="#d9e8f2";
    reset.style.cursor="pointer";
    reset.title="Restore this tuned EQ Assistant filter to its original suggested values";
   }
  }
 };

 proto.render=function(...args){
  const result=baseRender.apply(this,args);
  this.guardResetVisibility();
  return result;
 };
}
