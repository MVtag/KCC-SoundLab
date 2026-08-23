import"./kcc-soundlab-panel-0625.js?v=0.6.1";

const RESPONSE_TAG="kcc-measurement-response-0622";
const ResponseElement=customElements.get(RESPONSE_TAG);
const safe=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const GUARD_OCTAVES=1/3;
const GUARD_RATIO=Math.pow(2,GUARD_OCTAVES);

if(ResponseElement&&!ResponseElement.prototype.__kccCrossoverGuard0626){
 const proto=ResponseElement.prototype;
 proto.__kccCrossoverGuard0626=true;
 const baseRender=proto.render;

 proto.eqGuardContext=function(){return`${this.sessionId()}|${this.selectedChannel()}|${this.selectedSmoothing()}`};
 proto.eqGuardStore=function(){const panel=this.panel();if(!panel)return new Map();panel.measurementEqGuardAuto??=new Map();return panel.measurementEqGuardAuto};
 proto.eqGuardLimits=function(){
  const panel=this.panel(),channel=this.selectedChannel(),raw=panel?.workspace?.channels?.[channel]||{},hpf=Number(raw.hpf_hz),lpf=Number(raw.lpf_hz),hasHpf=Number.isFinite(hpf)&&hpf>20.01,hasLpf=Number.isFinite(lpf)&&lpf<19999;
  let low=hasHpf?Math.min(20000,hpf*GUARD_RATIO):20,high=hasLpf?Math.max(20,lpf/GUARD_RATIO):20000;
  if(low>high){const center=Math.sqrt(Math.max(20,hpf||20)*Math.min(20000,lpf||20000));low=center;high=center}
  return{hpf:Number.isFinite(hpf)?hpf:20,lpf:Number.isFinite(lpf)?lpf:20000,hasHpf,hasLpf,low,high};
 };
 proto.eqGuardCollectRows=function(){
  const rows=[];
  for(const toggle of this.querySelectorAll("[data-assistant-toggle]")){
   const row=toggle.closest("tr"),input=row?.querySelector('[data-assistant-edit][data-field="frequency_hz"]'),frequency=Number(input?.value),key=String(toggle.dataset.filterKey||"");
   if(row&&key&&Number.isFinite(frequency))rows.push({row,toggle,key,frequency});
  }
  return rows;
 };
 proto.eqGuardSync=function(){
  if(!this.response)return false;
  const rows=this.eqGuardCollectRows();if(!rows.length)return false;
  const limits=this.eqGuardLimits(),context=this.eqGuardContext(),store=this.eqGuardStore(),previousAuto=new Set(store.get(context)||[]),disabled=this.disabledKeys(),userDisabled=new Set([...disabled].filter(key=>!previousAuto.has(key))),currentAuto=new Set(rows.filter(item=>item.frequency<limits.low||item.frequency>limits.high).map(item=>item.key)),desired=new Set([...userDisabled,...currentAuto]);
  const current=[...disabled].sort().join("|");const next=[...desired].sort().join("|");
  store.set(context,currentAuto);
  if(current===next)return false;
  disabled.clear();for(const key of desired)disabled.add(key);
  this.eqApplyPreview=null;
  return true;
 };
 proto.eqGuardDecorate=function(){
  if(!this.response)return;
  const limits=this.eqGuardLimits(),context=this.eqGuardContext(),auto=new Set(this.eqGuardStore().get(context)||[]),rows=this.eqGuardCollectRows(),assistant=this.querySelector("[data-assistant-toggle]")?.closest(".difference-panel");
  for(const item of rows){
   if(!auto.has(item.key))continue;
   item.toggle.checked=false;item.toggle.disabled=true;item.row.style.opacity=".34";
   for(const input of item.row.querySelectorAll("[data-assistant-edit]"))input.disabled=true;
   const label=item.toggle.parentElement?.querySelector("span");if(label)label.textContent="Guarded";
   const typeCell=item.row.children?.[2];if(typeCell&&!typeCell.querySelector("[data-eq-guard-badge]")){const badge=document.createElement("small");badge.dataset.eqGuardBadge="true";badge.textContent="outside crossover guard";badge.style.cssText="display:block;color:#e2be67;margin-top:2px";typeCell.append(badge)}
  }
  if(!assistant||assistant.querySelector("[data-eq-guard-summary]"))return;
  const excluded=auto.size,low=Math.round(limits.low),high=Math.round(limits.high),hpfText=limits.hasHpf?`${Math.round(limits.hpf)} Hz HPF`:"no active HPF edge",lpfText=limits.hasLpf?`${Math.round(limits.lpf)} Hz LPF`:"no active LPF edge",box=document.createElement("div");
  box.dataset.eqGuardSummary="true";box.style.cssText="border:1px solid #365166;background:#0d1922;color:#9fc4dc;border-radius:8px;padding:9px;margin:10px 0;font-size:8px;line-height:1.5";
  box.innerHTML=`<b style="color:#69b2ff">CROSSOVER EQ GUARD</b> · safe correction range <b>${safe(low)} Hz–${safe(high)} Hz</b> · ${safe(excluded)} suggestion${excluded===1?"":"s"} guarded<br><span style="color:#788b99">⅓-octave margin from ${safe(hpfText)} / ${safe(lpfText)}. Guarded suggestions are excluded from prediction, Apply Preview and SoundLab EQ transfer.</span>`;
  const head=assistant.querySelector(".difference-head");head?.after(box);
 };
 proto.render=function(...args){
  let result=baseRender.apply(this,args);
  if(this.eqGuardSync())result=baseRender.apply(this,args);
  this.eqGuardDecorate();
  return result;
 };
}
