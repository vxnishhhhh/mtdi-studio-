/* ═══════════════════════════════════════════════════════════════════════════
   I³ INTERFACE FRAMEWORK · browser runtime
   Induction · Interference · Intelligence

   Extracted from the Inductra Vaion browser layer. Nothing here depends on Dash:
   every behaviour is attached to markup through data-i3-* attributes and re-armed
   whenever the routed page (#i3-page) changes, so the same file drives a Dash app,
   a static HTML page or any other host that renders the same markup.

   Configuration is read from window.I3_CONFIG (all optional):
     landUrl        URL of the Natural Earth land polygons for the globe
     stateUrl       JSON endpoint polled for live values ({key: value | {value, state}})
     statePollMs    poll interval, default 1500
     askUrl         POST endpoint for the NVTRA dock ({question} -> {answer})
     forceHomeOnLoad  start every full page load at "/" (Inductra behaviour)

   Public hooks on window.I3:
     I3.ask = async function(question){ return 'answer' }   replace to wire NVTRA
     I3.set(key, value, state)                              push a live value
     I3.rearm()                                             re-scan the page
   ═══════════════════════════════════════════════════════════════════════════ */
(function(){
  'use strict';

  var CFG=window.I3_CONFIG||{};
  var I3=window.I3=window.I3||{};
  var FRAME_INTERVAL=1000/144;

  // ── helpers ────────────────────────────────────────────────────────────────
  function attached(el){return !!(el&&el.isConnected);}
  function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
  function reduceMotion(){
    try{
      if(document.documentElement.classList.contains('i3-no-anim'))return true;
      return matchMedia('(prefers-reduced-motion: reduce)').matches;
    }catch(e){return false;}
  }
  function resetScroll(){
    try{scrollTo(0,0);}catch(e){}
    if(document.documentElement)document.documentElement.scrollTop=0;
    if(document.body)document.body.scrollTop=0;
  }
  function readJSON(el,attr,fallback){
    var raw=el&&el.getAttribute(attr);if(!raw)return fallback;
    try{return JSON.parse(raw);}catch(e){return fallback;}
  }
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  var PALETTE={
    oceanIn:'rgba(17,52,96,.95)',oceanOut:'rgba(4,10,24,.98)',
    limb:'rgba(140,224,255,.72)',grat:'rgba(96,178,235,.34)',
    land:'rgba(150,224,255,.66)',dot:'150,228,255',
    accent:'0,229,255',accent2:'41,121,255'
  };

  // Settings are restored before anything paints.
  try{if(localStorage.getItem('i3-anim')==='off')document.documentElement.classList.add('i3-no-anim');}catch(e){}

  // ══ PAGE SHADER — flowing field lines behind every page ══════════════════
  function bootPageShader(){
    if(document.getElementById('i3-page-shader')||reduceMotion())return;
    var canvas=document.createElement('canvas');canvas.id='i3-page-shader';
    document.body.insertBefore(canvas,document.body.firstChild);
    var gl=canvas.getContext('webgl',{powerPreference:'high-performance',antialias:false,alpha:false,depth:false,stencil:false})||canvas.getContext('experimental-webgl');
    if(!gl){canvas.remove();return;}
    var VS='attribute vec4 aPos;void main(){gl_Position=aPos;}';
    var FS=['precision highp float;','uniform vec2 iResolution; uniform float iTime;','const float S=0.045,sc=5.0;','const vec4 lc=vec4(0.08,0.25,1.0,1.0);',
      'float rnd(float t){return(cos(t)+cos(t*1.3+1.3)+cos(t*1.4+1.4))/3.0;}','float py(float x,float hf,float off){return rnd(x*0.2+iTime*S)*hf+off;}',
      '#define cr(p,hw,t) smoothstep(hw+0.015,hw,abs(p-(t)))','#define sm(p,hw,t) smoothstep(hw,0.0,abs(p-(t)))',
      'void main(){','  vec2 uv=gl_FragCoord.xy/iResolution.xy;','  vec2 sp=(gl_FragCoord.xy-iResolution.xy/2.0)/iResolution.x*2.0*sc;',
      '  float hf=1.0-(cos(uv.x*6.28)*0.5+0.5);','  float vf=1.0-(cos(uv.y*6.28)*0.5+0.5);',
      '  sp.y+=rnd(sp.x*0.5+iTime*S*0.2)*hf*1.5;','  sp.x+=rnd(sp.y*0.5+iTime*S*0.2+2.0)*hf;','  vec4 lines=vec4(0.0);',
      '  for(int l=0;l<16;l++){','    float nli=float(l)/16.0;float op=float(l)+sp.x*0.5;','    float rr=rnd(op+iTime*S*1.33)*0.5+0.5;',
      '    float hw=mix(0.01,0.18,rr*hf)/2.0;','    float off=rnd(op+iTime*S*1.33*(1.0+nli))*mix(0.6,2.0,hf);','    float lpos=py(sp.x,hf,off);',
      '    float ln=sm(lpos,hw,sp.y)/2.0+cr(lpos,hw*0.15,sp.y);','    float cx=mod(float(l)+iTime*S,25.0)-12.0;',
      '    float cd=length(sp-vec2(cx,py(cx,hf,off)));','    ln+=smoothstep(0.01+0.015,0.01,cd)*4.0;',
      '    lines+=ln*mix(lc,vec4(0.6,0.8,1.0,1.0),rr*0.25)*rr;','  }',
      '  vec4 col=mix(vec4(0.01,0.02,0.07,1.0),vec4(0.02,0.04,0.12,1.0),uv.x)*vf;','  col.a=1.0; col+=lines;','  gl_FragColor=col;}'].join('\n');
    function mk(src,type){var s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);return gl.getShaderParameter(s,gl.COMPILE_STATUS)?s:null;}
    var vs=mk(VS,gl.VERTEX_SHADER),fs=mk(FS,gl.FRAGMENT_SHADER);
    if(!vs||!fs){canvas.remove();return;}
    var prog=gl.createProgram();gl.attachShader(prog,vs);gl.attachShader(prog,fs);gl.linkProgram(prog);
    if(!gl.getProgramParameter(prog,gl.LINK_STATUS)){canvas.remove();return;}
    gl.useProgram(prog);
    var buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
    var pl=gl.getAttribLocation(prog,'aPos');gl.enableVertexAttribArray(pl);gl.vertexAttribPointer(pl,2,gl.FLOAT,false,0,0);
    var uT=gl.getUniformLocation(prog,'iTime'),uR=gl.getUniformLocation(prog,'iResolution');
    var t0=performance.now(),paused=false;
    document.addEventListener('visibilitychange',function(){paused=document.hidden;});
    // Resolution ladder: step down one rung when the GPU misses its frame budget for
    // two consecutive windows, step back up after 15 s of clean frames.
    var CAPS=[4096,3072,2048,1536,1152,864],capIndex=0,badWindows=0,cleanSince=0;
    var dpr=Math.min(devicePixelRatio||1,2);
    function resize(){
      var w=innerWidth*dpr,h=innerHeight*dpr,m=Math.max(w,h),cap=CAPS[capIndex];
      if(m>cap){var k=cap/m;w*=k;h*=k;}
      canvas.width=Math.max(2,Math.round(w));canvas.height=Math.max(2,Math.round(h));
      gl.viewport(0,0,canvas.width,canvas.height);
    }
    addEventListener('resize',resize,{passive:true});resize();
    var last=0,slow=0,drawn=0,fastest=1000/60;
    (function frame(ts){
      if(!attached(canvas))return;
      requestAnimationFrame(frame);
      if(paused||reduceMotion()){last=0;return;}
      if(ts&&ts-last<FRAME_INTERVAL-0.75)return;
      var gap=last?ts-last:0;last=ts||0;
      gl.uniform1f(uT,(performance.now()-t0)/1000);
      gl.uniform2f(uR,canvas.width,canvas.height);
      gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
      drawn++;
      if(drawn>30){
        if(gap>=FRAME_INTERVAL-0.75)fastest=Math.min(fastest,gap);
        if(gap>Math.max(FRAME_INTERVAL,fastest)*1.35+1&&gap<250)slow++;
        if(drawn%40===0){
          if(slow>16){badWindows++;cleanSince=0;}else{badWindows=0;if(slow<=2){if(!cleanSince)cleanSince=ts;}else cleanSince=0;}
          if(badWindows>=2&&capIndex<CAPS.length-1){capIndex++;resize();badWindows=0;cleanSince=0;}
          else if(cleanSince&&ts-cleanSince>15000&&capIndex>0){capIndex--;resize();cleanSince=0;}
          slow=0;
        }
      }
    })();
  }

  // ══ STARTUP INTRO — one boot per document load ═══════════════════════════
  function bootIntro(){
    var intro=document.getElementById('i3-intro');
    if(!intro||intro.dataset.booted==='1')return !!intro;
    intro.dataset.booted='1';
    var finishNow=function(){
      intro.remove();document.body.classList.remove('i3-intro-active');
      document.body.style.removeProperty('--i3-intro-home-y');resetScroll();window.__i3IntroDone=true;
    };
    if(reduceMotion()||getComputedStyle(intro).display==='none'){finishNow();return true;}
    var stage=intro.querySelector('.i3-intro-stage'),card=intro.querySelector('.i3-intro-card'),
        eyebrow=intro.querySelector('.i3-intro-eyebrow'),top=intro.querySelector('.i3-intro-top'),
        bottom=intro.querySelector('.i3-intro-bottom'),canvas=document.getElementById('i3-intro-shader');
    if(!stage||!card||!eyebrow||!top||!bottom||!canvas){finishNow();return true;}
    document.body.classList.add('i3-intro-active');
    document.body.style.setProperty('--i3-intro-home-y','100vh');
    intro.scrollTop=0;
    var stopShader=introShader(canvas);
    var target=0,current=-1,raf=0,lastTs=0,range=1,alive=true;
    var ease=function(v){return 1-Math.pow(1-v,2);};
    function measure(){range=Math.max(1,intro.scrollHeight-intro.clientHeight);update();}
    function update(){
      target=clamp(intro.scrollTop/range,0,1);
      if(target>=0.985){consume();return;}
      if(!raf)raf=requestAnimationFrame(frame);
    }
    function consume(){
      if(intro.dataset.consuming==='1')return;
      intro.dataset.consuming='1';target=1;cleanup();intro.style.pointerEvents='none';
      var start=current<0?0:clamp(current,0,1),started=performance.now();
      var duration=Math.max(180,Math.min(420,(1-start)*420));
      (function finish(now){
        if(!attached(intro))return;
        var t=clamp((now-started)/duration,0,1),e=1-Math.pow(1-t,3);
        paint(start+(1-start)*e);
        if(t<1){requestAnimationFrame(finish);return;}
        document.body.classList.remove('i3-intro-active');
        document.body.style.removeProperty('--i3-intro-home-y');
        intro.remove();window.__i3IntroDone=true;
      })(performance.now());
    }
    // The titles clear first, the card holds, then it enlarges and fades while the
    // already-mounted shell rises from below at the same rate.
    function paint(p){
      var enter=clamp(p/0.385,0,1),enterE=ease(enter),exit=clamp((p-0.615)/0.385,0,1);
      var shaderExit=ease(clamp((p-0.48)/0.24,0,1)),handoff=clamp((p-0.72)/0.28,0,1);
      card.style.transform='translate3d(0,0,0) scale('+(0.65+0.70*enterE+0.20*exit).toFixed(4)+')';
      card.style.opacity=Math.max(0.16,1-exit).toFixed(4);
      card.style.filter='blur('+(16*(1-enterE)).toFixed(3)+'px) brightness('+(0.42+1.18*enterE).toFixed(3)+')';
      eyebrow.style.transform='translate3d(0,'+(-500*enter).toFixed(2)+'px,0)';eyebrow.style.opacity=(1-enter).toFixed(4);
      top.style.transform='translate3d('+(-130*enter).toFixed(3)+'%,0,0)';top.style.opacity=(1-enter).toFixed(4);
      bottom.style.transform='translate3d('+(130*enter).toFixed(3)+'%,0,0)';bottom.style.opacity=(1-enter).toFixed(4);
      canvas.style.opacity=(.38*(1-shaderExit)).toFixed(4);
      stage.style.transform='translate3d(0,'+(-100*handoff).toFixed(4)+'%,0)';
      document.body.style.setProperty('--i3-intro-home-y',((1-handoff)*100).toFixed(4)+'vh');
    }
    function frame(ts){
      raf=0;if(!alive||!attached(intro))return;
      if(current<0)current=target;
      var dt=lastTs?Math.min((ts-lastTs)/1000,0.05):0.016;lastTs=ts;
      current+=(target-current)*(1-Math.exp(-dt/0.16));
      if(Math.abs(target-current)<0.00015)current=target;
      paint(current);
      if(current!==target)raf=requestAnimationFrame(frame);
    }
    function cleanup(){alive=false;if(raf)cancelAnimationFrame(raf);intro.removeEventListener('scroll',update);removeEventListener('resize',measure);stopShader();}
    var skip=intro.querySelector('[data-i3-intro-skip]');
    if(skip)skip.addEventListener('click',function(){intro.scrollTop=intro.scrollHeight;consume();});
    intro.addEventListener('scroll',update,{passive:true});
    addEventListener('resize',measure,{passive:true});
    measure();paint(0);
    return true;
  }
  function introShader(canvas){
    var gl=canvas.getContext('webgl',{alpha:false,antialias:true,depth:false,stencil:false,powerPreference:'high-performance'})||canvas.getContext('experimental-webgl');
    if(!gl)return function(){};
    var fs=['precision highp float;','uniform vec2 u_res;','uniform float u_time;','void main(){',
      'vec2 uv=(gl_FragCoord.xy*2.0-u_res)/min(u_res.x,u_res.y);','float t=u_time*0.04;','float lw=0.0025;','vec3 col=vec3(0.0);',
      'for(int j=0;j<3;j++){','for(int i=0;i<5;i++){','float fi=float(i);','float fj=float(j);',
      'col[j]+=lw*fi*fi/abs(fract(t-0.012*fj+fi*0.012)*5.0-length(uv)+mod(uv.x+uv.y,0.22));','}}',
      'float total=col.r+col.g+col.b;','col=vec3(total*0.14,total*0.42,total*0.95);','gl_FragColor=vec4(col,1.0);','}'].join('\n');
    function compile(type,src){var s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);return s;}
    var prog=gl.createProgram();
    gl.attachShader(prog,compile(gl.VERTEX_SHADER,'attribute vec2 a_pos;void main(){gl_Position=vec4(a_pos,0.0,1.0);}'));
    gl.attachShader(prog,compile(gl.FRAGMENT_SHADER,fs));gl.linkProgram(prog);gl.useProgram(prog);
    var buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
    var pos=gl.getAttribLocation(prog,'a_pos');gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);
    var uRes=gl.getUniformLocation(prog,'u_res'),uTime=gl.getUniformLocation(prog,'u_time');
    var af,time=0,lastFrame=0,stopped=false;
    function resize(){
      var w=Math.max(1,innerWidth),h=Math.max(1,innerHeight),scale=Math.min(devicePixelRatio||1,1.75);
      if(w*h*scale*scale>2200000)scale=Math.sqrt(2200000/(w*h));
      canvas.width=Math.round(w*scale);canvas.height=Math.round(h*scale);
      gl.viewport(0,0,canvas.width,canvas.height);gl.uniform2f(uRes,canvas.width,canvas.height);
    }
    function draw(now){
      if(stopped)return;af=requestAnimationFrame(draw);
      if(!lastFrame)lastFrame=now;
      var d=Math.min((now-lastFrame)/1000,0.05);lastFrame=now;
      time=Math.min(20,time+d*7.2);gl.uniform1f(uTime,time);gl.drawArrays(gl.TRIANGLES,0,6);
      if(time>=20)stopped=true;   // one complete pass, then hold the last frame
    }
    resize();addEventListener('resize',resize,{passive:true});af=requestAnimationFrame(draw);
    return function(){stopped=true;cancelAnimationFrame(af);removeEventListener('resize',resize);};
  }

  // ══ SCRUB OPENINGS — scroll-locked page openings ═════════════════════════
  // While an opening owns the screen the body is pinned and wheel, touch and key
  // input is spent on the opening's progress. Once it ends and the reader keeps
  // pushing, the page is handed back. Each opening plays once per page load.
  var scrub={hero:null,locked:false,lockedY:0,target:0,shown:0,moved:false,raf:0,painter:null,el:{}};
  var SCRUB_DISTANCE=3200,HOLD_DISTANCE=1100,seenOpenings={};
  function scrubActive(){return !!scrub.hero&&scrub.hero.isConnected&&!scrub.hero.classList.contains('is-hidden');}
  function scrubLock(){
    if(scrub.locked)return;scrub.locked=true;scrub.lockedY=scrollY;
    var b=document.body.style;b.position='fixed';b.top='-'+scrub.lockedY+'px';b.left='0';b.right='0';b.width='100%';b.minHeight='100vh';
  }
  function scrubRelease(settle){
    if(!scrub.locked)return;scrub.locked=false;
    var b=document.body.style;b.position='';b.top='';b.left='';b.right='';b.width='';b.minHeight='';
    scrollTo(0,scrub.lockedY);
    if(settle&&scrub.hero){scrub.hero.classList.add('is-hidden');cancelAnimationFrame(scrub.raf);resetScroll();}
  }
  function scrubConsume(dy){
    if(!scrub.locked)return false;
    if(scrub.target>=1&&scrub.shown>.98&&dy>0){scrubRelease(true);return true;}
    scrub.target=clamp(scrub.target+dy/(SCRUB_DISTANCE+HOLD_DISTANCE),0,1);
    if(scrub.target>.001)scrub.moved=true;
    return true;
  }
  function scrubPaint(p){
    var share=SCRUB_DISTANCE/(SCRUB_DISTANCE+HOLD_DISTANCE),v=clamp(p/share,0,1),e=scrub.el;
    if(scrub.painter)scrub.painter(v,p);
    var titleA=1-clamp(v/.35,0,1),tagA=clamp((v-.82)/.18,0,1);
    if(e.scrim)e.scrim.style.opacity=String(Math.max(titleA,tagA));
    if(e.title){e.title.style.opacity=String(titleA);e.title.style.transform='translateY('+((1-titleA)*-24).toFixed(1)+'px)';}
    if(e.tag){e.tag.style.opacity=String(tagA);e.tag.style.transform='translateY('+((1-tagA)*20).toFixed(1)+'px)';}
    if(e.hint)e.hint.style.opacity=scrub.moved?'0':'1';
    if(e.bar)e.bar.style.transform='scaleX('+p.toFixed(4)+')';
  }
  function scrubFrame(now){
    if(!scrubActive()){scrub.raf=0;return;}
    var dt=scrub.lastFrame?Math.min(50,now-scrub.lastFrame):1000/60;scrub.lastFrame=now;
    var prev=scrub.shown;
    scrub.shown+=(scrub.target-scrub.shown)*(1-Math.pow(.82,dt/(1000/60)));
    if(Math.abs(scrub.target-scrub.shown)<.00001)scrub.shown=scrub.target;
    if(scrub.shown!==prev||!scrub.painted){scrubPaint(scrub.shown);scrub.painted=true;}
    if(scrub.locked&&scrub.target>=1&&scrub.shown>.985){scrubRelease(true);return;}
    scrub.raf=requestAnimationFrame(scrubFrame);
  }
  var SCRUB_KEYS={ArrowDown:140,ArrowUp:-140,PageDown:700,PageUp:-700,' ':700,End:1e9,Home:-1e9};
  addEventListener('wheel',function(e){if(scrubActive()&&scrubConsume(e.deltaY))e.preventDefault();},{passive:false});
  var touchY=0;
  addEventListener('touchstart',function(e){touchY=e.touches[0]?e.touches[0].clientY:0;},{passive:true});
  addEventListener('touchmove',function(e){if(!scrubActive())return;var y=e.touches[0]?e.touches[0].clientY:touchY,d=touchY-y;touchY=y;if(scrubConsume(d))e.preventDefault();},{passive:false});
  addEventListener('keydown',function(e){
    if(!scrubActive()||(e.target.matches&&e.target.matches('input,textarea,select')))return;
    if(e.key==='Escape'&&scrub.locked){scrubSkip();return;}
    var step=SCRUB_KEYS[e.key];if(step===undefined)return;
    if(scrubConsume(step))e.preventDefault();
  });
  function scrubSkip(){scrub.target=scrub.shown=1;scrub.moved=true;scrubPaint(1);scrubRelease(true);}
  function scrubTeardown(){
    if(scrub.locked)scrubRelease();cancelAnimationFrame(scrub.raf);scrub.raf=0;
    if(scrub.hero)scrub.hero.querySelectorAll('.i3-scrub-stage,.i3-scrub-skip,.i3-scrub-rail').forEach(function(n){n.remove();});
    scrub.hero=null;scrub.painter=null;scrub.el={};
  }
  function scrubMount(hero){
    scrubTeardown();
    var kind=hero.getAttribute('data-i3-scrub');seenOpenings[kind+'|'+location.pathname]=true;
    scrub.hero=hero;scrub.lastFrame=0;scrub.painted=false;scrub.target=scrub.shown=0;scrub.moved=false;
    var stage=document.createElement('div');stage.className='i3-scrub-stage';hero.appendChild(stage);
    var c=document.createElement('canvas');c.className='i3-scrub-canvas';stage.appendChild(c);
    var scrim=document.createElement('div');scrim.className='i3-scrub-scrim';stage.appendChild(scrim);
    var titleText=hero.getAttribute('data-i3-title')||'',tagText=hero.getAttribute('data-i3-tagline')||'';
    var title=document.createElement('div');title.className='i3-scrub-title'+(titleText.length>40?' is-long':'');
    title.innerHTML='<h1>'+esc(titleText)+'</h1>';stage.appendChild(title);
    var tag=document.createElement('div');tag.className='i3-scrub-tag';tag.innerHTML='<p>'+esc(tagText)+'</p>';stage.appendChild(tag);
    var hint=document.createElement('div');hint.className='i3-scrub-hint';
    hint.innerHTML='<span>SCROLL</span><svg width="14" height="18" viewBox="0 0 14 18" aria-hidden="true"><path d="M7 1 L7 17 M2 12 L7 17 L12 12" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    stage.appendChild(hint);
    var skip=document.createElement('button');skip.type='button';skip.className='i3-scrub-skip';skip.textContent='Skip';
    skip.addEventListener('click',scrubSkip);hero.appendChild(skip);
    var rail=document.createElement('div');rail.className='i3-scrub-rail';var bar=document.createElement('div');bar.className='i3-scrub-bar';
    rail.appendChild(bar);hero.appendChild(rail);
    scrub.el={canvas:c,scrim:scrim,title:title,tag:tag,hint:hint,bar:bar,stage:stage};
    var painters={field:fieldPainter,flow:flowPainter};
    scrub.painter=(painters[kind]||fieldPainter)(c,hero);
    if(reduceMotion()){hero.classList.add('is-hidden');return;}
    var mountedAt=performance.now();
    (function tryLock(){
      if(scrub.hero!==hero||!hero.isConnected)return;
      if(document.getElementById('i3-intro')){setTimeout(tryLock,300);return;}
      if(scrollY>hero.offsetTop+1&&performance.now()-mountedAt<1500)scrollTo(0,hero.offsetTop);
      if(scrollY<=hero.offsetTop+1)scrubLock();
      else{scrub.target=scrub.shown=1;scrub.moved=true;scrubPaint(1);}
    })();
    scrub.raf=requestAnimationFrame(scrubFrame);
  }
  // React reuses the opening's node when the route changes, re-labelling it in
  // place, so an opening is identified by kind + route, never by DOM node.
  function scrubKey(hero){return hero.getAttribute('data-i3-scrub')+'|'+location.pathname;}
  function armScrub(){
    var hero=document.querySelector('#i3-page [data-i3-scrub]');
    if(scrub.hero&&(!hero||hero!==scrub.hero||scrub.key!==scrubKey(hero)))scrubTeardown();
    if(!hero||scrub.hero===hero)return;
    if(seenOpenings[scrubKey(hero)]){
      hero.classList.add('is-hidden');
      hero.querySelectorAll('.i3-scrub-stage,.i3-scrub-skip,.i3-scrub-rail').forEach(function(n){n.remove();});
      return;
    }
    hero.classList.remove('is-hidden');
    scrubMount(hero);scrub.key=scrubKey(hero);
  }
  // True when an element armed earlier still belongs to the page now showing.
  // React can hand a node from one route to the next, so attachment alone is not enough.
  function stillArmed(el,parts,kind){
    if(el.__i3path!==location.pathname||(kind&&el.__i3kind!==kind))return false;
    return !parts||parts.every(function(p){return p.isConnected&&el.contains(p);});
  }
  // Take ownership of a node for this route; any loop or handler from an earlier
  // owner sees the generation change and stands down.
  function claim(el,kind){el.__i3path=location.pathname;el.__i3kind=kind;return el.__i3gen=(el.__i3gen||0)+1;}
  function scrubSize(c){
    var r=c.parentElement.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,2);
    var w=Math.max(1,Math.round(r.width*ratio)),h=Math.max(1,Math.round(r.height*ratio));
    if(c.width!==w||c.height!==h){c.width=w;c.height=h;}
    return {w:r.width,h:r.height,ratio:ratio};
  }
  var smooth=function(x){return x<=0?0:x>=1?1:x*x*(3-2*x);};

  // A data-driven signal path: boxes appear in order and links trace between them.
  // Spec (data-i3-flow): {nodes:[{x,y,w,title,copy,core}], links:[[from,to]], footnote}
  function flowPainter(c,hero){
    var spec=readJSON(hero,'data-i3-flow',{nodes:[],links:[]});
    var nodes=spec.nodes||[],links=spec.links||[],foot=spec.footnote||'';
    var ys=nodes.map(function(n){return n.y;}).filter(function(v,i,a){return a.indexOf(v)===i;}).sort();
    nodes.forEach(function(n){if(n.at==null){var row=ys.indexOf(n.y);n.at=Math.min(.9,.02+row*.24+(nodes.filter(function(m){return m.y===n.y&&m.x<n.x;}).length)*.05);}});
    return function(v){
      var s=scrubSize(c),w=s.w,h=s.h,ctx=c.getContext('2d');if(!(w>0&&h>0))return;
      ctx.setTransform(s.ratio,0,0,s.ratio,0,0);ctx.clearRect(0,0,w,h);
      var compact=w<650,top=compact?h*.13:h*.08,usable=h*(compact?.78:.84),boxH=Math.min(compact?62:76,h*.1);ctx.lineCap='round';
      function pos(n){return {x:n.x*w,y:top+n.y*usable};}
      links.forEach(function(link,i){
        var a=nodes[link[0]],b=nodes[link[1]];if(!a||!b)return;
        var pa=pos(a),pb=pos(b),q=smooth((v-(.18+i*.045))/.22);if(q<=0)return;
        var sy=pa.y+boxH/2,ey=pb.y-boxH/2,mid=(sy+ey)/2;
        ctx.strokeStyle='rgba(86,208,236,'+(.22+.65*q)+')';ctx.lineWidth=1.2;ctx.beginPath();
        ctx.moveTo(pa.x,sy);ctx.lineTo(pa.x,mid);ctx.lineTo(pb.x,mid);ctx.lineTo(pb.x+(pa.x-pb.x)*(1-q),ey+(mid-ey)*(1-q));ctx.stroke();
        if(q>.92){ctx.fillStyle='#8ff5ff';ctx.beginPath();ctx.arc(pb.x,ey,2.2,0,7);ctx.fill();}
      });
      nodes.forEach(function(n){
        var a=smooth((v-n.at)/.18);if(a<=0)return;
        var p=pos(n),bw=Math.min((n.w||.3)*w,compact?w*.42:360),bh=boxH;
        ctx.save();ctx.globalAlpha=a;ctx.translate(0,(1-a)*18);
        ctx.fillStyle=n.core?'rgba(17,64,88,.94)':'rgba(10,28,48,.90)';
        ctx.strokeStyle=n.core?'rgba(75,230,241,.94)':'rgba(106,178,230,.64)';ctx.lineWidth=n.core?1.7:1;
        ctx.beginPath();if(ctx.roundRect)ctx.roundRect(p.x-bw/2,p.y-bh/2,bw,bh,10);else ctx.rect(p.x-bw/2,p.y-bh/2,bw,bh);
        ctx.fill();ctx.stroke();
        if(n.core){ctx.shadowColor='rgba(49,215,230,.45)';ctx.shadowBlur=24;ctx.stroke();ctx.shadowBlur=0;}
        ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#eaf7ff';
        ctx.font='700 '+(compact?9:12)+'px DM Mono,monospace';ctx.fillText(String(n.title||'').toUpperCase(),p.x,p.y-9);
        ctx.fillStyle='rgba(178,205,224,.82)';ctx.font=(compact?7:9)+'px DM Mono,monospace';ctx.fillText(String(n.copy||'').toUpperCase(),p.x,p.y+11);
        ctx.restore();
      });
      if(foot){ctx.textAlign='center';ctx.fillStyle='rgba(150,189,211,'+smooth((v-.86)/.12)+')';
        ctx.font='italic '+(compact?8:10)+'px DM Mono,monospace';ctx.fillText(String(foot).toUpperCase(),w/2,h*.965);}
    };
  }
  // Magnetosphere: a shaded Earth with dipole field lines that trace in as the
  // scene scrubs. Decorative; nothing here is measured.
  function fieldPainter(c){
    return function(v){
      var s=scrubSize(c),w=s.w,h=s.h,ctx=c.getContext('2d');if(!(w>0&&h>0))return;
      ctx.setTransform(s.ratio,0,0,s.ratio,0,0);ctx.clearRect(0,0,w,h);
      var R=Math.min(w,h)*(.40+v*.12),cx=w*.5,cy=h*(1.08-v*.30);
      var glow=ctx.createRadialGradient(cx,cy,R*.92,cx,cy,R*1.42);
      glow.addColorStop(0,'rgba(49,215,230,.30)');glow.addColorStop(.45,'rgba(41,121,255,.10)');glow.addColorStop(1,'rgba(41,121,255,0)');
      ctx.fillStyle=glow;ctx.beginPath();ctx.arc(cx,cy,R*1.42,0,7);ctx.fill();
      var body=ctx.createRadialGradient(cx-R*.42,cy-R*.46,R*.05,cx,cy,R*1.02);
      body.addColorStop(0,'#3d8fe8');body.addColorStop(.35,'#1b57b8');body.addColorStop(.72,'#0b2a66');body.addColorStop(1,'#030b1e');
      ctx.fillStyle=body;ctx.beginPath();ctx.arc(cx,cy,R,0,7);ctx.fill();
      ctx.save();ctx.beginPath();ctx.arc(cx,cy,R,0,7);ctx.clip();
      ctx.save();ctx.translate(cx,cy);ctx.rotate(-.40);ctx.lineWidth=1;
      for(var i=1;i<6;i++){var y=R*Math.sin((i-3)*Math.PI/6.5),rx=Math.sqrt(Math.max(0,R*R-y*y));
        ctx.strokeStyle='rgba(160,220,255,'+(i===3?.22:.12)+')';ctx.beginPath();ctx.ellipse(0,y,rx,rx*.16,0,0,7);ctx.stroke();}
      for(var m=0;m<7;m++){var a=m*Math.PI/7+v*.9,mx=Math.abs(Math.cos(a))*R;
        ctx.strokeStyle='rgba(160,220,255,'+(.08+.10*Math.abs(Math.sin(a)))+')';ctx.beginPath();ctx.ellipse(0,0,Math.max(.6,mx),R,0,0,7);ctx.stroke();}
      ctx.restore();
      var night=ctx.createLinearGradient(cx-R*.2,cy-R*.6,cx+R*.9,cy+R*.6);
      night.addColorStop(0,'rgba(2,8,24,0)');night.addColorStop(.55,'rgba(2,8,24,.35)');night.addColorStop(1,'rgba(2,8,24,.92)');
      ctx.fillStyle=night;ctx.fillRect(cx-R,cy-R,2*R,2*R);
      var spec=ctx.createRadialGradient(cx-R*.5,cy-R*.52,0,cx-R*.5,cy-R*.52,R*.5);
      spec.addColorStop(0,'rgba(230,250,255,.28)');spec.addColorStop(1,'rgba(230,250,255,0)');
      ctx.fillStyle=spec;ctx.fillRect(cx-R,cy-R,2*R,2*R);
      ctx.restore();
      var rim=ctx.createLinearGradient(cx-R,cy-R,cx+R,cy+R);
      rim.addColorStop(0,'rgba(140,235,255,.85)');rim.addColorStop(.6,'rgba(49,215,230,.35)');rim.addColorStop(1,'rgba(49,215,230,.08)');
      ctx.strokeStyle=rim;ctx.lineWidth=Math.max(1.2,R*.012);ctx.beginPath();ctx.arc(cx,cy,Math.max(0,R-ctx.lineWidth*.5),0,7);ctx.stroke();
      for(var k=0;k<7;k++){
        var L=R*(1.22+k*.30),frac=clamp(v*1.35-k*.05,0,1);if(frac<=0)continue;
        [1,-1].forEach(function(side){
          ctx.beginPath();var steps=110,started=false;
          for(var j=0;j<=steps*frac;j++){
            var lat=-Math.PI/2+Math.PI*j/steps,r=L*Math.cos(lat)*Math.cos(lat);
            if(r<R*.99){started=false;continue;}
            var x=cx+side*r*Math.cos(lat),yy=cy-r*Math.sin(lat);
            if(!started){ctx.moveTo(x,yy);started=true;}else ctx.lineTo(x,yy);
          }
          ctx.lineWidth=1.6-k*.14;ctx.strokeStyle='rgba(49,215,230,'+(.55-k*.065).toFixed(2)+')';ctx.stroke();
        });
        if(k<3){for(var q=0;q<4;q++){var u=((v*1.2+q/4+k*.13)%1),lt=-Math.PI/2+Math.PI*u,rr=L*Math.cos(lt)*Math.cos(lt);
          if(rr<R*1.02)continue;
          [1,-1].forEach(function(side){ctx.fillStyle='rgba(200,245,255,'+(.7*frac).toFixed(2)+')';ctx.beginPath();
            ctx.arc(cx+side*rr*Math.cos(lt),cy-rr*Math.sin(lt),1.6,0,7);ctx.fill();});}}
      }
      var sweep=ctx.createLinearGradient(0,0,w,0);
      sweep.addColorStop(clamp(v-.1,0,1),'rgba(0,0,0,0)');sweep.addColorStop(clamp(v,0,1),'rgba(49,215,230,.10)');sweep.addColorStop(clamp(v+.1,0,1),'rgba(0,0,0,0)');
      ctx.fillStyle=sweep;ctx.fillRect(0,0,w,h);
    };
  }

  // ══ ORBIT — cards revolving at one constant speed round a core ═══════════
  // Solves for a radius that keeps every card inside the scene AND clear of the
  // core, shrinking cards up to 42 % before conceding. null means no overlap-free
  // orbit exists and the scene falls back to a plain grid.
  function orbitFit(o){
    var GAP=16,vw=Math.max(240,Math.min(o.sceneW||innerWidth,innerWidth)),vh=Math.max(240,o.sceneH||480);
    for(var s=1;s>=0.58;s-=0.06){
      var halfW=o.cardW*s/2,halfH=o.cardH*s/2;
      var maxR=Math.min(vw/2-halfW-GAP,vh/2-halfH-GAP),minR=o.coreR+halfH+GAP;
      if(maxR>=minR)return {r:Math.max(minR,Math.min(maxR,o.ideal)),scale:s};
    }
    return null;
  }
  function armOrbits(){
    document.querySelectorAll('#i3-page .i3-orbit[data-i3-orbit]').forEach(function(scene){
      if(scene.__i3parts&&stillArmed(scene,scene.__i3parts))return;
      var cards=[].slice.call(scene.querySelectorAll(':scope > .i3-orbit-card'));
      var ring=scene.querySelector('.i3-orbit-ring'),core=scene.querySelector('.i3-orbit-core');
      if(!cards.length||!ring)return;
      // A reused node may still carry the previous route's state.
      scene.classList.remove('is-linear');
      cards.forEach(function(c){c.classList.remove('is-detached','is-expanded','is-closing');});
      var gen=scene.__i3gen=(scene.__i3gen||0)+1;
      scene.__i3path=location.pathname;scene.__i3parts=cards.concat([ring]);
      var expandable=scene.getAttribute('data-i3-orbit')==='pillars';
      var angle=-Math.PI/2,last=performance.now(),lastPaint=0,linear=null,scale=1;
      var active=null,transitioning=false,returnRect=null;
      function geometry(){
        var coreBox=core?Math.max(core.offsetWidth,core.offsetHeight):102;
        var fit=orbitFit({sceneW:scene.clientWidth||innerWidth,sceneH:scene.clientHeight||940,
          cardW:300,cardH:200,coreR:coreBox/2,ideal:360});
        if(!fit)return null;
        scale=fit.scale;ring.style.setProperty('--orbit-diameter',(fit.r*2)+'px');
        return fit.r;
      }
      function setLinear(on){
        if(linear===on)return;linear=on;scene.classList.toggle('is-linear',on);
        if(on)cards.forEach(function(c){c.style.transform='';c.style.zIndex='';c.style.opacity='';});
      }
      function paint(){
        if(active||transitioning||!attached(scene))return;
        if(innerWidth<=760){setLinear(true);return;}
        setLinear(false);
        var radius=geometry();if(radius===null){setLinear(true);return;}
        cards.forEach(function(card,i){
          var theta=angle+i*(Math.PI*2/cards.length),x=Math.cos(theta)*radius,y=Math.sin(theta)*radius,depth=(Math.sin(theta)+1)/2;
          card.style.transform='translate3d('+x.toFixed(2)+'px,'+y.toFixed(2)+'px,0) scale('+scale.toFixed(3)+')';
          card.style.zIndex=String(Math.round(10+depth*20));
          card.style.opacity=String(.80+depth*.20);
        });
      }
      function afterTransition(card,fn){
        var done=false;
        function finish(){if(done)return;done=true;card.removeEventListener('transitionend',ended);fn();}
        function ended(e){if(e.target===card&&e.propertyName==='width')finish();}
        card.addEventListener('transitionend',ended);setTimeout(finish,reduceMotion()?30:840);
      }
      function openCard(card){
        if(!card||transitioning||active)return;
        transitioning=true;returnRect=card.getBoundingClientRect();
        document.body.classList.add('i3-pillar-open');
        card.classList.add('is-detached');
        card.style.left=returnRect.left+'px';card.style.top=returnRect.top+'px';
        card.style.width=returnRect.width+'px';card.style.height=returnRect.height+'px';
        card.getBoundingClientRect();
        requestAnimationFrame(function(){requestAnimationFrame(function(){
          card.style.left='0px';card.style.top='0px';card.style.width='100vw';card.style.height='100dvh';card.style.borderRadius='0px';
        });});
        afterTransition(card,function(){
          if(!attached(card))return;
          card.classList.add('is-expanded');card.scrollTop=0;active=card;transitioning=false;
          var close=card.querySelector('.i3-pillar-close');if(close)try{close.focus({preventScroll:true});}catch(e){}
        });
      }
      function closeCard(card){
        if(!card||transitioning||active!==card)return;
        transitioning=true;card.classList.add('is-closing');
        setTimeout(function(){
          if(!attached(card))return;
          card.classList.remove('is-expanded','is-closing');card.scrollTop=0;
          card.style.left=returnRect.left+'px';card.style.top=returnRect.top+'px';
          card.style.width=returnRect.width+'px';card.style.height=returnRect.height+'px';card.style.borderRadius='12px';
          afterTransition(card,function(){
            card.classList.remove('is-detached');
            ['left','top','width','height','border-radius'].forEach(function(n){card.style.removeProperty(n);});
            document.body.classList.remove('i3-pillar-open');
            active=null;transitioning=false;last=performance.now();paint();
            try{card.focus({preventScroll:true});}catch(e){}
          });
        },reduceMotion()?0:190);
      }
      if(expandable){
        scene.addEventListener('click',function(e){
          if(scene.__i3gen!==gen)return;   // a handler from an earlier arm of a reused node
          var close=e.target.closest('.i3-pillar-close');
          if(close){e.preventDefault();e.stopPropagation();closeCard(close.closest('.i3-orbit-card'));return;}
          var card=e.target.closest('.i3-orbit-card');
          if(card&&!card.classList.contains('is-detached'))openCard(card);
        });
        scene.addEventListener('keydown',function(e){
          if(scene.__i3gen!==gen)return;
          var card=e.target.closest('.i3-orbit-card');
          if(card&&!card.classList.contains('is-detached')&&(e.key==='Enter'||e.key===' ')){e.preventDefault();openCard(card);}
        });
        var onEsc=function(e){if(e.key==='Escape'&&active&&!transitioning)closeCard(active);};
        document.addEventListener('keydown',onEsc);
      }
      addEventListener('resize',paint,{passive:true});
      paint();
      (function tick(now){
        if(!attached(scene)||scene.__i3gen!==gen||!stillArmed(scene,scene.__i3parts)){
          removeEventListener('resize',paint);if(onEsc)document.removeEventListener('keydown',onEsc);
          if(scene.__i3gen===gen)scene.__i3parts=null;   // let the next arm() take it
          document.body.classList.remove('i3-pillar-open');return;
        }
        requestAnimationFrame(tick);
        if(document.hidden||active||transitioning||reduceMotion()){last=now;return;}
        if(now-lastPaint<FRAME_INTERVAL-0.75)return;
        var dt=Math.min(64,now-last);last=now;lastPaint=now;
        angle=(angle+dt*.000075)%(Math.PI*2);paint();
      })(performance.now());
    });
  }

  // ══ GLOBE — dotted Earth with selectable nodes and exterior link arcs ═══
  // canvas[data-i3-globe] reads its nodes from data-i3-nodes:
  //   [{name, lon, lat, summary}]  and links from data-i3-links: [[a,b], ...]
  var landCache=null,landWaiters=[];
  function loadLand(cb){
    if(landCache){cb(landCache);return;}
    landWaiters.push(cb);if(landWaiters.length>1||!CFG.landUrl)return;
    fetch(CFG.landUrl,{cache:'force-cache'}).then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(data){
      var polys=[];
      if(Array.isArray(data))polys=data;
      else (data.features||[]).forEach(function(f){var g=f&&f.geometry;if(!g)return;
        if(g.type==='Polygon'&&g.coordinates[0])polys.push(g.coordinates[0]);
        else if(g.type==='MultiPolygon')g.coordinates.forEach(function(p){if(p[0])polys.push(p[0]);});});
      landCache={polygons:polys,points:buildDots(polys)};
      landWaiters.splice(0).forEach(function(fn){fn(landCache);});
    }).catch(function(){landWaiters=[];});   // graticule-only globe stays usable
  }
  function pointInPolygon(lon,lat,poly){
    var inside=false;
    for(var i=0,j=poly.length-1;i<poly.length;j=i++){
      var xi=poly[i][0],yi=poly[i][1],xj=poly[j][0],yj=poly[j][1];
      if(((yi>lat)!==(yj>lat))&&lon<(xj-xi)*(lat-yi)/(yj-yi)+xi)inside=!inside;
    }
    return inside;
  }
  function buildDots(polys){
    var dots=[];
    polys.forEach(function(poly){
      var minLon=180,maxLon=-180,minLat=90,maxLat=-90;
      poly.forEach(function(p){minLon=Math.min(minLon,p[0]);maxLon=Math.max(maxLon,p[0]);minLat=Math.min(minLat,p[1]);maxLat=Math.max(maxLat,p[1]);});
      for(var lat=Math.ceil(minLat/3)*3;lat<=maxLat;lat+=3)
        for(var lon=Math.ceil(minLon/3)*3;lon<=maxLon;lon+=3)
          if(pointInPolygon(lon,lat,poly))dots.push([lon,lat]);
    });
    return dots;
  }
  function armGlobes(){
    document.querySelectorAll('#i3-page canvas[data-i3-globe]').forEach(function(canvas){
      if(stillArmed(canvas,null,'globe'))return;
      var gen=claim(canvas,'globe');
      function own(fn){return function(e){if(canvas.__i3gen===gen)return fn(e);};}
      var ctx=canvas.getContext('2d');if(!ctx)return;
      var nodes=readJSON(canvas,'data-i3-nodes',[]),links=readJSON(canvas,'data-i3-links',[]);
      var note=canvas.parentElement&&canvas.parentElement.querySelector('.i3-globe-note');
      var dpr=Math.min(devicePixelRatio||1,2),yaw=0,pitch=-12,roll=0,zoom=1,spinDir=-1,baseYaw=.20*spinDir;
      var drag=false,lastX=0,lastY=0,velYaw=baseYaw,velPitch=0,velRoll=0,coastUntil=0,hits=[],land={polygons:[],points:[]};
      var rot=[1,0,1,0,1,0];
      function wrapA(v){return ((v+180)%360+360)%360-180;}
      function limitV(v){return clamp(v,-1,1);}
      function size(){var w=Math.max(64,canvas.clientWidth||330),h=Math.max(64,canvas.clientHeight||330);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
      function rotate(x,y,z){
        var x1=x*rot[0]+z*rot[1],z1=-x*rot[1]+z*rot[0],y2=y*rot[2]-z1*rot[3],z2=y*rot[3]+z1*rot[2];
        return [x1*rot[4]-y2*rot[5],x1*rot[5]+y2*rot[4],z2];
      }
      function unit(lon,lat){var la=lon*Math.PI/180,ph=lat*Math.PI/180,cp=Math.cos(ph);return [cp*Math.sin(la),-Math.sin(ph),cp*Math.cos(la)];}
      function project(lon,lat,w,h,r){var u=unit(lon,lat),p=rotate(u[0],u[1],u[2]);return [w/2+p[0]*r,h/2+p[1]*r,p[2]];}
      function render(){
        var ay=yaw*Math.PI/180,ax=pitch*Math.PI/180,az=roll*Math.PI/180;
        rot=[Math.cos(ay),Math.sin(ay),Math.cos(ax),Math.sin(ax),Math.cos(az),Math.sin(az)];
        var w=canvas.width/dpr,h=canvas.height/dpr,r=Math.min(w,h)*.37*zoom,vs=Math.max(.72,Math.min(1.35,w/300));
        ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
        var ocean=ctx.createRadialGradient(w*.42,h*.36,2,w/2,h/2,r);ocean.addColorStop(0,PALETTE.oceanIn);ocean.addColorStop(1,PALETTE.oceanOut);
        ctx.beginPath();ctx.arc(w/2,h/2,r,0,Math.PI*2);ctx.fillStyle=ocean;ctx.fill();
        ctx.save();ctx.shadowColor='rgba(49,215,230,.8)';ctx.shadowBlur=18*vs;ctx.strokeStyle=PALETTE.limb;ctx.lineWidth=.8*vs;ctx.stroke();ctx.restore();
        function curve(samples){
          ctx.beginPath();var on=false;
          for(var i=0;i<samples.length;i++){var p=project(samples[i][0],samples[i][1],w,h,r);
            if(p[2]<=0){on=false;continue;}if(!on){ctx.moveTo(p[0],p[1]);on=true;}else ctx.lineTo(p[0],p[1]);}
          ctx.stroke();
        }
        ctx.strokeStyle=PALETTE.grat;ctx.lineWidth=.6*vs;
        for(var gl=-60;gl<=60;gl+=30){var ls=[];for(var lo=-180;lo<=180;lo+=5)ls.push([lo,gl]);curve(ls);}
        for(var gn=-150;gn<=180;gn+=30){var ps=[];for(var la=-90;la<=90;la+=4)ps.push([gn,la]);curve(ps);}
        ctx.strokeStyle=PALETTE.land;ctx.lineWidth=.85*vs;
        land.polygons.forEach(function(poly){curve(poly.concat([poly[0]]));});
        land.points.forEach(function(pt){var q=project(pt[0],pt[1],w,h,r);if(q[2]<=0)return;
          ctx.beginPath();ctx.arc(q[0],q[1],.92*vs,0,Math.PI*2);ctx.fillStyle='rgba('+PALETTE.dot+','+(.46+q[2]*.46).toFixed(3)+')';ctx.fill();});
        // exterior great-circle arcs lifted clear of the surface
        ctx.save();ctx.lineCap='round';
        links.forEach(function(lk){
          var a=nodes[lk[0]],b=nodes[lk[1]];if(!a||!b)return;
          var va=unit(a.lon,a.lat),vb=unit(b.lon,b.lat),dot=clamp(va[0]*vb[0]+va[1]*vb[1]+va[2]*vb[2],-1,1),om=Math.acos(dot),so=Math.sin(om);
          if(so<1e-4)return;
          var run=[],front=0,total=0;
          for(var t=0;t<=26;t++){
            var f=t/26,c1=Math.sin((1-f)*om)/so,c2=Math.sin(f*om)/so,h1=1+.21*Math.sin(Math.PI*f);
            var p=rotate((va[0]*c1+vb[0]*c2)*h1,(va[1]*c1+vb[1]*c2)*h1,(va[2]*c1+vb[2]*c2)*h1);
            var sx=w/2+p[0]*r,sy=h/2+p[1]*r,hidden=p[2]<0&&Math.sqrt(p[0]*p[0]+p[1]*p[1])<1;
            total++;if(!hidden)front++;
            if(hidden){if(run.length>1)stroke(run,front/total);run=[];}else run.push([sx,sy]);
          }
          if(run.length>1)stroke(run,front/Math.max(1,total));
        });
        function stroke(pts,vis){
          var g=.30+vis*.55;ctx.save();ctx.shadowColor='rgba(64,214,255,'+(g*.9).toFixed(3)+')';ctx.shadowBlur=9*vs;
          var gr=ctx.createLinearGradient(pts[0][0],pts[0][1],pts[pts.length-1][0],pts[pts.length-1][1]);
          gr.addColorStop(0,'rgba(88,226,255,'+(g*.55).toFixed(3)+')');gr.addColorStop(.5,'rgba(196,246,255,'+g.toFixed(3)+')');gr.addColorStop(1,'rgba(146,168,255,'+(g*.6).toFixed(3)+')');
          ctx.strokeStyle=gr;ctx.lineWidth=1.45*vs;ctx.beginPath();ctx.moveTo(pts[0][0],pts[0][1]);
          for(var q=1;q<pts.length;q++)ctx.lineTo(pts[q][0],pts[q][1]);ctx.stroke();ctx.restore();
        }
        ctx.restore();
        hits=[];
        nodes.forEach(function(node,m){
          var mp=project(node.lon,node.lat,w,h,r);if(mp[2]<=0)return;
          var depth=.45+mp[2]*.55,pulse=(5.4+Math.sin(performance.now()*.0026+m*1.7)*1.5)*vs;
          ctx.save();ctx.shadowColor='rgba(120,236,255,'+(depth*.95).toFixed(3)+')';ctx.shadowBlur=16*vs;
          ctx.strokeStyle='rgba(96,226,255,'+(depth*.55).toFixed(3)+')';ctx.lineWidth=1.1*vs;ctx.beginPath();ctx.arc(mp[0],mp[1],pulse,0,Math.PI*2);ctx.stroke();
          ctx.fillStyle='rgba(214,250,255,'+depth.toFixed(3)+')';ctx.beginPath();ctx.arc(mp[0],mp[1],2.9*vs,0,Math.PI*2);ctx.fill();
          ctx.restore();hits.push({x:mp[0],y:mp[1],r:14*vs,node:node});
        });
      }
      function select(e){
        var rc=canvas.getBoundingClientRect(),x=e.clientX-rc.left,y=e.clientY-rc.top,best=null,bd=1e9;
        hits.forEach(function(h){var d=Math.hypot(x-h.x,y-h.y);if(d<h.r&&d<bd){bd=d;best=h;}});
        if(!best||!note)return;
        note.hidden=false;note.querySelector('b').textContent=best.node.name||'';note.querySelector('span').textContent=best.node.summary||'';
        e.preventDefault();e.stopPropagation();
      }
      function coast(s){coastUntil=Math.max(coastUntil,performance.now()+Math.min(3200,360+Math.max(0,s)*70));}
      var grabbedUntil=0;
      canvas.addEventListener('pointerdown',own(function(e){grabbedUntil=performance.now()+3000;try{canvas.setPointerCapture(e.pointerId);}catch(x){}drag=true;lastX=e.clientX;lastY=e.clientY;velYaw=velPitch=velRoll=0;}));
      canvas.addEventListener('pointermove',own(function(e){if(!drag)return;var dx=e.clientX-lastX,dy=e.clientY-lastY;
        if(e.shiftKey){roll+=dx*.24;velRoll=limitV(dx*.04);}else{yaw+=dx*.24;pitch-=dy*.22;velYaw=limitV(dx*.04);velPitch=limitV(-dy*.035);}
        lastX=e.clientX;lastY=e.clientY;render();}));
      var up=own(function(e){if(!drag)return;drag=false;coast((Math.abs(velYaw)+Math.abs(velPitch)+Math.abs(velRoll))*18);try{canvas.releasePointerCapture(e.pointerId);}catch(x){}});
      canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);
      canvas.addEventListener('wheel',own(function(e){
        if(!e.ctrlKey&&!e.shiftKey&&performance.now()>grabbedUntil)return;   // let the page scroll unless grabbed
        e.preventDefault();
        var rx=clamp(e.deltaX,-28,28),ry=clamp(e.deltaY,-28,28);
        if(e.ctrlKey)zoom=clamp(zoom*Math.exp(-ry*.003),.84,1.08);
        else{yaw+=-rx*.075;pitch-=-ry*.065;coast(Math.abs(rx)+Math.abs(ry));}
        render();
      }),{passive:false});
      canvas.addEventListener('click',own(select));
      canvas.addEventListener('dblclick',own(function(e){e.preventDefault();spinDir*=-1;baseYaw=.20*spinDir;velYaw=baseYaw;}));
      size();render();
      loadLand(function(l){land=l;if(attached(canvas)&&canvas.__i3gen===gen)render();});
      addEventListener('resize',function(){if(attached(canvas)&&canvas.__i3gen===gen){size();render();}},{passive:true});
      var lastF=0;
      (function frame(now){
        if(!attached(canvas)||canvas.__i3gen!==gen)return;requestAnimationFrame(frame);
        var b=canvas.getBoundingClientRect();
        if(document.hidden||b.bottom<0||b.top>innerHeight||drag||reduceMotion()||now-lastF<FRAME_INTERVAL-0.75){if(document.hidden)lastF=0;return;}
        var dt=lastF?Math.min(70,now-lastF):33;lastF=now;var f=dt/33;
        var settle=1-Math.exp(-dt/(now<coastUntil?2600:880));
        velYaw+=(baseYaw-velYaw)*settle;velPitch+=(0-velPitch)*settle;velRoll+=(0-velRoll)*settle;
        yaw=wrapA(yaw+velYaw*f);pitch=wrapA(pitch+velPitch*f);roll=wrapA(roll+velRoll*f);render();
      })(performance.now());
    });
  }

  // ══ WIRE SPHERE — the NVTRA mascot; also usable as an orbit core ═════════
  function armSpheres(root){
    (root||document).querySelectorAll('canvas[data-i3-sphere]').forEach(function(canvas){
      if(canvas.__i3kind==='sphere'&&canvas.__i3gen&&attached(canvas)&&(canvas.__i3fixed||stillArmed(canvas,null,'sphere')))return;
      var gen=claim(canvas,'sphere');canvas.__i3fixed=!canvas.closest('#i3-page');
      var ctx=canvas.getContext('2d');if(!ctx)return;
      var dpr=Math.min(devicePixelRatio||1,1.5);
      function size(){canvas.width=Math.round((canvas.clientWidth||300)*dpr);canvas.height=Math.round((canvas.clientHeight||300)*dpr);}
      size();
      var LAT=6,LON=14,grid=[];
      for(var i=0;i<=LAT;i++){var th=Math.PI*i/LAT,row=[];for(var j=0;j<LON;j++){var ph=2*Math.PI*j/LON;row.push([Math.sin(th)*Math.cos(ph),Math.cos(th),Math.sin(th)*Math.sin(ph)]);}grid.push(row);}
      var ay=0,ax=.42,last=0,spin=parseFloat(canvas.getAttribute('data-i3-sphere'))||1;
      (function frame(ts){
        if(!attached(canvas)||canvas.__i3gen!==gen)return;
        requestAnimationFrame(frame);
        if(document.hidden)return;
        if(ts&&ts-last<FRAME_INTERVAL-0.75)return;
        var dt=last?Math.min(50,ts-last):1000/144;last=ts||0;
        if(canvas.clientWidth>0&&Math.abs(canvas.width-Math.round(canvas.clientWidth*dpr))>4)size();
        var w=canvas.width,h=canvas.height;if(!w||!h)return;
        if(!reduceMotion())ay+=.006*spin*(dt/(1000/30));
        var cx=w/2,cy=h/2,sc=Math.min(w,h)*.33,cY=Math.cos(ay),sY=Math.sin(ay),cX=Math.cos(ax),sX=Math.sin(ax);
        ctx.clearRect(0,0,w,h);ctx.globalCompositeOperation='lighter';
        function proj(p){var x1=p[0]*cY-p[2]*sY,z1=p[0]*sY+p[2]*cY,y1=p[1]*cX-z1*sX,z2=p[1]*sX+z1*cX,d=2.6/(2.6+z2);return [cx+x1*d*sc,cy-y1*d*sc,z2];}
        var P=grid.map(function(r){return r.map(proj);});
        function edge(a,b){var al=.12+.44*(1-((a[2]+b[2])/2+1)/2);ctx.strokeStyle='rgba('+PALETTE.accent+','+al.toFixed(3)+')';ctx.lineWidth=dpr;ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();}
        for(var i=0;i<=LAT;i++)for(var j=0;j<LON;j++){edge(P[i][j],P[i][(j+1)%LON]);if(i<LAT)edge(P[i][j],P[i+1][j]);}
        var g=ctx.createRadialGradient(cx,cy,0,cx,cy,sc*.55);
        g.addColorStop(0,'rgba('+PALETTE.accent+',0.45)');g.addColorStop(.6,'rgba('+PALETTE.accent2+',0.12)');g.addColorStop(1,'rgba('+PALETTE.accent+',0)');
        ctx.fillStyle=g;ctx.beginPath();ctx.arc(cx,cy,sc*.55,0,7);ctx.fill();ctx.globalCompositeOperation='source-over';
      })();
    });
  }

  // ══ NVTRA DOCK — the intelligence island ═════════════════════════════════
  // Default answer when no backend is wired. Replace window.I3.ask to connect NVTRA.
  if(!I3.ask){
    I3.ask=function(question){
      if(CFG.askUrl){
        return fetch(CFG.askUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:question,path:location.pathname})})
          .then(function(r){return r.json();}).then(function(d){return d.answer||'';});
      }
      return Promise.resolve('NVTRA is not connected to this interface yet.');
    };
  }
  function armDock(){
    var dock=document.getElementById('i3-dock');
    if(!dock||dock.dataset.armed==='1')return;dock.dataset.armed='1';
    armSpheres(dock);
    var log=dock.querySelector('.i3-dock-log'),slot=dock.querySelector('.i3-dock-form'),form=null,input=null;
    if(slot){
      form=document.createElement('form');form.className='i3-dock-form';
      input=document.createElement('input');input.type='text';input.autocomplete='off';
      input.placeholder=slot.getAttribute('data-i3-placeholder')||'Ask';input.setAttribute('aria-label','Question');
      var send=document.createElement('button');send.type='submit';send.textContent='Ask';
      form.appendChild(input);form.appendChild(send);slot.replaceWith(form);
    }
    function setOpen(open){dock.classList.toggle('is-collapsed',!open);if(open&&input)setTimeout(function(){input.focus();},60);}
    dock.addEventListener('click',function(e){if(dock.classList.contains('is-collapsed')){setOpen(true);e.stopPropagation();}});
    document.addEventListener('click',function(e){if(!dock.contains(e.target)&&!dock.classList.contains('is-collapsed'))setOpen(false);});
    document.addEventListener('keydown',function(e){
      if(e.target.matches&&e.target.matches('input,textarea,select'))return;
      if(e.key==='n'&&!e.metaKey&&!e.ctrlKey&&!e.altKey){setOpen(dock.classList.contains('is-collapsed'));}
      if(e.key==='Escape')setOpen(false);
    });
    if(form)form.addEventListener('submit',function(e){
      e.preventDefault();var q=(input.value||'').trim();if(!q)return;input.value='';
      var me=document.createElement('p');me.className='me';me.textContent=q;log.appendChild(me);
      var out=document.createElement('p');out.textContent='…';log.appendChild(out);log.scrollTop=log.scrollHeight;
      Promise.resolve(I3.ask(q)).then(function(a){out.textContent=a||'';}).catch(function(){out.textContent='NVTRA could not answer.';})
        .then(function(){log.scrollTop=log.scrollHeight;});
    });
  }

  // ══ LIVE VALUES — [data-i3-bind] elements follow a JSON state feed ═══════
  // A value may be plain ("84.7 %") or {value, state} where state is ok|warn|high|off;
  // the state lands on the nearest .i3-dot inside the bound element's parent.
  I3.set=function(key,value,state){
    if(Array.isArray(value)){
      document.querySelectorAll('canvas[data-i3-spark="'+key+'"]').forEach(function(c){c.__i3data=value;drawSpark(c);});
      return;
    }
    document.querySelectorAll('[data-i3-bind="'+key+'"]').forEach(function(el){
      var text=value==null?'—':String(value);
      el.textContent=text;
      // Words, not numbers: set them smaller so a metric box never breaks a word in half.
      var box=el.closest&&el.closest('.i3-metric-v');
      if(box)box.classList.toggle('is-text',/[A-Za-z]{3,}/.test(text.replace(/\b(µ?[A-Za-z]{1,3}|RMS|dB[a-z]*)\b$/,''))||text.length>14);
      if(state){var dot=el.parentElement&&el.parentElement.querySelector('.i3-dot');if(dot)dot.className='i3-dot '+state;}
    });
  };
  function applyState(data){
    Object.keys(data||{}).forEach(function(k){
      var v=data[k];
      if(v&&typeof v==='object'&&!Array.isArray(v))I3.set(k,v.value,v.state);else I3.set(k,v);
    });
  }
  // A live trace drawn round zero (deviation from baseline), auto-scaled symmetrically.
  function drawSpark(canvas){
    var data=canvas.__i3data||[],dpr=Math.min(devicePixelRatio||1,2);
    var w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h)return;
    if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
    var ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    var acc=(getComputedStyle(canvas).getPropertyValue('--acc')||'').trim()||'#00e5ff';
    ctx.strokeStyle='rgba(255,255,255,.08)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,h/2);ctx.lineTo(w,h/2);ctx.stroke();
    if(data.length<2)return;
    var m=0;data.forEach(function(v){m=Math.max(m,Math.abs(v));});m=m||1;
    ctx.beginPath();
    data.forEach(function(v,i){var x=i/(data.length-1)*w,y=h/2-(v/m)*(h/2-4);if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y);});
    ctx.strokeStyle=acc;ctx.lineWidth=1.4;ctx.shadowColor=acc;ctx.shadowBlur=6;ctx.stroke();ctx.shadowBlur=0;
  }
  addEventListener('resize',function(){document.querySelectorAll('canvas[data-i3-spark]').forEach(drawSpark);},{passive:true});

  // ══ ACTIONS — [data-i3-action] buttons post to the host's action handler ═══
  document.addEventListener('click',function(e){
    var btn=e.target.closest&&e.target.closest('[data-i3-action]');if(!btn||!CFG.actionUrl)return;
    var spec;try{spec=JSON.parse(btn.getAttribute('data-i3-action'));}catch(x){return;}
    var args=Object.assign({},spec.args||{});
    if(spec.confirm&&!confirm(spec.confirm))return;
    if(spec.prompt){var answer=prompt(spec.prompt);if(!answer)return;args.name=answer.trim();}
    var out=btn.closest('.i3-actions');out=out&&out.querySelector('.i3-action-out');
    if(out){out.textContent='…';out.className='i3-action-out';}
    btn.disabled=true;
    fetch(CFG.actionUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:spec.action,args:args})})
      .then(function(r){return r.json();}).then(function(d){
        if(out){out.textContent=d.message||'';out.className='i3-action-out '+(d.ok?'ok':'err');}
        if(I3.refresh)I3.refresh();
      }).catch(function(){if(out){out.textContent='The studio did not answer.';out.className='i3-action-out err';}})
      .then(function(){btn.disabled=false;});
  });

  function pollState(){
    if(!CFG.stateUrl)return;
    var busy=false;
    function tick(){
      if(busy||document.hidden)return;busy=true;
      fetch(CFG.stateUrl,{cache:'no-store'}).then(function(r){return r.ok?r.json():null;}).then(applyState).catch(function(){}).then(function(){busy=false;});
    }
    I3.refresh=tick;tick();setInterval(tick,CFG.statePollMs||1500);
  }

  // ══ SETTINGS ══════════════════════════════════════════════════════════════
  function armSettings(){
    document.querySelectorAll('#i3-page [data-i3-setting="anim"]').forEach(function(seg){
      if(seg.dataset.armed==='1')return;seg.dataset.armed='1';
      function sync(){var off=document.documentElement.classList.contains('i3-no-anim');
        seg.querySelectorAll('button').forEach(function(b){b.classList.toggle('is-on',(b.value==='off')===off);});}
      seg.addEventListener('click',function(e){
        var b=e.target.closest('button');if(!b)return;
        var off=b.value==='off';document.documentElement.classList.toggle('i3-no-anim',off);
        try{localStorage.setItem('i3-anim',off?'off':'on');}catch(x){}
        if(!off)bootPageShader();else{var s=document.getElementById('i3-page-shader');if(s)s.remove();}
        sync();
      });
      sync();
    });
  }

  // ══ NAV — active state follows the route ═════════════════════════════════
  function syncNav(){
    var path=location.pathname.replace(/\/(index\.html)?$/,'')||'/';   // static hosts add / or index.html
    document.querySelectorAll('.i3-nav-btn[data-i3-path]').forEach(function(b){
      var p=b.getAttribute('data-i3-path').replace(/\/$/,'')||'/';
      b.classList.toggle('is-active',p===path||(p!=='/'&&path.indexOf(p+'/')===0));
    });
  }

  // ══ ARM — run on load and after every routed page swap ═══════════════════
  var lastPath=null;
  function arm(){
    if(location.pathname!==lastPath){
      if(lastPath!==null&&window.__i3IntroDone!==false)resetScroll();
      lastPath=location.pathname;document.body.classList.remove('i3-pillar-open');
    }
    syncNav();armScrub();armOrbits();armGlobes();armSpheres(document.getElementById('i3-page'));armSettings();armDock();
  }
  I3.rearm=arm;
  var pending=0;
  function schedule(){if(pending)return;pending=requestAnimationFrame(function(){pending=0;arm();});}

  function start(){
    if(!document.body)return setTimeout(start,20);
    if(document.querySelector('.i3-notice'))document.body.classList.add('has-notice');
    bootPageShader();
    var introWaitUntil=Date.now()+3000;
    (function waitIntro(){if(!bootIntro()&&Date.now()<introWaitUntil)setTimeout(waitIntro,40);})();
    new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
    addEventListener('popstate',schedule);
    schedule();pollState();
  }
  if(CFG.forceHomeOnLoad){
    if('scrollRestoration' in history)history.scrollRestoration='manual';
    try{if(location.pathname!=='/')history.replaceState(history.state,'','/'+location.search);}catch(e){}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
