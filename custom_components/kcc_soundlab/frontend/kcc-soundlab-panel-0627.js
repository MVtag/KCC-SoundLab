import"./kcc-soundlab-panel-0626.js?v=0.6.1";

const RESPONSE_TAG="kcc-measurement-response-0622";
const ResponseElement=customElements.get(RESPONSE_TAG);
const safe=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const DEEP_DIP_DB=-7;
const NARROW_DIP_DB=-4;
const NARROW_Q=3;

if(ResponseElement&&!ResponseElement.prototype.__kccNullBoostGuard0627){
 const proto=ResponseElement.prototype;
 proto.__kccNullBoostGuard0627=true;
 const baseRender=proto.render;

 proto.nullGuardContext=function(){return this.eqGuardContext?.()??`${this.sessionId()}|${this.selectedChannel()}|${this.selectedSmoothing()}`};
 proto.nullGuardStore=function(){const panel=this.panel();if(!panel)return new Map();panel.measurementEqNullGuardAuto??=new Map();return panel.measurementEqNullGuardAuto};
 proto.nullGuardRows=function(){
  const rows=[];
  const source=this.eqGuardCollectRows?.()||[];
  for(const item of source){
   const gain=Number(item.row.querySelector('[data-assistant-edit][data-field="gain_db"]')?.value),q=Number(item.row.querySelector('[data-assistant-edit][data-field="q"]')?.value),delta=parseFloat(String(item.row.children?.[6]?.textContent||""));
   if(Number.isFinite(gain)&&Number.isFinite(q)&&Number.isFinite(delta))rows.push({...item,gain,q,delta});
  }
  return rows;
 };
 proto.nullGuardReason=function(item){
  if(!(item.gain>0.05))return"";
  if(item.delta<=DEEP_DIP_DB)return"deep dip — boost blocked";
  if(item.delta<=NARROW_DIP_DB&&item.q>=NARROW_Q)return"narrow dip — boost blocked";
  return"";
 };
 proto.nullGuardSync=function(){
  if(!this.response)return false;
  const rows=this.nullGuardRows();if(!rows.length)return false;
  const context=this.nullGuardContext(),store=this.nullGuardStore(),previousNull=new Set(store.get(context)||[]),crossoverAuto=new Set(this.eqGuardStore?.().get(context)||[]),disabled=this.disabledKeys(),userDisabled=new Set([...disabled].filter(key=>!previousNull.has(key)&&!crossoverAuto.has(key))),currentNull=new Set();
  for(const item of rows){if(crossoverAuto.has(item.key))continue;if(this.nullGuardReason(item))currentNull.add(item.key)}
  const desired=new Set([...userDisabled,...crossoverAuto,...currentNull]),current=[...disabled].sort().join("|"),next=[...desired].sort().join("|");
  store.set(context,currentNull);
  if(current===next)return false;
  disabled.clear();for(const key of desired)disabled.add(key);
  this.eqApplyPreview=null;
  return true;
 };
 proto.nullGuardDecorate=function(){
  if(!this.response)return;
  const context=this.nullGuardContext(),auto=new Set(this.nullGuardStore().get(context)||[]),rows=this.nullGuardRows(),assistant=this.querySelector("[data-assistant-toggle]")?.closest(".difference-panel");
  for(const item of rows){
   if(!auto.has(item.key))continue;
   item.toggle.checked=false;item.toggle.disabled=true;item.row.style.opacity=".34";
   for(const input of item.row.querySelectorAll("[data-assistant-edit]"))input.disabled=true;
   const label=item.toggle.parentElement?.querySelector("span");if(label)label.textContent="Boost guarded";
   const typeCell=item.row.children?.[2];if(typeCell&&!typeCell.querySelector("[data-null-boost-guard-badge]")){const badge=document.createElement("small");badge.dataset.nullBoostGuardBadge="true";badge.textContent=this.nullGuardReason(item)||"risky boost blocked";badge.style.cssText="display:block;color:#ffb56b;margin-top:2px";typeCell.append(badge)}
  }
  if(!assistant||assistant.querySelector("[data-null-boost-guard-summary]"))return;
  const boostCount=rows.filter(item=>item.gain>0.05).length,excluded=auto.size,box=document.createElement("div");
  box.dataset.nullBoostGuardSummary="true";box.style.cssText="border:1px solid #624b30;background:#20170d;color:#d8ba8f;border-radius:8px;padding:9px;margin:10px 0;font-size:8px;line-height:1.5";
  box.innerHTML=`<b style="color:#ffb56b">NULL / BOOST GUARD</b> · ${safe(excluded)} of ${safe(boostCount)} boost suggestion${boostCount===1?"":"s"} guarded<br><span style="color:#9a8977">Cuts are never blocked here. Boost is guarded for dips ≤ ${safe(DEEP_DIP_DB)} dB, or dips ≤ ${safe(NARROW_DIP_DB)} dB when Q ≥ ${safe(NARROW_Q.toFixed(1))}. Guarded boosts are excluded from prediction, Apply Preview and SoundLab EQ transfer.</span>`;
  const crossover=assistant.querySelector("[data-eq-guard-summary]");if(crossover)crossover.after(box);else assistant.querySelector(".difference-head")?.after(box);
 };
 proto.render=function(...args){
  let result=baseRender.apply(this,args);
  if(this.nullGuardSync())result=baseRender.apply(this,args);
  this.nullGuardDecorate();
  return result;
 };
}
