import"./kcc-soundlab-panel-0628.js?v=0.6.1";

const RESPONSE_TAG="kcc-measurement-response-0622";
const ResponseElement=customElements.get(RESPONSE_TAG);
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const median=values=>{if(!values.length)return 0;const sorted=[...values].sort((a,b)=>a-b),mid=Math.floor(sorted.length/2);return sorted.length%2?sorted[mid]:(sorted[mid-1]+sorted[mid])/2};
const targetValue=(points,f)=>{if(!points?.length)return 0;const sorted=[...points].sort((a,b)=>Number(a.frequency_hz)-Number(b.frequency_hz));if(f<=Number(sorted[0].frequency_hz))return Number(sorted[0].gain_db)||0;if(f>=Number(sorted.at(-1).frequency_hz))return Number(sorted.at(-1).gain_db)||0;for(let i=0;i<sorted.length-1;i++){const a=sorted[i],b=sorted[i+1],fa=Number(a.frequency_hz),fb=Number(b.frequency_hz);if(f>=fa&&f<=fb){const t=(Math.log(f)-Math.log(fa))/(Math.log(fb)-Math.log(fa));return(Number(a.gain_db)||0)+((Number(b.gain_db)||0)-(Number(a.gain_db)||0))*t}}return 0};
const smoothPoints=(points,fraction)=>{const source=points.map(p=>({frequency_hz:Number(p.frequency_hz),spl_db:Number(p.spl_db)})).filter(p=>Number.isFinite(p.frequency_hz)&&Number.isFinite(p.spl_db));if(!fraction||source.length<3)return source;const sigma=1/(2*fraction),radius=sigma*3;return source.map(point=>{let weighted=0,total=0;for(const candidate of source){const distance=Math.abs(Math.log2(candidate.frequency_hz/point.frequency_hz));if(distance>radius)continue;const weight=Math.exp(-.5*Math.pow(distance/sigma,2));weighted+=candidate.spl_db*weight;total+=weight}return{frequency_hz:point.frequency_hz,spl_db:total?weighted/total:point.spl_db}})};
const comparisonFor=(response,target,fraction)=>{const points=smoothPoints(response?.points||[],fraction),curve=target?.points||[];if(!points.length)return[];const offsets=points.map(p=>({frequency:p.frequency_hz,value:p.spl_db-targetValue(curve,p.frequency_hz)})),pool=offsets.filter(x=>x.frequency>=500&&x.frequency<=2000).map(x=>x.value),reference=median(pool.length?pool:offsets.map(x=>x.value));return points.map(p=>{const targetDb=targetValue(curve,p.frequency_hz),relative=p.spl_db-reference;return{...p,delta_db:relative-targetDb}})};
const featureWidth=(points,index)=>{const center=points[index],sign=Math.sign(center.delta_db)||1,half=Math.abs(center.delta_db)*.5;let left=index,right=index;while(left>0&&Math.sign(points[left-1].delta_db)===sign&&Math.abs(points[left-1].delta_db)>=half)left--;while(right<points.length-1&&Math.sign(points[right+1].delta_db)===sign&&Math.abs(points[right+1].delta_db)>=half)right++;return Math.max(.16,Math.log2(points[right].frequency_hz/points[left].frequency_hz)||.16)};
const suggestionsFor=points=>{const candidates=[];for(let i=1;i<points.length-1;i++){const point=points[i],delta=Number(point.delta_db),frequency=Number(point.frequency_hz);if(!Number.isFinite(delta)||!Number.isFinite(frequency)||frequency<25||frequency>18000||Math.abs(delta)<1.5)continue;const prev=Number(points[i-1].delta_db),next=Number(points[i+1].delta_db),isPeak=delta>0&&delta>=prev&&delta>next,isDip=delta<0&&delta<=prev&&delta<next;if(!isPeak&&!isDip)continue;if(isDip&&Math.abs(delta)<2.5)continue;const width=featureWidth(points,i);if(width<.16)continue;const q=clamp(1/width,.45,6),gain=isPeak?-clamp(Math.abs(delta)*.9,1,6):clamp(Math.abs(delta)*.6,1,3),score=Math.abs(delta)*(isPeak?1.15:.72)*clamp(width/.35,.75,1.35);candidates.push({frequency_hz:frequency,gain_db:gain,q,score})}candidates.sort((a,b)=>b.score-a.score);const selected=[];for(const candidate of candidates){if(selected.some(item=>Math.abs(Math.log2(candidate.frequency_hz/item.frequency_hz))<.6))continue;selected.push(candidate);if(selected.length>=5)break}return selected};

if(ResponseElement&&!ResponseElement.prototype.__kccEqConfidence0629){
 const proto=ResponseElement.prototype;
 proto.__kccEqConfidence0629=true;
 const baseRender=proto.render;

 proto.confidenceSmoothingSets=function(){
  const panel=this.panel(),target=panel?.workspace?.target_curve||{points:[]};
  return[24,12,6].map(fraction=>suggestionsFor(comparisonFor(this.response,target,fraction)));
 };
 proto.confidenceRows=function(){
  const rows=[];
  for(const toggle of this.querySelectorAll("[data-assistant-toggle]")){
   const row=toggle.closest("tr"),key=String(toggle.dataset.filterKey||""),parts=key.split("|"),originalFrequency=Number(parts[0]),originalGain=Number(parts[1]),frequency=Number(row?.querySelector('[data-assistant-edit][data-field="frequency_hz"]')?.value),gain=Number(row?.querySelector('[data-assistant-edit][data-field="gain_db"]')?.value),q=Number(row?.querySelector('[data-assistant-edit][data-field="q"]')?.value),delta=parseFloat(String(row?.children?.[6]?.textContent||""));
   if(row&&key&&[originalFrequency,originalGain,frequency,gain,q,delta].every(Number.isFinite))rows.push({row,key,originalFrequency,originalGain,frequency,gain,q,delta});
  }
  return rows;
 };
 proto.confidenceFor=function(item,sets){
  const guarded=Boolean(item.row.querySelector("[data-eq-guard-badge],[data-null-boost-guard-badge]"));
  if(guarded)return{level:"Avoid",score:0,reasons:["blocked by active safety guard"],matches:0};
  let score=50;const reasons=[];
  const isCut=item.gain<-.05,isBoost=item.gain>.05,absDelta=Math.abs(item.delta);
  if(isCut){score+=12;reasons.push("cut preferred")}else if(isBoost){score-=3;reasons.push("boost needs review")}
  if(absDelta>=4){score+=10;reasons.push("strong repeatable feature candidate")}else if(absDelta>=2.5){score+=5}else score-=5;
  if(item.q>=.7&&item.q<=2.5){score+=10;reasons.push("broad/moderate Q")}else if(item.q<=3.2)score+=3;else if(item.q<=4)score-=5;else score-=10;
  const direction=Math.sign(item.originalGain),matches=sets.filter(set=>set.some(candidate=>Math.sign(candidate.gain_db)===direction&&Math.abs(Math.log2(candidate.frequency_hz/item.originalFrequency))<=.4)).length;
  if(matches===3){score+=20;reasons.push("seen in 3/3 smoothed analyses")}else if(matches===2){score+=10;reasons.push("seen in 2/3 smoothed analyses")}else if(matches===1){score-=5;reasons.push("seen in only 1/3 smoothed analyses")}else{score-=15;reasons.push("not repeated in smoothed analyses")}
  const limits=this.eqGuardLimits?.();
  if(limits){const low=Math.max(20,Number(limits.low)||20),high=Math.min(20000,Number(limits.high)||20000),edge=Math.min(Math.log2(item.frequency/low),Math.log2(high/item.frequency));if(edge>=1){score+=8;reasons.push("well inside crossover passband")}else if(edge>=.5)score+=4;else if(edge<.25){score-=10;reasons.push("close to crossover guard edge")}}
  const smoothing=String(this.selectedSmoothing?.()||"raw");if(smoothing==="1/6")score+=5;else if(smoothing==="1/12")score+=3;else if(smoothing==="raw")score-=4;
  if(item.row.children?.[2]?.textContent?.includes("tuned")){score-=5;reasons.push("manually tuned — verify")}
  score=Math.round(clamp(score,0,100));
  return{level:score>=75?"High confidence":"Review",score,reasons,matches};
 };
 proto.decorateConfidence=function(){
  if(!this.response)return;
  const rows=this.confidenceRows();if(!rows.length)return;
  const sets=this.confidenceSmoothingSets(),results=[];
  for(const item of rows){
   const result=this.confidenceFor(item,sets);results.push(result);
   const cell=item.row.children?.[2];if(!cell||cell.querySelector("[data-eq-confidence]"))continue;
   const badge=document.createElement("small");badge.dataset.eqConfidence="true";
   const palette=result.level==="High confidence"?{border:"#2e6b43",bg:"#10251a",color:"#78d39a"}:result.level==="Avoid"?{border:"#713b3b",bg:"#281313",color:"#ef9a9a"}:{border:"#6b5424",bg:"#241d0d",color:"#e2be67"};
   badge.textContent=result.level==="Avoid"?"Avoid · guarded":`${result.level} · ${result.score}/100`;
   badge.title=`Confidence factors: ${result.reasons.join(" · ")} · smoothing repeatability ${result.matches}/3`;
   badge.style.cssText=`display:inline-block;margin-top:4px;border:1px solid ${palette.border};background:${palette.bg};color:${palette.color};border-radius:10px;padding:3px 6px;font-size:7px;white-space:nowrap`;
   cell.append(badge);
  }
  const assistant=this.querySelector("[data-assistant-toggle]")?.closest(".difference-panel");if(!assistant||assistant.querySelector("[data-eq-confidence-summary]"))return;
  const high=results.filter(x=>x.level==="High confidence").length,review=results.filter(x=>x.level==="Review").length,avoid=results.filter(x=>x.level==="Avoid").length,box=document.createElement("div");
  box.dataset.eqConfidenceSummary="true";box.style.cssText="border:1px solid #30485c;background:#0d1922;color:#a8c4d8;border-radius:8px;padding:9px;margin:10px 0;font-size:8px;line-height:1.5";
  box.innerHTML=`<b style="color:#69b2ff">EQ ASSISTANT CONFIDENCE</b> · <span style="color:#78d39a">${high} high</span> · <span style="color:#e2be67">${review} review</span> · <span style="color:#ef9a9a">${avoid} avoid</span><br><span style="color:#8195a4">Quality score weighs cut/boost direction, measured Δ, Q, crossover distance, current smoothing and whether the same feature repeats at 1/24, 1/12 and 1/6 octave. Confidence is advisory; existing guards remain the only automatic block.</span>`;
  const nullGuard=assistant.querySelector("[data-null-boost-guard-summary]"),crossGuard=assistant.querySelector("[data-eq-guard-summary]");if(nullGuard)nullGuard.after(box);else if(crossGuard)crossGuard.after(box);else assistant.querySelector(".difference-head")?.after(box);
 };
 proto.render=function(...args){const result=baseRender.apply(this,args);this.decorateConfidence();return result};
}
