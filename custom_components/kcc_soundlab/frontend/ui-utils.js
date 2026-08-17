export const COLORS=["#348cff","#59a0ff","#63d66d","#ffb328","#b866ff","#43d8d8","#ff6b7a","#8ecbff","#a9db65","#ffc76b","#d38aff","#62e4b3"];
export const PROFILE=[
 {speaker:"BLAM FRS2N50 L",role:"Full-range"},{speaker:"BLAM FRS2N50 R",role:"Full-range"},
 {speaker:"BLAM 165 LSQ L",role:"Midbass"},{speaker:"BLAM 165 LSQ R",role:"Midbass"},
 {speaker:"BLAM SuperSub12",role:"Subwoofer"}
];
export const FILTERS=["Butterworth","Linkwitz-Riley","Bessel"];
export const SLOPES=[6,12,18,24,30,36,42,48].map(v=>`${v} dB/oct`);
export const PRESETS=["Driver SQ","Front Both","Bass Mode","Tuning"];
export const letter=i=>String.fromCharCode(65+i);
export const slug=i=>`out_${letter(i).toLowerCase()}`;
export const profile=i=>PROFILE[i]||{speaker:`OUT ${letter(i)}`,role:"DSP output"};
export const stateObj=(hass,id)=>id?hass?.states?.[id]||null:null;
export function findEntity(hass,domain,index,key,label=""){
 const expected=`${domain}.kcc_soundlab_${slug(index)}_${key}`; if(stateObj(hass,expected)) return expected;
 const out=`out ${letter(index).toLowerCase()}`, words=key.replaceAll("_"," ").toLowerCase(), alt=label.toLowerCase();
 return Object.keys(hass?.states||{}).find(id=>{if(!id.startsWith(`${domain}.`))return false;const n=String(hass.states[id].attributes?.friendly_name||"").toLowerCase();return n.includes(out)&&(n.includes(words)||(alt&&n.includes(alt)));})||null;
}
export function findPreset(hass){
 if(stateObj(hass,"select.kcc_soundlab_preset"))return "select.kcc_soundlab_preset";
 return Object.keys(hass?.states||{}).find(id=>id.startsWith("select.")&&String(hass.states[id].attributes?.friendly_name||"").toLowerCase().includes("soundlab")&&String(hass.states[id].attributes?.friendly_name||"").toLowerCase().endsWith("preset"))||null;
}
export function findReference(hass){
 if(stateObj(hass,"sensor.kcc_soundlab_reference_channel"))return "sensor.kcc_soundlab_reference_channel";
 return Object.keys(hass?.states||{}).find(id=>id.startsWith("sensor.")&&String(hass.states[id].attributes?.friendly_name||"").toLowerCase().includes("time alignment reference"))||null;
}
export function num(hass,id,fallback=0){const s=stateObj(hass,id);if(!s||["unknown","unavailable"].includes(s.state))return fallback;const v=Number(s.state);return Number.isFinite(v)?v:fallback;}
export function text(hass,id,fallback="—"){const s=stateObj(hass,id);return(!s||["unknown","unavailable"].includes(s.state))?fallback:String(s.state);}
export function channelData(hass,index){
 const ids={
  distance:findEntity(hass,"number",index,"distance","distance"),gain:findEntity(hass,"number",index,"gain","gain"),phase:findEntity(hass,"number",index,"phase","phase"),
  hpf:findEntity(hass,"number",index,"hpf_frequency","hpf frequency"),lpf:findEntity(hass,"number",index,"lpf_frequency","lpf frequency"),
  polarity:findEntity(hass,"select",index,"polarity","polarity"),hpfType:findEntity(hass,"select",index,"hpf_type","hpf type"),hpfSlope:findEntity(hass,"select",index,"hpf_slope","hpf slope"),
  lpfType:findEntity(hass,"select",index,"lpf_type","lpf type"),lpfSlope:findEntity(hass,"select",index,"lpf_slope","lpf slope"),
  delay:findEntity(hass,"sensor",index,"calculated_delay","calculated delay"),path:findEntity(hass,"sensor",index,"path_delta","path difference")
 };
 const p=profile(index);return{index,output:`OUT ${letter(index)}`,color:COLORS[index%COLORS.length],speaker:p.speaker,role:p.role,ids,
  distance:num(hass,ids.distance),gain:num(hass,ids.gain),phase:num(hass,ids.phase),hpf:num(hass,ids.hpf,20),lpf:num(hass,ids.lpf,20000),
  polarity:text(hass,ids.polarity,"Normal"),hpfType:text(hass,ids.hpfType,"Linkwitz-Riley"),hpfSlope:text(hass,ids.hpfSlope,"24 dB/oct"),
  lpfType:text(hass,ids.lpfType,"Linkwitz-Riley"),lpfSlope:text(hass,ids.lpfSlope,"24 dB/oct"),delay:num(hass,ids.delay),path:num(hass,ids.path)};
}
export const formatHz=v=>v>=1000?`${Number.isInteger(v/1000)?v/1000:(v/1000).toFixed(1)} kHz`:`${Math.round(v)} Hz`;
export function carMap(channels,selected,compact=false){
 const pos=[[72,145],[248,145],[69,280],[251,280],[160,445]];
 return `<div class="car-map ${compact?"compact":""}"><svg viewBox="0 0 320 520"><defs><linearGradient id="body" x1="0" x2="1"><stop stop-color="#27333d"/><stop offset=".5" stop-color="#12191f"/><stop offset="1" stop-color="#27333d"/></linearGradient></defs>
 <rect x="92" y="34" width="136" height="438" rx="58" fill="url(#body)" stroke="#4a5965"/><path d="M112 92Q160 62 208 92L218 182Q160 166 102 182Z" fill="#0d1419" stroke="#35424c"/>
 <rect x="108" y="192" width="104" height="172" rx="24" fill="#0b1116" stroke="#35414b"/><rect x="116" y="206" width="38" height="62" rx="14" fill="#26323b"/><rect x="166" y="206" width="38" height="62" rx="14" fill="#26323b"/><rect x="116" y="290" width="38" height="58" rx="14" fill="#202a32"/><rect x="166" y="290" width="38" height="58" rx="14" fill="#202a32"/>
 ${channels.slice(0,5).map((c,i)=>`<g class="node ${selected===c.index?"selected":""}" data-action="channel" data-index="${c.index}"><circle cx="${pos[i][0]}" cy="${pos[i][1]}" r="10" fill="#091016" stroke="${c.color}" stroke-width="4"/><circle cx="${pos[i][0]}" cy="${pos[i][1]}" r="4" fill="${c.color}"/></g>`).join("")}</svg>
 ${channels.slice(0,5).map((c,i)=>`<button class="map-label l${i}" style="--ch:${c.color}" data-action="channel" data-index="${c.index}" data-open="channels"><b>${c.output}</b><span>${c.speaker}</span><small>${c.role}</small></button>`).join("")}</div>`;
}
