import"./kcc-soundlab-panel-0631.js?v=0.6.1";

const RESPONSE_TAG="kcc-measurement-response-0622";
const ResponseElement=customElements.get(RESPONSE_TAG);
const safe=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const median=values=>{if(!values.length)return 0;const sorted=[...values].sort((a,b)=>a-b),mid=Math.floor(sorted.length/2);return sorted.length%2?sorted[mid]:(sorted[mid-1]+sorted[mid])/2};
const smoothingFraction=id=>({raw:0,"1/24":24,"1/12":12,"1/6":6}[String(id||"raw")]??0);
const targetValue=(points,f)=>{if(!points?.length)return 0;const sorted=[...points].sort((a,b)=>Number(a.frequency_hz)-Number(b.frequency_hz));if(f<=Number(sorted[0].frequency_hz))return Number(sorted[0].gain_db)||0;if(f>=Number(sorted.at(-1).frequency_hz))return Number(sorted.at(-1).gain_db)||0;for(let i=0;i<sorted.length-1;i++){const a=sorted[i],b=sorted[i+1],fa=Number(a.frequency_hz),fb=Number(b.frequency_hz);if(f>=fa&&f<=fb){const t=(Math.log(f)-Math.log(fa))/(Math.log(fb)-Math.log(fa));return(Number(a.gain_db)||0)+((Number(b.gain_db)||0)-(Number(a.gain_db)||0))*t}}return 0};
const smoothPoints=(points,fraction)=>{const source=(points||[]).map(p=>({frequency_hz:Number(p.frequency_hz),spl_db:Number(p.spl_db)})).filter(p=>Number.isFinite(p.frequency_hz)&&Number.isFinite(p.spl_db));if(!fraction||source.length<3)return source;const sigma=1/(2*fraction),radius=sigma*3;return source.map(point=>{let weighted=0,total=0;for(const candidate of source){const distance=Math.abs(Math.log2(candidate.frequency_hz/point.frequency_hz));if(distance>radius)continue;const weight=Math.exp(-.5*Math.pow(distance/sigma,2));weighted+=candidate.spl_db*weight;total+=weight}return{frequency_hz:point.frequency_hz,spl_db:total?weighted/total:point.spl_db}})};
const comparisonFor=(response,target,smoothing)=>{const points=smoothPoints(response?.points||[],smoothingFraction(smoothing)),curve=target?.points||[];if(!points.length)return[];const offsets=points.map(p=>({frequency:p.frequency_hz,value:p.spl_db-targetValue(curve,p.frequency_hz)})),pool=offsets.filter(x=>x.frequency>=500&&x.frequency<=2000).map(x=>x.value),reference=median(pool.length?pool:offsets.map(x=>x.value));return points.map(p=>{const targetDb=targetValue(curve,p.frequency_hz),relative=p.spl_db-reference;return{frequency_hz:p.frequency_hz,delta_db:relative-targetDb}})};
const interpolate=(points,frequency)=>{if(!points?.length)return null;if(frequency<=points[0].frequency_hz)return Number(points[0].delta_db);if(frequency>=points.at(-1).frequency_hz)return Number(points.at(-1).delta_db);for(let i=0;i<points.length-1;i++){const a=points[i],b=points[i+1];if(frequency<a.frequency_hz||frequency>b.frequency_hz)continue;const t=(Math.log(frequency)-Math.log(a.frequency_hz))/(Math.log(b.frequency_hz)-Math.log(a.frequency_hz));return Number(a.delta_db)+(Number(b.delta_db)-Number(a.delta_db))*t}return null};

if(ResponseElement&&!ResponseElement.prototype.__kccMultiPosition0632){
 const proto=ResponseElement.prototype;
 proto.__kccMultiPosition0632=true;
 const baseLoad=proto.load;
 const baseRender=proto.render;
 const baseChange=proto.onChange;

 proto.multiPositionMeasurements=[];
 proto.multiPositionError="";

 proto.loadMultiPosition=async function(){
  const panel=this.panel(),channel=this.selectedChannel();
  if(!panel?.send){this.multiPositionMeasurements=[];return}
  try{
   const data=await panel.send("kcc_soundlab/get_multi_position_responses",{channel});
   this.multiPositionMeasurements=Array.isArray(data?.measurements)?data.measurements:[];
   this.multiPositionError="";
  }catch(err){this.multiPositionMeasurements=[];this.multiPositionError=String(err?.message||err)}
  this.render();
 };

 proto.load=async function(...args){
  this.multiPositionMeasurements=[];this.multiPositionError="";
  const result=await baseLoad.apply(this,args);
  await this.loadMultiPosition();
  return result;
 };

 proto.multiPositionContext=function(){
  const session=String(this.sessionId?.()||""),all=this.multiPositionMeasurements||[],current=all.find(item=>String(item.session_id)===session),position=String(current?.position||this.panel()?.workspace?.measurement_sessions?.find?.(item=>String(item.id)===session)?.position||"Driver seat"),others=all.filter(item=>String(item.session_id)!==session&&String(item.position)!==position);
  return{session,position,others,positions:new Set(others.map(item=>String(item.position)))};
 };

 proto.multiPositionComparisons=function(){
  const panel=this.panel(),target=panel?.workspace?.target_curve||{points:[]},smoothing=this.selectedSmoothing?.()||"raw",context=this.multiPositionContext();
  return context.others.map(item=>({item,points:comparisonFor(item.response,target,smoothing)})).filter(entry=>entry.points.length);
 };

 proto.multiPositionStats=function(){
  const panel=this.panel(),target=panel?.workspace?.target_curve||{points:[]},smoothing=this.selectedSmoothing?.()||"raw",primary=comparisonFor(this.response,target,smoothing),others=this.multiPositionComparisons();
  if(!primary.length||!others.length)return{meanSpread:null,within15:null,grade:"Need another position"};
  const errors=[];for(const entry of others)for(const point of primary){const other=interpolate(entry.points,point.frequency_hz);if(Number.isFinite(other))errors.push(Math.abs(other-point.delta_db))}
  if(!errors.length)return{meanSpread:null,within15:null,grade:"Need another position"};
  const meanSpread=errors.reduce((sum,value)=>sum+value,0)/errors.length,within15=errors.filter(value=>value<=1.5).length/errors.length*100,grade=meanSpread<=1&&within15>=80?"Strong":meanSpread<=1.5&&within15>=65?"Good":"Review";
  return{meanSpread,within15,grade};
 };

 proto.multiPositionFeatureMatch=function(item,comparisons=this.multiPositionComparisons()){
  const wantedSign=item.originalGain<0?1:-1,frequency=Number(item.originalFrequency||item.frequency),matchedPositions=new Set(),allPositions=new Set();
  for(const entry of comparisons){const position=String(entry.item.position||"Other");allPositions.add(position);const match=entry.points.some(point=>Math.abs(Math.log2(point.frequency_hz/frequency))<=.25&&Math.sign(point.delta_db)===wantedSign&&Math.abs(point.delta_db)>=1.5);if(match)matchedPositions.add(position)}
  return{matches:matchedPositions.size,total:allPositions.size};
 };

 proto.injectMultiPosition=function(){
  const host=this.querySelector(".response-card");if(!host||!this.response||host.querySelector("[data-multi-position-evidence]"))return;
  const context=this.multiPositionContext(),stats=this.multiPositionStats(),comparisons=this.multiPositionComparisons(),rows=this.confidenceRows?.()||[];
  const chips=rows.length&&context.positions.size?rows.map(item=>{const result=this.multiPositionFeatureMatch(item,comparisons),color=result.total&&result.matches===result.total?"#78d39a":result.matches?"#e2be67":"#ef9a9a";return`<span style="border:1px solid #30485c;border-radius:10px;padding:4px 7px;color:${color}">${Math.round(item.originalFrequency)} Hz · ${result.matches}/${result.total} positions</span>`}).join(""):"";
  const positionRows=context.others.map(entry=>`<div style="display:grid;grid-template-columns:120px 1fr auto;gap:10px;align-items:center;border-top:1px solid #21323d;padding:8px 0"><b style="color:#9dc8ea">${safe(entry.position)}</b><span>${safe(entry.session_name)}<small style="display:block;color:#788b99">${safe(entry.response?.source_name||"REW response")}</small></span><span style="color:#788b99">${Number(entry.repeat_count)||0} repeats</span></div>`).join("");
  const error=this.multiPositionError?`<div style="border:1px solid #713b3b;background:#281313;color:#ef9a9a;border-radius:8px;padding:9px;margin-top:10px">${safe(this.multiPositionError)}</div>`:"";
  const card=document.createElement("div");card.className="difference-panel";card.dataset.multiPositionEvidence="true";card.style.borderColor="#3e4f74";
  card.innerHTML=`<div class="difference-head"><div><small>MULTI-POSITION FOUNDATION · READ ONLY</small><strong>${context.positions.size?`${context.positions.size+1} positions available":"Add another measurement position"}</strong></div><span>Current: ${safe(context.position)}</span></div><div class="response-stats"><div><small>POSITIONS</small><strong>${context.positions.size+1}</strong><span>Current + ${context.positions.size} other</span></div><div><small>MEAN SPREAD</small><strong>${stats.meanSpread==null?"—":`${stats.meanSpread.toFixed(1)} dB`}</strong><span>Other positions vs current</span></div><div><small>WITHIN ±1.5 dB</small><strong>${stats.within15==null?"—":`${stats.within15.toFixed(0)}%`}</strong><span>Cross-position points</span></div><div><small>AGREEMENT</small><strong>${safe(stats.grade)}</strong><span>Read-only evidence</span></div></div>${chips?`<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;font-size:8px">${chips}</div>`:""}<div style="margin-top:10px">${positionRows||`<p class="muted-copy">Create or select another Measurement session with a different position, such as Passenger seat, and import a primary REW response for the same output. SoundLab will then compare response shape across positions.</p>`}</div>${error}<p class="muted-copy" style="margin-top:10px">v0.6.32 is evidence only. Cross-position results do not change Confidence, Guards, Prediction, Apply Preview or SoundLab EQ.</p>`;
  const repeat=host.querySelector("[data-measurement-repeatability]"),controlled=[...host.querySelectorAll(".difference-panel")].find(panel=>panel.querySelector("[data-eq-assistant-apply]")),meta=host.querySelector(".response-meta");if(repeat)repeat.after(card);else if(controlled)controlled.before(card);else if(meta)meta.before(card);else host.append(card);
 };

 proto.onChange=function(event){
  if(event.target.matches?.("[data-response-channel]")){this.multiPositionMeasurements=[];this.multiPositionError=""}
  return baseChange.call(this,event);
 };

 proto.render=function(...args){const result=baseRender.apply(this,args);this.injectMultiPosition();return result};
}
