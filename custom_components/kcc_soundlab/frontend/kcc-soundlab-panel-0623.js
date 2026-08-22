import"./kcc-soundlab-panel.js?v=0.6.1";

const RESPONSE_TAG="kcc-measurement-response-0622";
const ResponseElement=customElements.get(RESPONSE_TAG);
const html=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const fmtDate=value=>{const date=new Date(value);return Number.isNaN(date.getTime())?String(value||"—"):date.toLocaleString()};

if(ResponseElement&&!ResponseElement.prototype.__kccControlledApply0623){
 const proto=ResponseElement.prototype;
 proto.__kccControlledApply0623=true;
 const originalRender=proto.render;
 const originalLoad=proto.load;
 const originalClick=proto.onClick;

 proto.activeAssistantFilters=function(){
  const filters=[];
  for(const toggle of this.querySelectorAll("[data-assistant-toggle]")){
   if(!toggle.checked)continue;
   const row=toggle.closest("tr");
   if(!row)continue;
   const values={};
   for(const input of row.querySelectorAll("[data-assistant-edit]"))values[String(input.dataset.field||"")]=Number(input.value);
   const frequency=Number(values.frequency_hz),gain=Number(values.gain_db),q=Number(values.q);
   if(Number.isFinite(frequency)&&Number.isFinite(gain)&&Number.isFinite(q))filters.push({frequency_hz:frequency,gain_db:gain,q});
  }
  return filters;
 };

 proto.freeEqSlots=function(){
  const panel=this.panel(),channel=this.selectedChannel(),bands=panel?.workspace?.channels?.[channel]?.eq_bands||[];
  return bands.filter(band=>band&& !Boolean(band.enabled)&&Math.abs(Number(band.gain_db)||0)<.001).length;
 };

 proto.loadEqApplyStatus=async function(){
  const panel=this.panel(),session=this.sessionId(),channel=this.selectedChannel();
  if(!panel?.send||!session){this.eqApplyLoading=false;return}
  this.eqApplyLoading=true;
  this.eqApplyError="";
  try{
   const data=await panel.send("kcc_soundlab/get_eq_assistant_apply",{session_id:session,channel});
   this.eqApplyStatus=data?.apply||null;
  }catch(err){this.eqApplyError=String(err?.message||err)}
  finally{this.eqApplyLoading=false;this.render()}
 };

 proto.load=async function(...args){
  this.eqApplyLoading=true;
  const result=await originalLoad.apply(this,args);
  await this.loadEqApplyStatus();
  return result;
 };

 proto.applyAssistantToEq=async function(){
  const panel=this.panel(),session=this.sessionId(),channel=this.selectedChannel(),filters=this.activeAssistantFilters();
  if(!panel?.send||!session||!filters.length||this.eqApplyStatus?.status==="active")return;
  const free=this.freeEqSlots(),output=panel?.workspace?.channels?.[channel]?.output||`OUT ${String.fromCharCode(65+channel)}`;
  if(free<filters.length){this.eqApplyError=`Need ${filters.length} unused EQ slots but only ${free} are available`;this.render();return}
  if(globalThis.confirm&&!globalThis.confirm(`Apply ${filters.length} active EQ Assistant filter${filters.length===1?"":"s"} to ${output}? SoundLab will create a full tuning snapshot first. Goldhorn is not changed.`))return;
  this.eqApplyBusy=true;this.eqApplyError="";this.render();
  try{
   const data=await panel.send("kcc_soundlab/apply_eq_assistant",{session_id:session,channel,smoothing:this.selectedSmoothing(),filters});
   if(data?.workspace)panel.workspace=data.workspace;
   panel.eqChannel=channel;
   this.eqApplyStatus=data?.apply||null;
   this.message=`Applied ${filters.length} EQ Assistant filter${filters.length===1?"":"s"} to ${output}`;
  }catch(err){this.eqApplyError=String(err?.message||err)}
  finally{this.eqApplyBusy=false;this.render()}
 };

 proto.restoreAssistantEq=async function(){
  const panel=this.panel(),session=this.sessionId(),channel=this.selectedChannel(),apply=this.eqApplyStatus;
  if(!panel?.send||!session||apply?.status!=="active")return;
  if(globalThis.confirm&&!globalThis.confirm("Restore the pre-apply tuning snapshot? This restores the full SoundLab tuning state captured immediately before EQ Assistant Apply."))return;
  this.eqApplyBusy=true;this.eqApplyError="";this.render();
  try{
   const data=await panel.send("kcc_soundlab/restore_eq_assistant_apply",{session_id:session,channel});
   if(data?.workspace)panel.workspace=data.workspace;
   panel.eqChannel=channel;
   this.eqApplyStatus=data?.apply||null;
   this.message="Pre-apply tuning snapshot restored";
  }catch(err){this.eqApplyError=String(err?.message||err)}
  finally{this.eqApplyBusy=false;this.render()}
 };

 proto.openAppliedEq=function(){const panel=this.panel();if(!panel)return;panel.eqChannel=this.selectedChannel();panel.view="eq";panel.render()};

 proto.injectControlledApply=function(){
  const host=this.querySelector(".response-card");
  if(!host)return;
  const active=this.activeAssistantFilters(),free=this.freeEqSlots(),apply=this.eqApplyStatus,isOutstanding=apply?.status==="active",canApply=Boolean(this.response)&&active.length>0&&free>=active.length&&!this.eqApplyBusy&&!this.eqApplyLoading&&!isOutstanding;
  if(!this.response&&!isOutstanding)return;
  const card=document.createElement("div");
  card.className="difference-panel";
  card.style.borderColor=isOutstanding?"#6b5424":"#28503a";
  const used=Array.isArray(apply?.band_indices)?apply.band_indices.map(index=>`#${Number(index)+1}`).join(", "):"—";
  const lastRestored=apply?.status==="restored"?`<div style="border:1px solid #28503a;background:#0d2118;color:#78d39a;border-radius:8px;padding:9px;margin:10px 0">Last controlled apply was restored ${html(fmtDate(apply.restored_at))}.</div>`:"";
  const outstanding=isOutstanding?`<div style="border:1px solid #6b5424;background:#241d0d;color:#e2be67;border-radius:8px;padding:10px;margin:10px 0"><b>ROLLBACK READY</b><br>${html(apply.filter_count)} filter${Number(apply.filter_count)===1?"":"s"} applied to ${html(apply.output)} · EQ slots ${html(used)}<br><small>Snapshot: ${html(apply.snapshot_name)} · ${html(fmtDate(apply.applied_at))}</small></div>`:"";
  const error=this.eqApplyError?`<div style="border:1px solid #713b3b;background:#281313;color:#ef9a9a;border-radius:8px;padding:9px;margin:10px 0">${html(this.eqApplyError)}</div>`:"";
  card.innerHTML=`<div class="difference-head"><div><small>CONTROLLED APPLY · SOUNDLAB EQ</small><strong>${isOutstanding?"Assistant filters applied · rollback available":"Transfer active filters with snapshot protection"}</strong></div><span>Goldhorn untouched</span></div>${lastRestored}${outstanding}${error}<div class="response-stats"><div><small>ACTIVE ASSISTANT FILTERS</small><strong>${active.length}</strong><span>Current analysis</span></div><div><small>UNUSED EQ SLOTS</small><strong>${free}</strong><span>Disabled + 0.0 dB</span></div><div><small>SNAPSHOT</small><strong>${isOutstanding?"Ready":"Auto"}</strong><span>Full tuning state</span></div><div><small>WRITE TARGET</small><strong>SoundLab only</strong><span>No Goldhorn link</span></div></div><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">${isOutstanding?`<button type="button" class="danger-btn" data-eq-assistant-apply="restore" ${this.eqApplyBusy?"disabled":""}>Restore pre-apply snapshot</button>`:`<button type="button" class="primary" data-eq-assistant-apply="apply" ${canApply?"":"disabled"}>${this.eqApplyBusy?"Applying…":`Apply ${active.length} active filter${active.length===1?"":"s"} to SoundLab EQ`}</button>`}<button type="button" data-eq-assistant-apply="open-eq">Open EQ</button></div><p style="margin-top:10px">Apply uses only currently active/tuned Assistant filters and fills unused EQ slots without overwriting active bands. A full tuning snapshot is created before the write. Restore returns the whole SoundLab tuning state to that pre-apply snapshot, so restore before making unrelated tuning changes.</p>`;
  const meta=host.querySelector(".response-meta");
  if(meta)meta.before(card);else host.append(card);
 };

 proto.render=function(...args){
  const result=originalRender.apply(this,args);
  this.injectControlledApply();
  return result;
 };

 proto.onClick=function(event){
  const control=event.target.closest("[data-eq-assistant-apply]");
  if(control){
   const action=String(control.dataset.eqAssistantApply||"");
   if(action==="apply")this.applyAssistantToEq();
   else if(action==="restore")this.restoreAssistantEq();
   else if(action==="open-eq")this.openAppliedEq();
   return;
  }
  return originalClick.call(this,event);
 };
}
