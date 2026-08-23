import"./kcc-soundlab-panel-0630.js?v=0.6.1";

const RESPONSE_TAG="kcc-measurement-response-0622";
const ResponseElement=customElements.get(RESPONSE_TAG);

if(ResponseElement&&!ResponseElement.prototype.__kccRepeatabilityStateInit0630){
 const proto=ResponseElement.prototype;
 proto.__kccRepeatabilityStateInit0630=true;
 const baseConnected=proto.connectedCallback;
 const baseLoad=proto.load;
 const resetState=function(){
  this.repeatabilityRepeats=[];
  this.repeatabilityMax=4;
  this.repeatabilityBusy=false;
  this.repeatabilityMessage="";
  this.repeatabilityError="";
 };
 proto.connectedCallback=function(...args){resetState.call(this);return baseConnected?.apply(this,args)};
 proto.load=async function(...args){
  this.repeatabilityRepeats=[];
  this.repeatabilityMessage="";
  this.repeatabilityError="";
  return baseLoad.apply(this,args);
 };
}
