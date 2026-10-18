/* MTDI demo replay: plays back what the real MTDI engine produced at build time on
   SIMULATED inputs, one state per second, through I³'s live bindings. */
(function(){
  var me=document.currentScript,url=me&&me.getAttribute('data-replay');
  if(!url||!window.I3)return;
  var sparks={},current=null;
  fetch(url).then(function(r){return r.json();}).then(function(data){
    var i=0,states=data.states||[];if(!states.length)return;
    function step(){
      if(i>=states.length){i=0;sparks={};}
      var s=states[i++];current=s;
      Object.keys(s.v).forEach(function(k){
        var v=s.v[k];
        if(v&&typeof v==='object'&&!Array.isArray(v))I3.set(k,v.value,v.state);else I3.set(k,v);
      });
      Object.keys(s.d).forEach(function(c){
        var a=sparks[c]||(sparks[c]=[]);a.push(s.d[c]);if(a.length>120)a.shift();
        I3.set('ch.'+c+'.spark',a.slice());
      });
    }
    step();setInterval(step,1000);
  });
  I3.ask=function(q){
    if(!current)return Promise.resolve('The replay is still loading.');
    var c=current.q;
    return Promise.resolve('Score '+c[2]+' %. '+c[0]+'. '+c[1]+
      ' (This website replays simulated data; run the studio for live answers.)');
  };
})();
