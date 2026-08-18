import{esc}from"./ui-utils.js?v=0.7.0";

export function subwooferView(app,ch){
 const sub=ch.find(c=>c.role==="Subwoofer")||ch[ch.length-1]||null;
 const mids=ch.filter(c=>c.role==="Midbass"||c.role==="Woofer");
 const refs=mids.length?mids:ch.filter(c=>c.index!==sub?.index).slice(0,2);
 const subLabel=sub?`${esc(sub.output)} · ${esc(sub.speaker||sub.name||"Subwoofer")}`:"No subwoofer channel configured";
 const refLabel=refs.length?refs.map(c=>`${esc(c.output)} · ${esc(c.speaker||c.name||c.role)}`).join(" + "):"No front reference configured";
 return`<section class="page"><div class="page-title"><div><small>SUBWOOFER ALIGNMENT</small><h2>Sub Alignment</h2><p>Step 1 · Layout test only. No tuning values are changed from this page yet.</p></div><span class="pill">STEP 1</span></div><div class="cards"><article class="card"><small>SUB OUTPUT</small><h3>${subLabel}</h3><p>Detected from the channel role in SoundLab.</p></article><article class="card"><small>FRONT REFERENCE</small><h3>${refLabel}</h3><p>Midbass/woofer channels are preferred for the later acoustic alignment workflow.</p></article></div><article class="card"><small>NEXT TEST</small><h3>Guided sub ↔ midbass alignment</h3><p>When this tab is confirmed stable, crossover timing, polarity and delay tools are added one small step at a time.</p></article></section>`;
}
