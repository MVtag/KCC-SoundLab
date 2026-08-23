import"./kcc-soundlab-panel-0623.js?v=0.6.1";

const RESPONSE_TAG="kcc-measurement-response-0622";
const ResponseElement=customElements.get(RESPONSE_TAG);
const safe=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));

if(ResponseElement&&!ResponseElement.prototype.__kccApplyPreview0625){
 const proto=ResponseElement.prototype;
 proto.__kccApplyPreview0625=true;
 const baseInject=proto.injectControlledApply;
 const baseClick=proto.onClick;
 const baseChange=proto.onChange;

 proto.eqAssistantPreviewData=function(){
  const panel=this.panel(),session=this.sessionId(),channel=this.selectedChannel(),filters=this.activeAssistantFilters(),smoothing=this.selectedSmoothing(),channelData=panel?.workspace?.channels?.[channel],bands=channelData?.eq_bands||[],freeIndices=[];
  bands.forEach((band,index)=>{if(band&&!Boolean(band.enabled)&&Math.abs(Number(band.gain_db)||0)<.001)freeIndices.push(index)});
  const output=channelData?.output||`OUT ${String.fromCharCode(65+channel)}`,bandIndices=freeIndices.slice(0,filters.length),snapshotName=`EQ Assistant pre-apply · ${output}`;
  const data={session_id:String(session||""),channel:Number(channel),smoothing:String(smoothing||""),output:String(output),snapshot_name:snapshotName,band_indices:bandIndices,filters:filters.map(filter=>({frequency_hz:Number(filter.frequency_hz),gain_db:Number(filter.gain_db),q:Number(filter.q)}))};
  data.signature=JSON.stringify({session_id:data.session_id,channel:data.channel,smoothing:data.smoothing,band_indices:data.band_indices,filters:data.filters});
  return data;
 };

 proto.applyAssistantToEq=function(){
  const panel=this.panel(),preview=this.eqAssistantPreviewData();
  if(!panel?.send||!preview.session_id||!preview.filters.length||this.eqApplyStatus?.status==="active")return;
  if(preview.band_indices.length<preview.filters.length){this.eqApplyError=`Need ${preview.filters.length} unused EQ slots but only ${preview.band_indices.length} are available`;this.eqApplyPreview=null;this.render();return}
  this.eqApplyError="";
  this.eqApplyPreview=preview;
  this.render();
 };

 proto.confirmAssistantApply=async function(){
  const panel=this.panel(),preview=this.eqApplyPreview;
  if(!panel?.send||!preview||this.eqApplyStatus?.status==="active"||this.eqApplyBusy)return;
  const current=this.eqAssistantPreviewData();
  if(current.signature!==preview.signature){
   this.eqApplyPreview=current.filters.length&&current.band_indices.length>=current.filters.length?current:null;
   this.eqApplyError="Apply inputs changed after preview. Review the refreshed preview before confirming.";
   this.render();
   return;
  }
  this.eqApplyBusy=true;this.eqApplyError="";this.render();
  try{
   const data=await panel.send("kcc_soundlab/apply_eq_assistant",{session_id:preview.session_id,channel:preview.channel,smoothing:preview.smoothing,filters:preview.filters});
   if(data?.workspace)panel.workspace=data.workspace;
   panel.eqChannel=preview.channel;
   this.eqApplyStatus=data?.apply||null;
   this.eqApplyPreview=null;
   this.message=`Applied ${preview.filters.length} EQ Assistant filter${preview.filters.length===1?"":"s"} to ${preview.output}`;
  }catch(err){this.eqApplyError=String(err?.message||err)}
  finally{this.eqApplyBusy=false;this.render()}
 };

 proto.cancelAssistantApply=function(){this.eqApplyPreview=null;this.eqApplyError="";this.render()};

 proto.injectControlledApply=function(){
  baseInject.call(this);
  const preview=this.eqApplyPreview;
  if(!preview||this.eqApplyStatus?.status==="active")return;
  const applyButton=this.querySelector('[data-eq-assistant-apply="apply"]');
  const card=applyButton?.closest(".difference-panel");
  if(!applyButton||!card)return;
  const actions=applyButton.parentElement;
  const rows=preview.filters.map((filter,index)=>`<tr><td><b>#${Number(preview.band_indices[index])+1}</b></td><td>${safe(Number(filter.frequency_hz).toFixed(Number(filter.frequency_hz)<100?1:0))} Hz</td><td style="color:${Number(filter.gain_db)<0?"#67adff":"#e2be67"};font-weight:700">${Number(filter.gain_db)>0?"+":""}${safe(Number(filter.gain_db).toFixed(1))} dB</td><td>${safe(Number(filter.q).toFixed(2))}</td></tr>`).join("");
  const box=document.createElement("div");
  box.setAttribute("data-eq-apply-preview","true");
  box.style.cssText="border:1px solid #2e72b6;background:#0b1823;border-radius:9px;padding:12px;margin:12px 0";
  box.innerHTML=`<div class="difference-head"><div><small>APPLY PREVIEW · NO WRITE YET</small><strong>${safe(preview.output)} · ${preview.filters.length} active filter${preview.filters.length===1?"":"s"}</strong></div><span>${safe(preview.smoothing)} smoothing</span></div><div class="snapshot-summary" style="margin-top:10px"><span>Snapshot to create</span><strong>${safe(preview.snapshot_name)}</strong><span>Write target</span><strong>SoundLab EQ only · Goldhorn untouched</strong></div><div class="scroll" style="margin-top:10px"><table><thead><tr><th>EQ slot</th><th>Frequency</th><th>Gain</th><th>Q</th></tr></thead><tbody>${rows}</tbody></table></div><p class="muted-copy" style="margin:10px 0 0">Nothing has been written yet. Confirm only after the channel, slots and PEQ values above match what you intend to transfer.</p>`;
  if(actions)card.insertBefore(box,actions);else card.append(box);
  applyButton.dataset.eqAssistantApply="confirm";
  applyButton.textContent=this.eqApplyBusy?"Applying…":"Confirm Apply to SoundLab EQ";
  const cancel=document.createElement("button");
  cancel.type="button";
  cancel.dataset.eqAssistantApply="cancel";
  cancel.textContent="Cancel preview";
  cancel.style.cssText="border:1px solid #344451;background:#111a21;color:#b8c6d1;border-radius:8px;padding:9px 12px;cursor:pointer";
  actions?.insertBefore(cancel,applyButton.nextSibling);
 };

 proto.onClick=function(event){
  const control=event.target.closest("[data-eq-assistant-apply]");
  if(control){
   const action=String(control.dataset.eqAssistantApply||"");
   if(action==="confirm"){this.confirmAssistantApply();return}
   if(action==="cancel"){this.cancelAssistantApply();return}
  }
  return baseClick.call(this,event);
 };

 proto.onChange=function(event){
  const target=event.target;
  if(target?.matches?.("[data-assistant-toggle],[data-assistant-edit],[data-response-channel],[data-response-smoothing],[data-response-file]"))this.eqApplyPreview=null;
  return baseChange.call(this,event);
 };
}
