export const COLORS=["#348cff","#59a0ff","#63d66d","#ffb328","#b866ff","#43d8d8","#ff6b7a","#8ecbff","#a9db65","#ffc76b","#d38aff","#62e4b3"];
export const PROFILE=[
 {speaker:"BLAM FRS2N50 L",role:"Full-range",location:"Front left dash"},{speaker:"BLAM FRS2N50 R",role:"Full-range",location:"Front right dash"},
 {speaker:"BLAM 165 LSQ L",role:"Midbass",location:"Front left door"},{speaker:"BLAM 165 LSQ R",role:"Midbass",location:"Front right door"},
 {speaker:"BLAM SuperSub12",role:"Subwoofer",location:"Boot / trunk"}
];
export const FILTERS=["Butterworth","Linkwitz-Riley","Bessel"];
export const SLOPES=[6,12,18,24,30,36,42,48].map(v=>`${v} dB/oct`);
export const PRESETS=["Driver SQ","Front Both","Bass Mode","Tuning"];
export const ROLES=["Full-range","Tweeter","Midrange","Midbass","Woofer","Subwoofer","Center","Rear fill","DSP output"];
export const LOCATIONS=["Front left dash","Front right dash","Front left door","Front right door","Center dash","Rear left","Rear right","Boot / trunk","Under seat","Other"];
export const letter=i=>String.fromCharCode(65+i);
export const profile=i=>PROFILE[i]||{speaker:`OUT ${letter(i)}`,role:"DSP output",location:"Other"};
export const esc=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch]));
const token=(index,field)=>`${index}|${field}`;
const n=(value,fallback=0)=>{const v=Number(value);return Number.isFinite(v)?v:fallback};

export function channelData(raw,index){
 const p=profile(index),c=raw||{},ready=Boolean(raw);
 const ids={
  name:ready?token(index,"name"):null,speaker:ready?token(index,"speaker"):null,role:ready?token(index,"role"):null,location:ready?token(index,"location"):null,
  distance:ready?token(index,"distance_cm"):null,gain:ready?token(index,"gain_db"):null,phase:ready?token(index,"phase_deg"):null,fineDelay:ready?token(index,"fine_delay_ms"):null,
  hpf:ready?token(index,"hpf_hz"):null,lpf:ready?token(index,"lpf_hz"):null,polarity:ready?token(index,"polarity"):null,
  polarityVerified:ready?token(index,"polarity_verified"):null,alignmentVerified:ready?token(index,"alignment_verified"):null,
  hpfType:ready?token(index,"hpf_type"):null,hpfSlope:ready?token(index,"hpf_slope"):null,lpfType:ready?token(index,"lpf_type"):null,lpfSlope:ready?token(index,"lpf_slope"):null
 };
 return{index,output:String(c.output||`OUT ${letter(index)}`),name:String(c.name||`OUT ${letter(index)}`),color:COLORS[index%COLORS.length],speaker:String(c.speaker||p.speaker),role:String(c.role||p.role),location:String(c.location||p.location),ids,
  distance:n(c.distance_cm),gain:n(c.gain_db),phase:n(c.phase_deg),hpf:n(c.hpf_hz,20),lpf:n(c.lpf_hz,20000),fineDelay:n(c.fine_delay_ms),
  polarity:String(c.polarity||"Normal"),polarityVerified:Boolean(c.polarity_verified),alignmentVerified:Boolean(c.alignment_verified),
  hpfType:String(c.hpf_type||"Linkwitz-Riley"),hpfSlope:String(c.hpf_slope||"24 dB/oct"),lpfType:String(c.lpf_type||"Linkwitz-Riley"),lpfSlope:String(c.lpf_slope||"24 dB/oct"),
  delay:n(c.delay_ms),recommendedDelay:n(c.recommended_delay_ms,c.delay_ms),path:n(c.path_delta_cm)};
}
export const formatHz=v=>v>=1000?`${Number.isInteger(v/1000)?v/1000:(v/1000).toFixed(1)} kHz`:`${Math.round(v)} Hz`;
export function carMap(channels,selected,compact=false){
 const pos=[[72,145],[248,145],[69,280],[251,280],[160,445]];
 return `<div class="car-map ${compact?"compact":""}"><svg viewBox="0 0 320 520"><defs><linearGradient id="body" x1="0" x2="1"><stop stop-color="#27333d"/><stop offset=".5" stop-color="#12191f"/><stop offset="1" stop-color="#27333d"/></linearGradient></defs>
 <rect x="92" y="34" width="136" height="438" rx="58" fill="url(#body)" stroke="#4a5965"/><path d="M112 92Q160 62 208 92L218 182Q160 166 102 182Z" fill="#0d1419" stroke="#35424c"/>
 <rect x="108" y="192" width="104" height="172" rx="24" fill="#0b1116" stroke="#35414b"/><rect x="116" y="206" width="38" height="62" rx="14" fill="#26323b"/><rect x="166" y="206" width="38" height="62" rx="14" fill="#26323b"/><rect x="116" y="290" width="38" height="58" rx="14" fill="#202a32"/><rect x="166" y="290" width="38" height="58" rx="14" fill="#202a32"/>
 ${channels.slice(0,5).map((c,i)=>`<g class="node ${selected===c.index?"selected":""}" data-action="channel" data-index="${c.index}"><circle cx="${pos[i][0]}" cy="${pos[i][1]}" r="10" fill="#091016" stroke="${c.color}" stroke-width="4"/><circle cx="${pos[i][0]}" cy="${pos[i][1]}" r="4" fill="${c.color}"/></g>`).join("")}</svg>
 ${channels.slice(0,5).map((c,i)=>`<button class="map-label l${i}" style="--ch:${c.color}" data-action="channel" data-index="${c.index}" data-open="channels"><b>${esc(c.output)}</b><span>${esc(c.speaker)}</span><small>${esc(c.role)} · ${esc(c.location)}</small></button>`).join("")}</div>`;
}
