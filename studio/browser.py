"""SCRUB_JS: the browser layer (page shader, intro, orbits, globe, constellation, hand vision)."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system', 'tokens', 'theme')

# ════════════════════════════════════════════════════════
#  BROWSER LAYER  (SCRUB_JS)
#
#  Rules this file obeys, in order of how much jitter they removed:
#   1. ONE MutationObserver, scoped to #page-content, childList only, debounced. It
#      does not re-run global boots — a Dash value update must never restart an effect.
#   2. Every requestAnimationFrame loop checks that its element is still in the
#      document and returns permanently when it is not. Leaving orphaned RAF loops
#      running after navigation was a real CPU leak on this host.
#   3. dcc.Link scrolls the window to 0 SYNCHRONOUSLY on click, before the new page
#      exists. That is what made the OLD page visibly jump before switching. We swallow
#      exactly that one scroll and do our own instant reset when the new content mounts.
#   4. No GSAP, no ScrollTrigger, no CDN. disarmOrphans() stays as a defensive kill for
#      any ScrollTrigger a future build might introduce.
#   5. The only "loading" affordance is a 2px bar under the header. The page is never
#      blanked, so there is no white flash between routes.
# ════════════════════════════════════════════════════════
SCRUB_JS = r"""
(function(){
  'use strict';

  // ── shared helpers ─────────────────────────────────────────────────────────
  var INTRO_TRIGGER_ID='studio-startup-intro';
  // Sensor and Plotly refresh intervals are identical on phone and desktop. Only
  // visual loops target up to 144 Hz on every display, including touch screens.
  // requestAnimationFrame follows the actual display; sensor polling is unchanged.
  var COARSE_DEVICE=false;
  try{COARSE_DEVICE=matchMedia('(pointer:coarse)').matches||navigator.maxTouchPoints>0;}catch(e){}
  var FRAME_INTERVAL=1000/144;
  function attached(el){ return !!(el && el.isConnected); }
  // The startup intro is a fixed overlay, never part of document flow. Therefore
  // every routed module has one stable top: document scroll position zero.
  function resetScroll(){
    try{ window.scrollTo(0,0); }catch(e){}
    if(document.documentElement)document.documentElement.scrollTop=0;
    if(document.body)document.body.scrollTop=0;
  }
  // Shared with the routing clientside callback so route changes and in-page view
  // changes use ONE definition of "top of the current module".
  window.__i3ResetScroll=resetScroll;
  function reduceMotion(){
    try{
      if(document.documentElement.classList.contains('no-anim')) return true;
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }catch(e){ return false; }
  }

  // ── Canvas palette ────────────────────────────────────────────────────────
  // The globe, the constellation and the mascot paint to <canvas>, so the light
  // mode stylesheet can never reach them — they stayed dark-on-white and read as
  // foreign objects dropped into the page. Each render pulls its ink from here
  // instead of hardcoding hex, so they follow the theme like every other surface.
  var _i3Light=null;
  function i3Theme(){
    var light=false;
    if(_i3Light && _i3Light.light===light) return _i3Light;
    _i3Light = light ? {
      light:true,
      oceanIn:'rgba(238,243,249,.96)', oceanOut:'rgba(214,224,238,.98)',
      limb:'rgba(22,32,46,.38)', grat:'rgba(22,32,46,.14)',
      land:'rgba(22,32,46,.42)', dot:'30,45,66',
      plate:'255,255,255', plateInk:'#26364c',
      ring:'rgba(22,32,46,.12)', starNear:'#33405a', starFar:'#93a2b6',
      accent:'0,121,143', accent2:'21,101,216'
    } : {
      light:false,
      oceanIn:'rgba(17,52,96,.95)', oceanOut:'rgba(4,10,24,.98)',
      limb:'rgba(140,224,255,.72)', grat:'rgba(96,178,235,.34)',
      land:'rgba(150,224,255,.66)', dot:'150,228,255',
      plate:'9,14,22', plateInk:'#cbd7e5',
      ring:'rgba(137,163,194,.10)', starNear:'#c7d8e8', starFar:'#66809a',
      accent:'0,229,255', accent2:'41,121,255'
    };
    return _i3Light;
  }

  var CHIP_INFO={
    'Item 1': {icon:'∿',field:'Heading 1',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 2': {icon:'σ',field:'Heading 1',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 3': {icon:'|v|',field:'Heading 1',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 4': {icon:'unit',field:'Heading 1',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 5': {icon:'⚡',field:'Heading 2',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 6': {icon:'〜',field:'Heading 2',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 7': {icon:'Φ',field:'Heading 2',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 8': {icon:'∇',field:'Heading 2',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 9': {icon:'⊞',field:'Heading 3',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 10': {icon:'⟷',field:'Heading 3',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 11': {icon:'⊡',field:'Heading 3',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 12': {icon:'⊟',field:'Heading 3',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 13': {icon:'⬡',field:'Heading 4',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 14': {icon:'⇉',field:'Heading 4',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 15': {icon:'◈',field:'Heading 4',desc:'Paragraph. Enter your text here.',tag:'Text'},
    'Item 16': {icon:'≈',field:'Heading 4',desc:'Paragraph. Enter your text here.',tag:'Text'}
  };

  function showChipPopup(chip,info){
    var old=document.getElementById('chip-popup');if(old)old.remove();
    var pop=document.createElement('div');pop.id='chip-popup';pop.className='chip-popup';
    var rect=chip.getBoundingClientRect();
    // The old maths assumed a 300x220 box and a viewport wider than it, so on a
    // narrow window `innerWidth-300` went negative and on a short one the flipped
    // position still overflowed. Measure the box after insertion instead, then
    // clamp both axes to the real viewport.
    var GAP=8;
    var left=rect.left, top=rect.bottom+GAP, placed=false;
    pop.style.left=left+'px';pop.style.top=top+'px';
    var inner=document.createElement('div');inner.className='chip-popup-inner';
    var head=document.createElement('div');head.className='chip-popup-header';
    var icon=document.createElement('div');icon.className='chip-popup-icon';icon.textContent=info.icon;
    var meta=document.createElement('div');
    var title=document.createElement('div');title.className='chip-popup-title';title.textContent=chip.textContent.trim();
    var field=document.createElement('div');field.className='chip-popup-field';field.textContent=info.field;
    meta.appendChild(title);meta.appendChild(field);
    var close=document.createElement('button');close.className='chip-popup-close';close.textContent='✕';
    close.addEventListener('click',function(){var p=document.getElementById('chip-popup');if(p)p.remove();});
    head.appendChild(icon);head.appendChild(meta);head.appendChild(close);
    var body=document.createElement('div');body.className='chip-popup-body';body.textContent=info.desc;
    var tag=document.createElement('div');tag.className='chip-popup-tag';tag.textContent=info.tag;
    inner.appendChild(head);inner.appendChild(body);inner.appendChild(tag);
    pop.appendChild(inner);
    document.body.appendChild(pop);
    // Now that it has a real box, place it: prefer below the chip, flip above when
    // that would overflow, then clamp to the viewport on both axes.
    var box=pop.getBoundingClientRect();
    var vw=document.documentElement.clientWidth, vh=document.documentElement.clientHeight;
    if(top+box.height+GAP>vh){
      var above=rect.top-box.height-GAP;
      if(above>=GAP){top=above;placed=true;}
    } else placed=true;
    if(!placed) top=Math.max(GAP,vh-box.height-GAP);
    left=Math.max(GAP,Math.min(left,vw-box.width-GAP));
    top=Math.max(GAP,Math.min(top,vh-box.height-GAP));
    pop.style.left=left+'px';pop.style.top=top+'px';
    if(!document.__chipDocBound){
      document.__chipDocBound=true;
      document.addEventListener('click',function(e){
        var p=document.getElementById('chip-popup');
        if(p&&!p.contains(e.target)&&!(e.target.closest&&e.target.closest('.pillar-chip')))p.remove();
      });
    }
    clearTimeout(window.__chipTimer);
    window.__chipTimer=setTimeout(function(){
      var p=document.getElementById('chip-popup');if(p)p.remove();
    },7000);
  }

  // DOM-scoped: must be re-armed after #page-content is replaced, but only for
  // elements that have not been armed yet.
  function armChipClicks(){
    var chips=document.querySelectorAll('.pillar-chip:not([data-chip-armed])');
    for(var i=0;i<chips.length;i++){
      (function(chip){
        chip.dataset.chipArmed='1';
        chip.addEventListener('click',function(e){
          e.stopPropagation();
          var info=CHIP_INFO[chip.textContent.trim()];
          var active=document.querySelectorAll('.pillar-chip.active-chip');
          for(var k=0;k<active.length;k++)active[k].classList.remove('active-chip');
          chip.classList.add('active-chip');
          if(info)showChipPopup(chip,info);
        });
      })(chips[i]);
    }
  }

  // Kill module-scoped ScrollTriggers whose trigger element left the DOM on a route
  // change. The startup intro is explicitly exempt: its trigger (#startup-intro)
  // lives in the permanent shell and stays attached, and it is never killed while
  // it is active.
  function disarmOrphans(){
    if(!window.ScrollTrigger||!window.ScrollTrigger.getAll)return;
    window.ScrollTrigger.getAll().forEach(function(t){
      if(t.vars&&t.vars.id===INTRO_TRIGGER_ID)return;             // never the intro
      if(!t.trigger||!document.body.contains(t.trigger)){ try{t.kill();}catch(e){} }
    });
  }

  // ── discipline-architecture SVG (MTDI > I3 pane) ───────────────────────────
  function armDiscSvg(){
    var host=document.querySelector('.disc-svg-host');
    if(!host||host.dataset.discInited==='1')return;
    var root=document.querySelector('.disc-title-card');
    var titles=document.querySelectorAll('.pillar-header');
    if(!root||titles.length<4)return;
    host.dataset.discInited='1';
    var NS='http://www.w3.org/2000/svg';
    var running=true;
    function mkEl(tag,attrs){var el=document.createElementNS(NS,tag);Object.keys(attrs).forEach(function(k){el.setAttribute(k,attrs[k]);});return el;}
    function build(){
      while(host.firstChild)host.removeChild(host.firstChild);
      var hR=host.getBoundingClientRect(),rR=root.getBoundingClientRect();
      var sx=rR.left+rR.width/2-hR.left,sy=rR.bottom-hR.top+2;
      var svg=document.createElementNS(NS,'svg');
      svg.style.cssText='position:absolute;top:0;left:0;width:100%;height:100%;overflow:visible;pointer-events:none;';
      var defs=document.createElementNS(NS,'defs');
      for(var li=0;li<4;li++){
        var lg=mkEl('linearGradient',{id:'disc-lg-'+li,gradientUnits:'userSpaceOnUse'});
        lg.appendChild(mkEl('stop',{offset:'0%','stop-color':'#00e5ff','stop-opacity':'0.85'}));
        lg.appendChild(mkEl('stop',{offset:'100%','stop-color':'#2979ff','stop-opacity':'0.4'}));
        defs.appendChild(lg);
      }
      svg.appendChild(defs);
      svg.appendChild(mkEl('circle',{cx:sx,cy:sy,r:'3',fill:'#00e5ff'}));
      var aP=[];
      for(var i=0;i<4;i++){
        var th=titles[i].getBoundingClientRect();
        var tx=th.left+th.width/2-hR.left,ty=th.top+th.height/2-hR.top,mY=sy+(ty-sy)*0.5;
        var d='M '+sx.toFixed(1)+' '+sy.toFixed(1)+' C '+sx.toFixed(1)+' '+mY.toFixed(1)+','+tx.toFixed(1)+' '+mY.toFixed(1)+','+tx.toFixed(1)+' '+ty.toFixed(1);
        var lg2=svg.querySelector('#disc-lg-'+i);
        if(lg2){lg2.setAttribute('x1',sx);lg2.setAttribute('y1',sy);lg2.setAttribute('x2',tx);lg2.setAttribute('y2',ty);}
        var mainLine=mkEl('path',{d:d,fill:'none',stroke:'url(#disc-lg-'+i+')','stroke-width':'1.5','stroke-dasharray':'6 5','stroke-linecap':'round',opacity:'0.9'});
        svg.appendChild(mainLine);
        var dots=[];
        if(!reduceMotion()){
          for(var k=0;k<2;k++){
            var dt=mkEl('circle',{r:'3',fill:'#00e5ff',opacity:'0'});
            svg.appendChild(dt);dots.push({dot:dt,phase:i*0.25+k*0.52});
          }
        }
        aP.push({path:mainLine,len:0,dots:dots});
      }
      host.appendChild(svg);
      aP.forEach(function(ap){try{ap.len=ap.path.getTotalLength();}catch(e){ap.len=300;}});
      return aP;
    }
    var paths=build();
    var t0=performance.now();
    (function tick(){
      // Stop for good once the MTDI pane is unmounted. Without this the loop keeps
      // running for the life of the tab after a single visit to the pillar.
      if(!running||!attached(host)){running=false;host.dataset.discInited='0';return;}
      requestAnimationFrame(tick);
      if(reduceMotion())return;
      var now=(performance.now()-t0)/1000;
      for(var i=0;i<paths.length;i++){
        var ap=paths[i];
        for(var k=0;k<ap.dots.length;k++){
          var dk=ap.dots[k],t=((now*0.36+dk.phase)%1);
          var pt;try{pt=ap.path.getPointAtLength(t*ap.len);}catch(e){continue;}
          var fade=t<0.08?t/0.08:(t>0.84?(1-t)/0.16:1);
          fade=Math.max(0,Math.min(1,fade));
          dk.dot.setAttribute('cx',pt.x);dk.dot.setAttribute('cy',pt.y);
          dk.dot.setAttribute('opacity',fade.toFixed(3));
        }
      }
    })();
    if(!window.__discResizeBound){
      window.__discResizeBound=true;
      var rt;
      window.addEventListener('resize',function(){
        clearTimeout(rt);
        rt=setTimeout(function(){
          var h=document.querySelector('.disc-svg-host');
          if(h&&h.dataset.discInited==='1'&&typeof h.__rebuild==='function')h.__rebuild();
        },220);
      },{passive:true});
    }
    host.__rebuild=function(){paths=build();};
  }

  // ── full-page background shader ────────────────────────────────────────────
  function bootPageShader(){
    if(document.getElementById('page-shader-canvas'))return;
    if(reduceMotion())return;
    var canvas=document.createElement('canvas');
    canvas.id='page-shader-canvas';
    canvas.style.cssText='position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.28;';
    document.body.insertBefore(canvas,document.body.firstChild);
    var gl=canvas.getContext('webgl',{powerPreference:'high-performance',antialias:false,alpha:false,depth:false,stencil:false})||canvas.getContext('experimental-webgl');
    if(!gl){canvas.remove();return;}
    var VS='attribute vec4 aVertexPosition;void main(){gl_Position=aVertexPosition;}';
    var FS=['precision highp float;','uniform vec2 iResolution; uniform float iTime;','const float S=0.045,sc=5.0;','const vec4 lc=vec4(0.08,0.25,1.0,1.0);','float rnd(float t){return(cos(t)+cos(t*1.3+1.3)+cos(t*1.4+1.4))/3.0;}','float py(float x,float hf,float off){return rnd(x*0.2+iTime*S)*hf+off;}','#define cr(p,hw,t) smoothstep(hw+0.015,hw,abs(p-(t)))','#define sm(p,hw,t) smoothstep(hw,0.0,abs(p-(t)))','void main(){','  vec2 uv=gl_FragCoord.xy/iResolution.xy;','  vec2 sp=(gl_FragCoord.xy-iResolution.xy/2.0)/iResolution.x*2.0*sc;','  float hf=1.0-(cos(uv.x*6.28)*0.5+0.5);','  float vf=1.0-(cos(uv.y*6.28)*0.5+0.5);','  sp.y+=rnd(sp.x*0.5+iTime*S*0.2)*hf*1.5;','  sp.x+=rnd(sp.y*0.5+iTime*S*0.2+2.0)*hf;','  vec4 lines=vec4(0.0);','  for(int l=0;l<16;l++){','    float nli=float(l)/16.0;float op=float(l)+sp.x*0.5;','    float rr=rnd(op+iTime*S*1.33)*0.5+0.5;','    float hw=mix(0.01,0.18,rr*hf)/2.0;','    float off=rnd(op+iTime*S*1.33*(1.0+nli))*mix(0.6,2.0,hf);','    float lpos=py(sp.x,hf,off);','    float ln=sm(lpos,hw,sp.y)/2.0+cr(lpos,hw*0.15,sp.y);','    float cx=mod(float(l)+iTime*S,25.0)-12.0;','    float cd=length(sp-vec2(cx,py(cx,hf,off)));','    ln+=smoothstep(0.01+0.015,0.01,cd)*4.0;','    lines+=ln*mix(lc,vec4(0.6,0.8,1.0,1.0),rr*0.25)*rr;','  }','  vec4 col=mix(vec4(0.01,0.02,0.07,1.0),vec4(0.02,0.04,0.12,1.0),uv.x)*vf;','  col.a=1.0; col+=lines;','  gl_FragColor=col;}'].join('\n');
    function mk(src,type){var s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);return gl.getShaderParameter(s,gl.COMPILE_STATUS)?s:null;}
    var vs=mk(VS,gl.VERTEX_SHADER),fs=mk(FS,gl.FRAGMENT_SHADER);
    if(!vs||!fs){canvas.remove();return;}
    var prog=gl.createProgram();gl.attachShader(prog,vs);gl.attachShader(prog,fs);gl.linkProgram(prog);
    if(!gl.getProgramParameter(prog,gl.LINK_STATUS)){canvas.remove();return;}
    gl.useProgram(prog);
    var buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
    var pl=gl.getAttribLocation(prog,'aVertexPosition');
    gl.enableVertexAttribArray(pl);gl.vertexAttribPointer(pl,2,gl.FLOAT,false,0,0);
    var uT=gl.getUniformLocation(prog,'iTime'),uR=gl.getUniformLocation(prog,'iResolution');
    var t0=performance.now(),paused=false;
    document.addEventListener('visibilitychange',function(){paused=document.hidden;});
    // ── Resolution ladder ──────────────────────────────────────────────────
    // Now that no panel uses backdrop-filter, the background no longer forces ~25
    // frosted surfaces to re-blur every frame, so it can afford to be sharp. It
    // renders at device-pixel resolution, capped on the long edge by the ladder
    // below. If the GPU cannot hold the frame budget we step DOWN one rung and stay
    // there — never back up, so it can't oscillate. A fast machine sits on the top
    // rung; a loaded Pi settles wherever it is comfortable.
    // Long-edge caps in device pixels. 4096 covers a 3024 px Retina panel at DPR 2 with no
    // upscaling; the lower rungs exist for this host's own screen and loaded machines.
    var CAPS=[4096,3072,2048,1536,1152,864], capIndex=0, badWindows=0, cleanSince=0;
    var dpr=Math.min(window.devicePixelRatio||1,2);
    function resize(){
      var w=window.innerWidth*dpr,h=window.innerHeight*dpr;
      var m=Math.max(w,h),cap=CAPS[capIndex];
      if(m>cap){var k=cap/m;w*=k;h*=k;}
      canvas.width=Math.max(2,Math.round(w));
      canvas.height=Math.max(2,Math.round(h));
      gl.viewport(0,0,canvas.width,canvas.height);
    }
    window.addEventListener('resize',resize,{passive:true});
    resize();
    var _last=0,slow=0,drawn=0,TARGET=FRAME_INTERVAL,fastestGap=1000/60;
    (function frame(ts){
      if(!attached(canvas))return;         // settings toggled it off -> stop for good
      requestAnimationFrame(frame);
      if(paused||reduceMotion()){_last=0;return;}
      if(ts&&ts-_last<TARGET-0.75)return;       // cap at 144 fps on high-refresh panels
      var frameGap=_last?ts-_last:0;
      _last=ts||0;
      var t1=performance.now();
      gl.uniform1f(uT,(t1-t0)/1000);
      gl.uniform2f(uR,canvas.width,canvas.height);
      gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
      // Adaptive guard. Ignore the first 30 frames (shader/driver warm-up), then drop
      // a rung if a quarter of the sampled frames blow the budget.
      drawn++;
      if(drawn>30){
        // GPU commands are asynchronous: use delivered frame spacing, not submission time.
        if(frameGap>=TARGET-0.75)fastestGap=Math.min(fastestGap,frameGap);
        if(frameGap>Math.max(TARGET,fastestGap)*1.35+1&&frameGap<250)slow++;
        if(drawn%40===0){
          // Step down only after two consecutive windows with 40 % slow frames (a route change or
          // a Plotly burst alone must not lower the background for the rest of the session), and
          // step back up after 15 s of clean windows so a transient never leaves it pixelated.
          if(slow>16){badWindows++;cleanSince=0;}else{badWindows=0;if(slow<=2){if(!cleanSince)cleanSince=ts;}else cleanSince=0;}
          if(badWindows>=2&&capIndex<CAPS.length-1){capIndex++;resize();badWindows=0;cleanSince=0;}
          else if(cleanSince&&ts-cleanSince>15000&&capIndex>0){capIndex--;resize();cleanSince=0;}
          slow=0;
        }
      }
    })();
  }

  // ── NVTRA mascot: wireframe sphere on a 2D canvas, no libraries ────────────
  function bootMascot(){
    var canvas=document.getElementById('nvtra-mascot-canvas');
    if(!canvas||canvas.dataset.mInit==='1')return;
    canvas.dataset.mInit='1';
    var ctx=canvas.getContext('2d');if(!ctx)return;
    var dpr=Math.min(window.devicePixelRatio||1,1.5);
    function size(){
      var w=canvas.clientWidth||300,h=canvas.clientHeight||300;
      canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    }
    size();
    var LAT=6,LON=14,grid=[];
    for(var i=0;i<=LAT;i++){
      var th=Math.PI*i/LAT,row=[];
      for(var j=0;j<LON;j++){
        var ph=2*Math.PI*j/LON;
        row.push([Math.sin(th)*Math.cos(ph),Math.cos(th),Math.sin(th)*Math.sin(ph)]);
      }
      grid.push(row);
    }
    var ay=0,ax=0.42,_last=0,FPS=144,paused=false;
    document.addEventListener('visibilitychange',function(){paused=document.hidden;});
    (function frame(ts){
      // Detached (route change) -> stop permanently and let it re-init on return.
      if(!attached(canvas)){canvas.dataset.mInit='0';return;}
      requestAnimationFrame(frame);
      if(paused||reduceMotion())return;
      if(ts&&ts-_last<1000/FPS-0.75)return;
      var frameDt=_last?Math.min(50,ts-_last):1000/FPS;_last=ts||0;
      if(canvas.clientWidth>0&&Math.abs(canvas.width-Math.round(canvas.clientWidth*dpr))>4)size();
      var w=canvas.width,h=canvas.height;if(!w||!h)return;
      ay+=.006*(frameDt/(1000/30));
      var cx=w/2,cy=h/2,scale=Math.min(w,h)*0.33;
      var cY=Math.cos(ay),sY=Math.sin(ay),cX=Math.cos(ax),sX=Math.sin(ax);
      var TH=i3Theme();
      // 'lighter' additively blends toward white, which is correct over the dark
      // shell but erases the sphere against a light panel.
      ctx.clearRect(0,0,w,h);
      ctx.globalCompositeOperation=TH.light?'source-over':'lighter';
      function proj(p){
        var x=p[0],y=p[1],z=p[2];
        var x1=x*cY-z*sY,z1=x*sY+z*cY;
        var y1=y*cX-z1*sX,z2=y*sX+z1*cX;
        var d=2.6/(2.6+z2);
        return [cx+x1*d*scale,cy-y1*d*scale,z2];
      }
      var P=grid.map(function(r){return r.map(proj);});
      // Light mode needs both a darker ink and a higher floor alpha, or the wire
      // sphere disappears into the white panel entirely.
      var edgeBase=TH.light?0.22:0.12, edgeSpan=TH.light?0.50:0.44;
      function edge(a,b){
        var depth=(a[2]+b[2])/2,al=edgeBase+edgeSpan*(1-(depth+1)/2);
        ctx.strokeStyle='rgba('+TH.accent+','+al.toFixed(3)+')';
        ctx.lineWidth=1.0*dpr;ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();
      }
      for(var i=0;i<=LAT;i++){
        for(var j=0;j<LON;j++){
          var a=P[i][j];
          edge(a,P[i][(j+1)%LON]);
          if(i<LAT)edge(a,P[i+1][j]);
        }
      }
      var g=ctx.createRadialGradient(cx,cy,0,cx,cy,scale*0.55);
      g.addColorStop(0,'rgba('+TH.accent+',0.45)');
      g.addColorStop(0.6,'rgba('+TH.accent2+',0.12)');
      g.addColorStop(1,'rgba('+TH.accent+',0)');
      ctx.fillStyle=g;ctx.beginPath();ctx.arc(cx,cy,scale*0.55,0,7);ctx.fill();
      ctx.globalCompositeOperation='source-over';
    })();
  }

  // ── NVTRA Siri-wave WebGL loader ─────────────────────────────────────────
  function bootNvtraLoader(){
    var canvas=document.getElementById('nvtra-loader-canvas');
    if(!canvas||canvas.dataset.waveInit==='1')return;
    canvas.dataset.waveInit='1';
    var gl=canvas.getContext('webgl',{alpha:false,antialias:false});if(!gl)return;
    var vertex='attribute vec2 aPos;void main(){gl_Position=vec4(aPos,0.,1.);}';
    var fragment=`precision highp float;
uniform vec2 iResolution;uniform float iTime;
const float PI=3.14159265359;
vec3 density4(int s){float x=float(s);return clamp(vec3(abs(x-3.)-1.,2.-abs(x-2.),2.-abs(x-4.)),0.,1.);}
void main(){
 vec2 R=iResolution.xy;float aspect=R.x/R.y;
 vec2 p=(gl_FragCoord.xy+.5)*2./R-1.;p.x*=aspect;float yScreen=p.y;p/=.6;
 float t=iTime,low=clamp(.45+.45*sin(t*.8)*sin(t*.37+1.),0.,1.);
 float mid=clamp(.4+.4*sin(t*1.7+2.)*sin(t*.53),0.,1.);
 float high=clamp(.3+.3*sin(t*2.9+4.)*sin(t*.71+2.),0.,1.);
 float drift=mod(t,20.*PI)*2.4,xN=p.x/max(aspect,1.);
 float env=cos(PI*.5*min(abs(.9*xN),1.));env*=env;
 float A1=.32+.01*low*6.,A2=A1+mid*.05+high*.06,AB=2.6+mid*.8+high*.5;
 float th=.03,inten=.01*(2.+low*1.5),soft=.01*(2.5+mid*.4);
 float yMain=A1*env*sin(p.x*1.1+drift);vec3 num=vec3(0.),den=vec3(0.);
 for(int s=0;s<4;s++){
  vec3 hue=density4(s);den+=hue;float ab=mix(-AB,AB,float(s)/3.);
  float yL=A2*env*sin(p.x+drift+ab),d=abs(p.y-yL);
  float line=inten/(sqrt(d*d+soft*soft)+th);
  float lo=min(yMain,yL),hi=max(yMain,yL),dBand=max(0.,max(p.y-hi,lo-p.y));
  num+=hue*(line+.0001*30000.*inten/(dBand+.08));
 }
 vec3 col=num/max(den,vec3(.001));float dM=abs(p.y-yMain);
 col+=.5*inten/(sqrt(dM*dM+soft*soft)+th);col=pow(max(col,0.),vec3(1.5));
 float emT=clamp((abs(yScreen)-1.)/-.4,0.,1.),em=emT*emT*(3.-2.*emT);
 col*=em*exp(-pow(xN*1.7,2.));gl_FragColor=vec4(col,1.);
}`;
    function shader(type,source){var s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){gl.deleteShader(s);return null;}return s;}
    var vs=shader(gl.VERTEX_SHADER,vertex),fs=shader(gl.FRAGMENT_SHADER,fragment);if(!vs||!fs)return;
    var program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);gl.useProgram(program);
    var buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    var pos=gl.getAttribLocation(program,'aPos');gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);
    var uR=gl.getUniformLocation(program,'iResolution'),uT=gl.getUniformLocation(program,'iTime'),start=performance.now(),last=0;
    function resize(){var side=Math.max(180,Math.min(360,canvas.clientWidth||360));var dim=Math.round(side*.65);if(canvas.width!==dim){canvas.width=dim;canvas.height=dim;gl.viewport(0,0,dim,dim);}}
    (function frame(now){
      var wrap=document.getElementById('nvtra-spline-loading');
      if(!attached(canvas)||!wrap||wrap.style.display==='none'){canvas.dataset.waveInit='0';return;}
      requestAnimationFrame(frame);if(document.hidden||reduceMotion()||now-last<FRAME_INTERVAL-0.75)return;last=now;
      resize();gl.uniform2f(uR,canvas.width,canvas.height);gl.uniform1f(uT,(now-start)/1000);gl.drawArrays(gl.TRIANGLES,0,3);
    })(performance.now());
  }

  // ── NVTRA Spline robot ───────────────────────────────────────────────────
  function bootSplineRobot(){
    var host=document.getElementById('nvtra-spline-host');
    var canvas=document.getElementById('nvtra-spline-canvas');
    if(!host||!canvas||host.dataset.splineInit==='1')return;
    host.dataset.splineInit='1';
    var loading=document.getElementById('nvtra-spline-loading');
    bootNvtraLoader();
    var revealRobot=function(){
      if(!loading)return;loading.style.opacity='0';
      setTimeout(function(){if(loading)loading.style.display='none';},360);
    };
    // The published Spline scene binds its look-at handlers to the WINDOW, so the
    // robot's head tracked the cursor across every panel on the page - it read as
    // the machine watching you rather than as one exhibit among many. Confine it:
    // while the app registers its listeners we wrap any pointer-move handler so it
    // only fires when the cursor is actually inside the robot's own panel. The
    // scene keeps its idle animation everywhere else.
    var TRACK_EVENTS={mousemove:1,pointermove:1,touchmove:1};
    function confinePointerTracking(register){
      var patched=[],flag={on:true};
      [window,document].forEach(function(target){
        var original=target.addEventListener;
        patched.push([target,original]);
        target.addEventListener=function(type,handler,options){
          if(flag.on&&TRACK_EVENTS[type]&&typeof handler==='function'){
            var wrapped=function(event){
              var t=event&&event.target;
              if(t&&t.nodeType===1&&!host.contains(t))return;
              return handler.call(this,event);
            };
            return original.call(target,type,wrapped,options);
          }
          return original.call(target,type,handler,options);
        };
      });
      function restore(){
        flag.on=false;
        patched.forEach(function(pair){pair[0].addEventListener=pair[1];});
      }
      try{return register();}finally{
        // Listeners are added synchronously by the constructor and again as the
        // scene finishes loading, so hold the patch across that second pass.
        setTimeout(restore,8000);
      }
    }

    function startRobot(){
      var Application=window.__NvtraSplineApplication;
      if(!Application)return false;
      try{
        var app=confinePointerTracking(function(){
          return new Application(canvas,{wasmPath:'/_i3'});
        });
        host.__splineApp=app;
        Promise.resolve(app.load('/_i3/nvtra-robot.splinecode'))
          .then(function(){
            try{app.addEventListener('mouseDown',function(event){
              var part=event&&event.target,name=String(part&&part.name||'').toLowerCase();if(!part||!part.rotation)return;
              var base={x:part.rotation.x,y:part.rotation.y,z:part.rotation.z};
              if(/head|neck/.test(name))part.rotation.y=base.y+.28;
              else if(/arm|hand|elbow/.test(name))part.rotation.z=base.z-.38;
              else if(/leg|shin|foot/.test(name))part.rotation.x=base.x+.24;
              else part.rotation.y=base.y+.16;
              setTimeout(function(){if(part&&part.rotation){part.rotation.x=base.x;part.rotation.y=base.y;part.rotation.z=base.z;}},520);
            });}catch(error){}
            revealRobot();
          })
          .catch(function(error){
            console.error('[studio] NVTRA robot scene failed',error);
            revealRobot();
          });
        setTimeout(revealRobot,10000);
      }catch(error){
        console.error('[studio] NVTRA robot failed to start',error);
        revealRobot();
      }
      return true;
    }
    if(!startRobot()){
      window.addEventListener('nvtra-spline-runtime-ready',startRobot,{once:true});
      import('/_i3/spline-runtime.js').then(function(module){
        window.__NvtraSplineApplication=module.Application;
        startRobot();
      }).catch(function(error){
        console.error('[studio] NVTRA runtime failed to import',error);
        revealRobot();
      });
    }
  }

  // ── persistent chrome: these live outside #page-content, so ONCE is enough ──
  function bootAlertStack(){
    if(window.__alertStackInited)return;
    var trigger=document.getElementById('nvtra-alert-trigger');
    var stack=document.getElementById('nvtra-alert-stack');
    if(!trigger||!stack)return;
    window.__alertStackInited=true;
    var lastText='';
    new MutationObserver(function(){
      var clean=(trigger.textContent||'').trim().replace(/\|\d+$/,'').trim();
      if(!clean||clean===lastText)return;
      lastText=clean;
      var el=document.createElement('div');
      el.className='nvtra-alert-item';el.textContent=clean;
      stack.appendChild(el);
      setTimeout(function(){if(el.parentNode)el.parentNode.removeChild(el);},5400);
    }).observe(trigger,{childList:true,subtree:true,characterData:true});
  }

  function bootTypewriter(){
    var el=document.getElementById('typewriter-text');
    if(!el){
      clearTimeout(window.__typewriterBootTimer);
      window.__typewriterBootTimer=setTimeout(bootTypewriter,50);
      return;
    }
    if(el.dataset.twInited==='1')return;
    clearTimeout(window.__typewriterBootTimer);
    el.dataset.twInited='1';
    var phrases=[
      'Enter your text here',
      'MTDI framework',
      'Induction. Interference. Intelligence.',
      'Title',
      'Heading 1',
      'Heading 2',
      'Text'
    ];
    var pi=0,ci=0,del=false,pause=0;
    function tick(){
      if(!attached(el))return;
      if(reduceMotion()){el.textContent=phrases[0];setTimeout(tick,2000);return;}
      var ph=phrases[pi];
      if(!del){
        ci++;el.textContent=ph.slice(0,ci);
        if(ci===ph.length){del=true;pause=38;}
        setTimeout(tick,55);
      }else{
        if(pause>0){pause--;setTimeout(tick,40);return;}
        ci--;el.textContent=ph.slice(0,ci);
        if(ci===0){del=false;pi=(pi+1)%phrases.length;setTimeout(tick,300);}
        else setTimeout(tick,28);
      }
    }
    setTimeout(tick,800);
  }

  // Settings segment buttons reflect the SAVED choice. Bound once; the class sync is
  // cheap and safe to call after a route change.
  function syncSettingsSeg(){
    var a;
    try{a=localStorage.getItem('i3-anim')||'on';}
    catch(e){a='on';}
    var m={'anim-on':a!=='off','anim-off':a==='off'};
    Object.keys(m).forEach(function(id){
      var el=document.getElementById(id);if(!el)return;
      el.classList.toggle('seg-active',m[id]);
      if(!el.dataset.segArmed){
        el.dataset.segArmed='1';
        el.addEventListener('click',function(){setTimeout(syncSettingsSeg,120);});
      }
    });
  }

  // Plotly can mount while an EM sub-view is still width:0. Resize it after the
  // view becomes visible instead of waiting for the user's first click.
  function resizeVisiblePlots(){
    if(!window.Plotly||!window.Plotly.Plots||!window.Plotly.Plots.resize)return;
    document.querySelectorAll('#page-content .js-plotly-plot').forEach(function(plot){
      var r=plot.getBoundingClientRect();
      if(r.width>20&&r.height>20){
        try{window.Plotly.Plots.resize(plot);}catch(e){}
      }
    });
  }
  function schedulePlotResize(){
    [0,60,180,420].forEach(function(delay){setTimeout(resizeVisiblePlots,delay);});
  }

  // ── Shared orbit fitting ──────────────────────────────────────────────────
  // Both orbits used to clamp with Math.max(FLOOR, fit…), which let the floor win
  // over the fit: once the scene got narrow the radius stopped shrinking and the
  // cards were pushed back over the core and over each other. This solves for a
  // radius that satisfies BOTH constraints at once —
  //    outer: the whole card stays inside the scene box
  //    inner: the card stays clear of the centre core
  // — shrinking the cards up to 42% before conceding. `null` means no overlap-free
  // orbit exists at this size, and the caller falls back to a plain grid, which is
  // what a phone wants anyway.
  function orbitFit(o){
    var GAP=16;
    var vw=Math.max(240,Math.min(o.sceneW||innerWidth,innerWidth));
    var vh=Math.max(240,o.sceneH||480);
    for(var s=(o.scale||1); s>=0.58; s-=0.06){
      var halfW=o.cardW*s/2, halfH=o.cardH*s/2;
      var maxR=Math.min(vw/2-halfW-GAP, vh/2-halfH-GAP);
      var minR=o.coreR+halfH+GAP;
      if(maxR>=minR) return {r:Math.max(minR,Math.min(maxR,o.ideal)),scale:s};
    }
    return null;
  }

  // ── HOME: upright four-module orbit at one constant speed ─────────────────
  function armHomeOrbit(){
    var stage=document.getElementById('home-module-orbit-stage');
    if(!stage||stage.dataset.homeOrbit==='1')return;
    var cards=[].slice.call(stage.querySelectorAll('.home-module-orbit-card'));
    var ring=stage.parentElement&&stage.parentElement.querySelector('.mtdi-orbit-ring-v2');
    if(cards.length!==4||!ring)return;
    stage.dataset.homeOrbit='1';
    var angle=-Math.PI/2,last=performance.now(),lastPaint=0,alive=true;
    var radiusNow=260;

    var cardScale=1,wasLinear=null;
    function geometry(){
      var mobile=innerWidth<=760;
      var scene=stage.parentElement;
      var fit=orbitFit({
        sceneW:(scene&&scene.clientWidth)||innerWidth,
        sceneH:(scene&&scene.clientHeight)||(mobile?560:940),
        cardW:mobile?154:300, cardH:mobile?130:200,
        coreR:(mobile?140:350)/2,
        ideal:mobile?148:360});
      if(!fit){radiusNow=null;return null;}
      radiusNow=fit.r; cardScale=fit.scale;
      ring.style.setProperty('--orbit-diameter',(fit.r*2)+'px');
      return fit.r;
    }
    function setLinear(scene,on){
      if(wasLinear===on)return;
      wasLinear=on;
      if(scene)scene.classList.toggle('is-linear',on);
      if(on)for(var j=0;j<cards.length;j++){
        cards[j].style.transform='';cards[j].style.zIndex='';cards[j].style.opacity='';
      }
    }
    function paint(){
      if(!attached(stage))return;
      var scene=stage.parentElement;
      var radius=geometry();
      if(radius===null){setLinear(scene,true);return;}
      setLinear(scene,false);
      for(var i=0;i<cards.length;i++){
        var theta=angle+i*(Math.PI*2/cards.length);
        var x=Math.cos(theta)*radius,y=Math.sin(theta)*radius;
        var depth=(Math.sin(theta)+1)/2;
        cards[i].style.transform='translate3d('+x.toFixed(2)+'px,'+y.toFixed(2)+'px,0) scale('+cardScale.toFixed(3)+')';
        cards[i].style.zIndex=String(Math.round(10+depth*20));
        cards[i].style.opacity=String(.80+depth*.20);
      }
    }
    function resized(){paint();}
    addEventListener('resize',resized,{passive:true});
    paint();
    (function tick(now){
      if(!alive||!attached(stage)){
        alive=false;
        removeEventListener('resize',resized);return;
      }
      requestAnimationFrame(tick);
      if(document.hidden){last=now;return;}
      if(now-lastPaint<FRAME_INTERVAL-0.75)return;
      var dt=Math.min(64,now-last);last=now;lastPaint=now;
      angle=(angle+dt*.000075)%(Math.PI*2);paint();
    })(performance.now());
  }

  // Mac-only, opt-in hand tracking. Triple-clicking either supported canvas is
  // the user gesture that requests the camera; no frames leave the browser.
  function registerMacHandZoom(canvas,controls){
    if(!canvas||!/Macintosh|Mac OS X/.test(navigator.userAgent||''))return;
    canvas.title=(canvas.title?canvas.title+' · ':'')+'Triple-click for camera hand zoom';
    canvas.addEventListener('click',function(event){
      if(event.detail!==3)return;
      event.preventDefault();event.stopPropagation();
      startMacHandVision(canvas,controls);
    });
  }
  function handVisionStatus(text,state){
    var el=document.getElementById('i3-hand-vision-status');
    if(!el){el=document.createElement('div');el.id='i3-hand-vision-status';el.className='i3-hand-vision-status';document.body.appendChild(el);}
    el.className='i3-hand-vision-status'+(state?' '+state:'');el.textContent=text;
    /* status is a notice, not a fixture: errors linger 8 s, everything else 4 s, then fade */
    clearTimeout(el.__i3Fade);el.__i3Fade=setTimeout(function(){el.classList.add('i3-fade');},state==='error'?8000:4000);
  }
  function loadExternalScript(src){
    return new Promise(function(resolve,reject){
      var found=document.querySelector('script[src="'+src+'"]');
      if(found){if(found.dataset.ready==='1')resolve();else found.addEventListener('load',resolve,{once:true});return;}
      var script=document.createElement('script');script.src=src;script.crossOrigin='anonymous';
      script.onload=function(){script.dataset.ready='1';resolve();};script.onerror=reject;document.head.appendChild(script);
    });
  }
  async function startMacHandVision(canvas,controls){
    if(window.__i3HandVisionRunning){window.__i3HandControls=controls;handVisionStatus('HAND VISION · TARGET CHANGED','live');return;}
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
      handVisionStatus('CAMERA BLOCKED · USE HTTPS OR A LOCALHOST CONNECTION','error');return;
    }
    window.__i3HandControls=controls;handVisionStatus('REQUESTING CAMERA PERMISSION','');
    try{
      await loadExternalScript('https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js');
      window.__i3HandVisionStarting=true;var cancelled=false;
      var stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:640},height:{ideal:480}},audio:false});
      // The camera can be switched off while the hand model is still loading: release the
      // stream at once instead of leaving the light on until the model arrives.
      window.__i3StopHandVision=function(){cancelled=true;window.__i3HandVisionStarting=false;window.__i3HandVisionRunning=false;try{stream.getTracks().forEach(function(t){t.stop();});}catch(e){}try{if(preview)preview.remove();}catch(e){}try{document.removeEventListener('visibilitychange',onVisible);window.removeEventListener('focus',onVisible);window.removeEventListener('pageshow',onVisible);}catch(e){}handVisionStatus('CAMERA OFF','');};
      if(cancelled){stream.getTracks().forEach(function(t){t.stop();});return;}
      var preview=document.createElement('div');preview.className='i3-hand-vision-preview';
      var video=document.createElement('video');video.className='i3-hand-vision-video';video.autoplay=true;video.muted=true;video.playsInline=true;video.srcObject=stream;
      var overlay=document.createElement('canvas');overlay.className='i3-hand-vision-overlay';overlay.width=640;overlay.height=480;
      preview.appendChild(video);preview.appendChild(overlay);document.body.appendChild(preview);await video.play();
      var hands=new Hands({locateFile:function(file){return 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/'+file;}});
      hands.setOptions({maxNumHands:2,modelComplexity:0,minDetectionConfidence:.55,minTrackingConfidence:.55});
      var smoothed=1,busy=false,lastSent=0,lastPalmX=null,lastPalmY=null,twoHandReference=null;
      // Watchdog state: the solution can go quiet without an error (a lost WebGL context
      // when the page opens many 3D plots, a suspended tab, a camera taken by another app).
      var lastResultAt=performance.now(),sendErrors=0,rebuiltAt=0,resultsHandler=null;
      // The camera stream is kept alive independently of hand CONTROL. Control is
      // "armed" separately, so a dropped camera, a backgrounded tab or another app
      // taking the device costs you the gesture, not the whole session: raise a hand
      // to your head and it comes back without reaching for the mouse.
      var armed=true,headSince=0,lastArmAt=0,reacquiring=false,reacquireAt=0;
      window.__i3HandArmed=function(){return armed;};
      window.__i3HandArm=function(on){armed=!!on;lastArmAt=performance.now();};
      var links=[[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
      function fingerCount(hand){
        var count=0,w=hand[0],tips=[4,8,12,16,20],joints=[3,6,10,14,18];
        for(var i=0;i<tips.length;i++){
          var td=Math.hypot(hand[tips[i]].x-w.x,hand[tips[i]].y-w.y);
          var jd=Math.hypot(hand[joints[i]].x-w.x,hand[joints[i]].y-w.y);
          if(td>jd*1.16)count++;
        }
        return count;
      }
      function paintHands(sets){
        var oc=overlay.getContext('2d');oc.clearRect(0,0,overlay.width,overlay.height);oc.lineWidth=3;oc.strokeStyle='rgba(0,229,255,.9)';oc.fillStyle='#ffca28';
        sets.forEach(function(hand){
          links.forEach(function(pair){oc.beginPath();oc.moveTo(hand[pair[0]].x*640,hand[pair[0]].y*480);oc.lineTo(hand[pair[1]].x*640,hand[pair[1]].y*480);oc.stroke();});
          hand.forEach(function(point){oc.beginPath();oc.arc(point.x*640,point.y*480,4,0,Math.PI*2);oc.fill();});
        });
      }
      resultsHandler=function(results){
        lastResultAt=performance.now();sendErrors=0;
        var sets=results.multiHandLandmarks||[];paintHands(sets);
        if(!sets.length){lastPalmX=null;lastPalmY=null;twoHandReference=null;headSince=0;
          handVisionStatus(armed?'HAND VISION LIVE \u00b7 SHOW YOUR HAND':'HAND CONTROL PAUSED \u00b7 RAISE A HAND TO YOUR HEAD','live');return;}
        var hand=sets[0],palmX=(hand[0].x+hand[5].x+hand[9].x+hand[13].x+hand[17].x)/5;
        // Hand-at-head: on a laptop camera at eye level your head occupies the top of
        // the frame, so a hand held up there is the unambiguous "resume" signal. It has
        // to be held, or an ordinary wave past the top edge would trigger it.
        var palmY=(hand[0].y+hand[9].y+hand[13].y)/3;
        var atHead=palmY<0.34;
        if(atHead){
          if(!headSince)headSince=lastResultAt;
          var held=lastResultAt-headSince;
          if(!armed&&held>600&&lastResultAt-lastArmAt>900){
            armed=true;lastArmAt=lastResultAt;lastPalmX=null;lastPalmY=null;twoHandReference=null;
            handVisionStatus('HAND CONTROL RESUMED \u00b7 HAND AT HEAD','live');
          }else if(!armed){
            handVisionStatus('HOLD \u00b7 RESUMING HAND CONTROL','');
          }
        }else headSince=0;
        if(!armed){lastPalmX=null;lastPalmY=null;twoHandReference=null;return;}
        if(sets.length>=2){
          var other=sets[1],otherPalmX=(other[0].x+other[5].x+other[9].x+other[13].x+other[17].x)/5;
          palmX=(palmX+otherPalmX)/2;
        }
        // Both axes. The preview is mirrored, so horizontal travel is negated and
        // vertical is not; sending only dx is why up/down never moved anything.
        var palmYc=(hand[0].y+hand[5].y+hand[9].y+hand[13].y+hand[17].y)/5;
        if(sets.length>=2){
          var oth=sets[1],oy=(oth[0].y+oth[5].y+oth[9].y+oth[13].y+oth[17].y)/5;
          palmYc=(palmYc+oy)/2;
        }
        if(lastPalmX!==null&&window.__i3HandControls&&window.__i3HandControls.rotate){
          var visibleDx=-(palmX-lastPalmX),visibleDy=(palmYc-lastPalmY);
          if(Math.abs(visibleDx)<.002)visibleDx=0;
          if(Math.abs(visibleDy)<.002)visibleDy=0;
          if(visibleDx||visibleDy)window.__i3HandControls.rotate(visibleDx,visibleDy);
        }
        lastPalmX=palmX;lastPalmY=palmYc;
        if(sets.length>=2){
          var pa=sets[0][9],pb=sets[1][9],distance=Math.hypot(pa.x-pb.x,pa.y-pb.y);
          if(twoHandReference===null)twoHandReference=Math.max(.04,distance);
          var continuousZoom=Math.max(.58,Math.min(1.65,distance/twoHandReference));
          smoothed+=.22*(continuousZoom-smoothed);
          if(window.__i3HandControls&&window.__i3HandControls.zoom)window.__i3HandControls.zoom(smoothed);
          handVisionStatus('TWO-HAND ZOOM · SPREAD OUT OR MOVE TOGETHER','live');
        }else{
          twoHandReference=null;
          var fingers=fingerCount(hand),goal=fingers<=1?.66:(fingers>=4?1.34:smoothed);
          smoothed+=.20*(goal-smoothed);
          if(window.__i3HandControls&&window.__i3HandControls.zoom)window.__i3HandControls.zoom(smoothed);
          handVisionStatus('ONE HAND · '+fingers+' FINGERS · MOVE TO ROTATE','live');
        }
      };
      hands.onResults(resultsHandler);
      if(cancelled){try{hands.close();}catch(e){}return;}
      window.__i3HandVisionStarting=false;
      window.__i3HandVisionRunning=true;
      function rebuildHands(reason){
        if(performance.now()-rebuiltAt<5000)return;rebuiltAt=performance.now();
        try{hands.close();}catch(e){}
        try{
          hands=new Hands({locateFile:function(file){return window.__i3HandModelUrl?window.__i3HandModelUrl(file):'https://cdn.jsdelivr.net/npm/@mediapipe/hands/'+file;}});
          hands.setOptions(window.__i3HandOptions||{maxNumHands:2,modelComplexity:0,minDetectionConfidence:.55,minTrackingConfidence:.55});
          hands.onResults(resultsHandler);
          lastResultAt=performance.now();sendErrors=0;busy=false;
          handVisionStatus('HAND VISION RESTARTED · '+reason,'');
          console.warn('[studio] hand vision restarted: '+reason);
        }catch(e){console.error('[studio] hand vision rebuild failed',e);}
      }
      // A camera track that ends (sleep, another app, unplugged) is re-requested instead of
      // leaving the loop sending frames from a dead video element.
      function watchTrack(track){
        // A track can die three ways: it ENDS (unplugged, another app claimed it), it is
        // MUTED (macOS/Safari suspend a backgrounded tab's camera without ending it), or
        // it stays live while the <video> is paused. All three look identical to the
        // frame loop, so all three are handled here rather than in the watchdog.
        track.addEventListener('ended',function(){reacquireCamera('camera ended');});
        track.addEventListener('mute',function(){
          if(!window.__i3HandVisionRunning)return;
          handVisionStatus('CAMERA SUSPENDED \u00b7 WILL RESUME','');
        });
        track.addEventListener('unmute',function(){
          if(!window.__i3HandVisionRunning)return;
          video.play().catch(function(){});
          lastResultAt=performance.now();
          handVisionStatus(armed?'CAMERA BACK \u00b7 HAND VISION LIVE':'CAMERA BACK \u00b7 RAISE A HAND TO YOUR HEAD','live');
        });
      }
      stream.getVideoTracks().forEach(watchTrack);
      async function reacquireCamera(reason){
        if(!window.__i3HandVisionRunning||reacquiring)return;
        if(performance.now()-reacquireAt<2500)return;
        reacquiring=true;reacquireAt=performance.now();
        handVisionStatus('CAMERA LOST \u00b7 RECONNECTING','error');
        try{
          try{stream.getTracks().forEach(function(t){t.stop();});}catch(e){}
          var again=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:640},height:{ideal:480}},audio:false});
          stream=again;video.srcObject=again;again.getVideoTracks().forEach(watchTrack);
          await video.play();
          rebuildHands('camera reconnected: '+reason);
          // Control is deliberately left disarmed after a reconnect. The operator asks
          // for it back with the gesture, so a camera that flickers cannot silently
          // start spinning a 3D object while they are doing something else.
          armed=false;headSince=0;lastArmAt=performance.now();
          handVisionStatus('CAMERA BACK \u00b7 RAISE A HAND TO YOUR HEAD','live');
        }catch(e){
          handVisionStatus('CAMERA LOST \u00b7 TURN IT ON AGAIN','error');
        }finally{reacquiring=false;}
      }
      // Returning from another app: the tab was frozen, the video paused and the track
      // may have been suspended. Resume deliberately instead of waiting for the loop to
      // notice, which is what used to leave the camera dead after a long switch away.
      function onVisible(){
        if(!window.__i3HandVisionRunning||document.hidden)return;
        lastResultAt=performance.now();
        var live=stream.getVideoTracks().filter(function(t){return t.readyState==='live';});
        if(!live.length){reacquireCamera('no live track after app switch');return;}
        if(video.paused)video.play().catch(function(){reacquireCamera('video would not resume');});
        if(live.some(function(t){return t.muted;}))handVisionStatus('CAMERA SUSPENDED \u00b7 WILL RESUME','');
        requestAnimationFrame(frame);
      }
      document.addEventListener('visibilitychange',onVisible);
      window.addEventListener('focus',onVisible);
      window.addEventListener('pageshow',onVisible);
      async function frame(now){
        if(!window.__i3HandVisionRunning)return;
        requestAnimationFrame(frame);if(busy&&now-lastSent>4000)busy=false;
        if(!document.hidden&&now-lastResultAt>3500){
          var tracks=stream.getVideoTracks();
          var dead=!tracks.length||tracks.every(function(t){return t.readyState!=='live';});
          var asleep=tracks.some(function(t){return t.muted;})||video.paused;
          // A dead track needs a new camera; a merely paused/suspended one needs a nudge;
          // only a genuinely stuck model is worth tearing down and rebuilding.
          if(dead)reacquireCamera('track not live');
          else if(asleep){video.play().catch(function(){});lastResultAt=now;}
          else if(video.readyState>=2)rebuildHands('no results for 3.5 s');
        }
        if(busy||video.readyState<2||now-lastSent<66)return;
        busy=true;lastSent=now;try{await hands.send({image:video});}catch(error){if(++sendErrors>=3)rebuildHands('frame errors');}finally{busy=false;}
      }
      requestAnimationFrame(frame);
    }catch(error){
      window.__i3HandVisionStarting=false;
      var why=(error&&error.name)||'';var hint=why==='NotAllowedError'?'CAMERA BLOCKED · CLICK THE CAMERA ICON IN THE ADDRESS BAR AND ALLOW':why==='NotFoundError'?'NO CAMERA FOUND':why==='NotReadableError'?'CAMERA BUSY IN ANOTHER APP · CLOSE IT AND RETRY':'CAMERA OR HAND MODEL UNAVAILABLE · '+String((error&&error.message)||why).slice(0,60).toUpperCase();
      handVisionStatus(hint,'error');var res=document.getElementById('i3-control-result');if(res)res.textContent=hint;
      console.error('[studio] hand vision failed',error);
    }
  }

  // The MTDI centre uses unconstrained three-axis rotation, gentle momentum and
  // permanent directional drift. It preserves the operator's chosen orientation.
  function bootInstrumentConstellation(){
    var canvas=document.getElementById('mtdi-constellation-canvas');
    if(!canvas||canvas.dataset.galleryInit==='1')return;
    canvas.dataset.galleryInit='1';
    var ctx=canvas.getContext('2d');if(!ctx)return;
    var dpr=Math.min(devicePixelRatio||1,1.8),yaw=0,pitch=-.18,roll=0,zoom=1;
    var spinDirection=-1,baseYaw=.00016*spinDirection;
    var drag=false,lastX=0,lastY=0,startX=0,startY=0,moved=false;
    var velYaw=baseYaw,velPitch=0,velRoll=0,lastFrame=0;
    var coastUntil=0,touchGesture=null,lastTouchAt=-Infinity;
    var seed=9173;
    function random(){seed=(seed*16807)%2147483647;return(seed-1)/2147483646;}
    function wrap(v){while(v>Math.PI)v-=Math.PI*2;while(v< -Math.PI)v+=Math.PI*2;return v;}
    function limit(v){return Math.max(-.0035,Math.min(.0035,v));}
    function interact(){}
    function coast(strength){coastUntil=Math.max(coastUntil,performance.now()+Math.min(3300,420+strength*90));}
    // ── the constellation ────────────────────────────────────────────────────
    // A branching graph rather than a flat ring of cards: MTDI at the core, the
    // six pillars and the Aether layer on an inner shell, and each pillar's diagnostics on an outer
    // shell above and below it. The ids and order match MTDI_ORBIT_PILLARS, so
    // what is drawn here is the page's own structure and not a decoration.
    var GROUPS=[
      {id:'validation',text:'VALIDATION CHAMBER',color:'#a5c9fa',lat:-.32,
       children:[['connection','CONNECTION'],['freshness','FRESHNESS'],['sensor-integrity','INTEGRITY'],
                 ['host-telemetry','HOST TELEMETRY'],['uncertainty','UNCERTAINTY'],['clipping','CLIPPING'],
                 ['timing','TIMING QUALITY'],['sample-rate','SAMPLE RATE'],['calibration','CALIBRATION']]},
      {id:'environment',text:'ENVIRONMENTAL INTELLIGENCE',color:'#96d9bb',lat:.38,
       children:[['baselines','BASELINES'],['ch1-field','CHANNEL 1'],['ch2-field','CHANNEL 2'],
                 ['correlation','CORRELATION'],['ch3-sweep3','CHANNEL 3'],
                 ['noise-floor','NOISE FLOOR'],['linefreq-50hz','REFERENCE'],['harmonics-env','HARMONICS']]},
      {id:'computational',text:'COMPUTATIONAL CORE',color:'#9fe7f2',lat:.30,
       children:[['ml','MACHINE LEARNING'],['matlab','MATLAB'],['llm','LANGUAGE MODELS'],['agents','AGENTS'],
                 ['storage','STORAGE'],['voice-cc','VOICE'],['integrations','INTEGRATIONS'],['sdks','SDKS']]},
      {id:'nvtra',text:'NVTRA',color:'#e0c997',lat:-.30,
       children:[['completeness','COMPLETENESS'],['stability','STABILITY'],['trust','TRUST'],['diagnostics','DIAGNOSTICS'],
                 ['confidence','CONFIDENCE'],['consensus','CONSENSUS'],['transients','TRANSIENTS'],
                 ['anomaly','ANOMALY σ'],['events','EVENTS']]},
      {id:'i3',text:'I³',color:'#b5a0e4',lat:.34,
       children:[['induction','INDUCTION'],['interference','INTERFERENCE'],['intelligence','INTELLIGENCE'],
                 ['harmonics','HARMONICS'],['fingerprint','FINGERPRINT'],['signature','SIGNATURE'],
                 ['d4','D4 ENGINE'],['filters','FILTERS'],['trend','TREND']]},
      {id:'research',text:'RESEARCH',color:'#f2c48d',lat:.26,
       children:[['datasets','DATASETS'],['sources','SOURCES'],['licences','LICENCES'],['credits','CREDITS'],
                 ['catalogue','CATALOGUE'],['offline','OFFLINE']]},
      {id:'aether',text:'AETHER',color:'#d8a3b1',lat:-.23,
       children:[['purpose','PURPOSE'],['persistence','PERSISTENCE'],['authorship','AUTHORSHIP'],['origin','ORIGIN'],
                 ['struggle','STRUGGLE'],['obsession','OBSESSION'],['rebuilding','REBUILDING'],
                 ['soul','SOUL LAYER'],['meaning','MEANING']]}
    ];
    // Latitude is the vertical axis here, matching this canvas's projection, where
    // the supplied sketch used z. Everything else is its spherical distribution.
    function shell(lon,lat,rad){return{x:Math.cos(lon)*Math.cos(lat)*rad,
      y:Math.sin(lat)*rad,z:Math.sin(lon)*Math.cos(lat)*rad};}
    // The old plates sat out near 1.7 units; keep the same drawn size on screen.
    var SHELL=1.62;
    var core={id:'mtdi',text:'MTDI',color:'#bdefff',core:true,x:0,y:0,z:0};
    var nodes=[core],groups=[],byId={mtdi:core};
    // Every label is drawn at every size. An earlier pass hid the diagnostics when
    // the canvas was small, on the grounds that they overlapped; the author wants the
    // dense, crowded look, and the overlap IS the look - a constellation reads as
    // busy, not as five tidy words. Depth still sorts them, so the near ones cover
    // the far ones and it resolves as you rotate.
    function showChildLabels(w){return true;}
    for(var gi=0;gi<GROUPS.length;gi++){
      var g=GROUPS[gi],lon=-Math.PI/2+gi*Math.PI*2/GROUPS.length;
      var gp=shell(lon,g.lat,.80*SHELL);
      var group={id:g.id,text:g.text,color:g.color,major:true,group:g.id,
        x:gp.x,y:gp.y,z:gp.z,children:[]};
      groups.push(group);nodes.push(group);byId[g.id]=group;
      for(var ci=0;ci<g.children.length;ci++){
        var n=g.children.length;
        var band=[-.46,.46,0][ci%3],ring=1.02+(ci%3===2?.16:0);
        var cp=shell(lon+(ci-(n-1)/2)*.155,g.lat+band,ring*SHELL);
        var child={id:g.children[ci][0],text:g.children[ci][1],color:g.color,
          group:g.id,x:cp.x,y:cp.y,z:cp.z};
        group.children.push(child);nodes.push(child);byId[child.id]=child;
      }
    }
    // A small cluster of unlabelled points around each pillar, so a branch reads as
    // a constellation and not a single dot.
    var satellites=[];
    for(var si=0;si<groups.length;si++){
      var host=groups[si];
      for(var k=0;k<22;k++){
        var ang=random()*6.28,rad=(.045+random()*.12)*SHELL;
        satellites.push({x:host.x+Math.cos(ang)*rad,y:host.y+(random()-.5)*.4*SHELL,
          z:host.z+Math.sin(ang)*rad,group:host.id,r:random()*1.1+.35});
      }
    }
    var DUST=['#afd5df','#8bb3db','#c89cb5','#b0a1d1','#dacda1'];
    var particles=[];
    for(var di=0;di<900;di++){
      particles.push({a:random()*Math.PI*2,r:(.72+random()*.28)*SHELL,
        h:random()*2-1,s:.25+random()*.85,p:random()*6.28,c:Math.floor(random()*5)});
    }
    // Screen-space background stars, unaffected by rotation, exactly as before.
    var stars=[];
    for(var sti=0;sti<420;sti++){
      stars.push({x:random(),y:random(),r:random()<.97?random()*.8+.12:1.2,
        a:random()*.5+.08,p:random()*6.28});
    }
    var phase=0;
    // ── focus ─────────────────────────────────────────────────────────────────
    // Clicking a pillar focuses its branch and dims the rest, the way the sketch
    // the author supplied behaves. Clicking empty space keeps the existing contract
    // and expands or contracts the stage, so nothing that worked before changes.
    var selected=null;
    function hitTest(px,py,w,h,r){
      var best=null,bestD=1e9;
      for(var i=0;i<nodes.length;i++){
        var n=nodes[i],q=project(n,w,h,r);
        var d=Math.hypot(q.x-px,q.y-py);
        // Pillars and the core get a generous target; diagnostics a tighter one,
        // so a stray click near a crowded label does not hijack the expand toggle.
        var reach=n.core?34:n.major?30:14;
        if(d<reach&&d<bestD){bestD=d;best=n;}
      }
      return best;}
    function focusGroup(id){
      selected=(selected===id||!id)?null:id;
      canvas.dataset.focus=selected||'';
      var hint=canvas.closest('.mtdi-orbit-scene')?.querySelector('.mtdi-constellation-label em');
      if(hint)hint.textContent=selected?String(selected).toUpperCase()+' · CLICK CORE TO CLEAR'
        :(canvas.dataset.expanded==='1'?'CLICK TO CONTRACT':'CLICK TO EXPAND');
      render();}
    function dimFor(group){return !selected||group===selected?1:.16;}
    function size(){
      var w=Math.max(96,canvas.clientWidth||190),h=Math.max(96,canvas.clientHeight||190);
      canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);render();
    }
    function rotate(p){
      var cy=Math.cos(yaw),sy=Math.sin(yaw),cx=Math.cos(pitch),sx=Math.sin(pitch),cz=Math.cos(roll),sz=Math.sin(roll);
      var x1=p.x*cy+p.z*sy,z1=-p.x*sy+p.z*cy;
      var y2=p.y*cx-z1*sx,z2=p.y*sx+z1*cx;
      return{x:x1*cz-y2*sz,y:x1*sz+y2*cz,z:z2};
    }
    function project(p,w,h,r){
      var q=rotate(p),persp=2.8/(3.45-q.z);
      return{x:w/2+q.x*r*persp,y:h/2-q.y*r*persp,z:q.z,k:persp};
    }
    function glow(x,y,r,color,alpha){
      if(!(r>0)||!(alpha>0))return;
      ctx.globalAlpha=Math.min(1,alpha);
      var g=ctx.createRadialGradient(x,y,0,x,y,r);
      g.addColorStop(0,color);g.addColorStop(.12,color+'b0');
      g.addColorStop(.38,color+'30');g.addColorStop(1,color+'00');
      ctx.fillStyle=g;ctx.fillRect(x-r,y-r,r*2,r*2);ctx.globalAlpha=1;
    }
    function link(a,b,color,alpha,width){
      ctx.globalAlpha=alpha;ctx.strokeStyle=color;ctx.lineWidth=width||.6;
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.globalAlpha=1;
    }
    // Labels are drawn on the canvas rather than as positioned <a> elements. The
    // supplied sketch used DOM links because it owned the whole page; here the
    // constellation is one element inside a Dash layout, and DOM overlays would
    // escape the card, fight the full-screen transition and need their own z-index
    // bookkeeping. Canvas text stays inside the canvas at every angle.
    function drawLabel(node,p,w,h,dim){
      var scale=Math.max(.72,Math.min(1.3,w/420));
      var px=node.core?21:node.major?10.5:7.2;
      var size=Math.max(6.5,px*p.k*scale);
      ctx.font=(node.core?'500 ':'400 ')+size.toFixed(2)+'px DM Mono, monospace';
      var spacing=node.core?size*.36:node.major?size*.17:size*.06;
      var text=node.text,width=ctx.measureText(text).width+spacing*(text.length-1);
      // Ease an extreme edge position inward so a label is never sliced in half by
      // the canvas border. Same guard the plates used, measured on real text.
      var dx=p.x-w/2,dy=p.y-h/2,pad=6;
      var limitX=Math.max(1,w/2-width/2-pad),limitY=Math.max(1,h/2-size-pad);
      var edge=Math.min(1,limitX/Math.max(1,Math.abs(dx)),limitY/Math.max(1,Math.abs(dy)));
      var x=w/2+dx*edge-width/2,y=h/2+dy*edge+(node.core?size*.36:-(node.major?12:9));
      var TH=i3Theme();
      ctx.globalAlpha=Math.min(1,dim*.82);
      ctx.fillStyle='rgba('+TH.plate+',.72)';
      ctx.fillRect(x-5,y-size*.92,width+10,size*1.3);
      ctx.globalAlpha=dim;
      ctx.fillStyle=node.core?'#e0f9ff':node.color;
      ctx.textAlign='left';ctx.textBaseline='alphabetic';
      for(var i=0;i<text.length;i++){
        ctx.fillText(text[i],x,y);x+=ctx.measureText(text[i]).width+spacing;
      }
      ctx.globalAlpha=1;
      return {x:w/2+dx*edge,y:y};
    }
    function render(){
      var w=canvas.width/dpr,h=canvas.height/dpr,r=Math.min(w,h)*.29*zoom;
      ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
      var TH=i3Theme();
      var centre=project(core,w,h,r),R=r*.86;
      // Background stars: screen space, so they read as distance rather than as
      // part of the object being rotated.
      for(var si=0;si<stars.length;si++){
        var st=stars[si];
        ctx.globalAlpha=st.a*(.75+.25*Math.sin(phase*2+st.p));
        ctx.fillStyle=TH.starFar;
        ctx.fillRect(st.x*w-st.r/2,st.y*h-st.r/2,st.r,st.r);
      }
      ctx.globalAlpha=1;
      glow(centre.x,centre.y,R*1.6,'#142e43',.25);
      glow(centre.x-R*.45,centre.y+R*.1,R*.9,'#37223c',.18);
      // The rotating dust shell.
      for(var pi=0;pi<particles.length;pi++){
        var d=particles[pi],ang=d.a+phase*(.12+.1*(1-d.r/SHELL));
        var band=Math.sqrt(Math.max(0,1-d.h*d.h));
        var q=project({x:Math.cos(ang)*d.r*band,y:d.h*d.r,z:Math.sin(ang)*d.r*band},w,h,r);
        var alpha=(.32+.45*(1-d.r/SHELL))*(.65+.35*Math.sin(d.p+phase))
                 *Math.max(.25,Math.min(1.2,1-q.z));
        ctx.globalAlpha=Math.min(1,alpha);ctx.fillStyle=DUST[d.c];
        var ps=Math.max(.4,d.s*q.k*zoom);
        ctx.fillRect(q.x-ps/2,q.y-ps/2,ps,ps);
      }
      ctx.globalAlpha=1;
      // Each pillar's small cluster, plus a few threads back to the pillar itself.
      for(var i=0;i<satellites.length;i++){
        var sat=satellites[i],sp=project(sat,w,h,r),host=byId[sat.group];
        var sd=dimFor(sat.group);
        ctx.fillStyle=host.color;ctx.globalAlpha=.55*sd;
        ctx.beginPath();ctx.arc(sp.x,sp.y,sat.r*sp.k,0,Math.PI*2);ctx.fill();
        ctx.globalAlpha=1;
        var next=satellites[i+1];
        if(next&&next.group===sat.group&&i%3!==0)link(sp,project(next,w,h,r),host.color,.12*sd,.45);
        if(i%7===0)link(sp,project(host,w,h,r),host.color,.15*sd,.5);
      }
      // Core to pillar, pillar to diagnostic, and the chain along each branch.
      for(var gi=0;gi<groups.length;gi++){
        var g=groups[gi],gp=project(g,w,h,r),gd=dimFor(g.id);
        var start={x:centre.x+(gp.x-centre.x)*.12,y:centre.y+(gp.y-centre.y)*.12};
        link(start,gp,g.color,.32*gd,.75);
        var previous=gp;
        for(var ci=0;ci<g.children.length;ci++){
          var cp=project(g.children[ci],w,h,r);
          link(gp,cp,g.color,.30*gd,.65);link(previous,cp,g.color,.12*gd,.45);previous=cp;
        }
        // A pulse travelling out along the branch: this is the only motion in the
        // scene that is decorative, and it stops under prefers-reduced-motion.
        if(!reduceMotion()){
          var t=(phase*.6+gi*.19)%1;
          glow(start.x+(gp.x-start.x)*t,start.y+(gp.y-start.y)*t,4*gp.k,g.color,.7*gd);
        }
      }
      // The ring joining the pillars near the core.
      for(var ri=0;ri<groups.length;ri++){
        var a=project(groups[ri],w,h,r),b=project(groups[(ri+1)%groups.length],w,h,r);
        link({x:centre.x+(a.x-centre.x)*.32,y:centre.y+(a.y-centre.y)*.32},
             {x:centre.x+(b.x-centre.x)*.32,y:centre.y+(b.y-centre.y)*.32},'#80b6c9',.16,.5);
      }
      // Nodes and labels, painted back to front so a near label covers a far one.
      var ordered=nodes.slice().sort(function(a,b){
        return project(b,w,h,r).z-project(a,w,h,r).z;});
      for(var ni=0;ni<ordered.length;ni++){
        var node=ordered[ni],p=project(node,w,h,r);
        var dim=Math.max(.35,Math.min(1,(p.z+1.4)/2.4))*(node.core?1:dimFor(node.group));
        if(!node.core){
          glow(p.x,p.y,(node.major?15:8)*p.k,node.color,.7*dim);
          ctx.globalAlpha=dim;
          ctx.fillStyle=node.major?'#f5f0df':node.color;
          ctx.beginPath();ctx.arc(p.x,p.y,(node.major?2.5:1.35)*p.k,0,Math.PI*2);ctx.fill();
          if(node.major){
            ctx.strokeStyle=node.color;ctx.globalAlpha=.38*dim;ctx.lineWidth=.6;
            ctx.beginPath();ctx.arc(p.x,p.y,5.2*p.k,0,Math.PI*2);ctx.stroke();
          }
          ctx.globalAlpha=1;
        }
        if(!node.core&&(node.major||showChildLabels(w)))drawLabel(node,p,w,h,dim);
      }
      // Three great circles so the eye reads a sphere rather than a scatter.
      var axisColors=['#94dfff','#839ec7','#c6b0d2'];
      for(var ax=0;ax<3;ax++){
        ctx.beginPath();
        for(var j=0;j<=72;j++){
          var a2=j/72*Math.PI*2,cx=Math.cos(a2)*SHELL*.99,cy=Math.sin(a2)*SHELL*.99;
          var q2=project(ax===0?{x:cx,y:cy,z:0}:ax===1?{x:cx,y:0,z:cy}:{x:0,y:cx,z:cy},w,h,r);
          if(j===0)ctx.moveTo(q2.x,q2.y);else ctx.lineTo(q2.x,q2.y);
        }
        ctx.strokeStyle=axisColors[ax];ctx.globalAlpha=.085;ctx.lineWidth=.6;ctx.stroke();
      }
      ctx.globalAlpha=1;
    }
    function toggleExpanded(){
      var stage=canvas.closest('.mtdi-orbit-scene');if(!stage)return;
      stage.classList.toggle('is-constellation-expanded');
      var expanded=stage.classList.contains('is-constellation-expanded');
      canvas.dataset.expanded=expanded?'1':'0';
      var hint=stage.querySelector('.mtdi-constellation-label em');if(hint)hint.textContent=expanded?'CLICK TO CONTRACT':'CLICK TO EXPAND';
      if(stage.__mtdiPaint)stage.__mtdiPaint();
      setTimeout(size,40);setTimeout(size,360);setTimeout(size,760);
    }
    function toggleDirection(){spinDirection*=-1;baseYaw=.00016*spinDirection;velYaw=baseYaw;interact();}
    function down(e){wheelArmedUntil=performance.now()+3000;
      if(e.pointerType==='touch'||performance.now()-lastTouchAt<700)return;
      drag=true;moved=false;startX=lastX=e.clientX;startY=lastY=e.clientY;velYaw=velPitch=velRoll=0;interact();
      try{canvas.setPointerCapture(e.pointerId);}catch(x){}
    }
    function move(e){
      if(!drag||e.pointerType==='touch')return;var dx=e.clientX-lastX,dy=e.clientY-lastY;
      if(Math.hypot(e.clientX-startX,e.clientY-startY)>5)moved=true;
      if(e.shiftKey){roll+=dx*.0011;velRoll=limit(dx*.00012);}
      else{yaw+=dx*.0012;pitch-=dy*.0011;velYaw=limit(dx*.00012);velPitch=limit(-dy*.00011);}
      lastX=e.clientX;lastY=e.clientY;interact();render();
    }
    function up(e){
      if(e.pointerType==='touch')return;drag=false;coast((Math.abs(velYaw)+Math.abs(velPitch)+Math.abs(velRoll))*1200);
      try{canvas.releasePointerCapture(e.pointerId);}catch(x){}
      if(!moved){
        var w=canvas.width/dpr,h=canvas.height/dpr,r=Math.min(w,h)*.29*zoom;
        var rect=canvas.getBoundingClientRect();
        var hit=hitTest(e.clientX-rect.left,e.clientY-rect.top,w,h,r);
        if(hit&&hit.core)focusGroup(null);
        else if(hit)focusGroup(hit.group);
        else toggleExpanded();
      }
    }
    function liveTouches(list){var out=[];for(var i=0;i<list.length;i++)out.push({x:list[i].clientX,y:list[i].clientY});return out;}
    function touchStart(e){
      lastTouchAt=performance.now();e.preventDefault();var t=liveTouches(e.touches);interact();moved=false;
      if(t.length===1)touchGesture={mode:1,x:t[0].x,y:t[0].y,yaw:yaw,pitch:pitch};
      else if(t.length===2){var dx=t[1].x-t[0].x,dy=t[1].y-t[0].y;touchGesture={mode:2,cx:(t[0].x+t[1].x)/2,cy:(t[0].y+t[1].y)/2,d:Math.hypot(dx,dy),a:Math.atan2(dy,dx),yaw:yaw,pitch:pitch,roll:roll,zoom:zoom};}
      drag=true;velYaw=velPitch=velRoll=0;
    }
    function touchMove(e){
      lastTouchAt=performance.now();e.preventDefault();var t=liveTouches(e.touches);if(!touchGesture)return;
      if(t.length===1&&touchGesture.mode===1){var ny=touchGesture.yaw+(t[0].x-touchGesture.x)*.0012,np=touchGesture.pitch-(t[0].y-touchGesture.y)*.001;
        moved=moved||Math.hypot(t[0].x-touchGesture.x,t[0].y-touchGesture.y)>7;velYaw=limit((ny-yaw)*.11);velPitch=limit((np-pitch)*.11);yaw=ny;pitch=np;}
      else if(t.length===2&&touchGesture.mode===2){var dx=t[1].x-t[0].x,dy=t[1].y-t[0].y,cx=(t[0].x+t[1].x)/2,cy=(t[0].y+t[1].y)/2,a=Math.atan2(dy,dx),da=wrap(a-touchGesture.a);
        yaw=touchGesture.yaw-(cx-touchGesture.cx)*.001;pitch=touchGesture.pitch+(cy-touchGesture.cy)*.0009;roll=touchGesture.roll+da*.18;
        zoom=Math.max(.84,Math.min(1.12,touchGesture.zoom*Math.pow(Math.hypot(dx,dy)/Math.max(8,touchGesture.d),.72)));moved=true;}
      interact();render();
    }
    function touchEnd(e){
      lastTouchAt=performance.now();e.preventDefault();if(e.touches.length)return;
      drag=false;touchGesture=null;coast((Math.abs(velYaw)+Math.abs(velPitch)+Math.abs(velRoll))*1200);if(!moved)toggleExpanded();
    }
    var wheelArmedUntil=0;
    function wheel(e){
      // A plain two-finger scroll over the globe must scroll the page. The globe takes the
      // wheel only with a modifier (ctrl = zoom, shift = roll) or for 3 s after it was grabbed.
      if(!e.ctrlKey&&!e.shiftKey&&performance.now()>wheelArmedUntil)return;
      e.preventDefault();interact();var dx=Math.max(-30,Math.min(30,e.deltaX)),dy=Math.max(-30,Math.min(30,e.deltaY));
      if(e.ctrlKey)zoom=Math.max(.84,Math.min(1.12,zoom*Math.exp(-dy*.001)));
      else if(e.shiftKey){roll+=dy*.0007;velRoll=limit(velRoll+dy*.00005);}
      else{yaw-=dx*.0008;pitch+=dy*.0007;velYaw=limit(velYaw-dx*.00005);velPitch=limit(velPitch+dy*.000045);}
      coast(Math.abs(dx)+Math.abs(dy));render();
    }
    registerMacHandZoom(canvas,{
      zoom:function(handScale){zoom=Math.max(.65,Math.min(1.40,handScale));render();},
      /* Match the Home globe's direct-manipulation sign and inertial coast. This
         renderer stores yaw in radians, so 4.19 rad matches the globe's 240° gain. */
      rotate:function(screenDx,screenDy){
        screenDy=screenDy||0;
        // The Earth's physics, in this renderer's units: direct manipulation on both
        // axes, velocity seeded from the same travel, and one coast covering both.
        // Previously only screenDx existed, so up/down did nothing at all.
        yaw+=screenDx*4.19;pitch-=screenDy*3.84;
        velYaw=limit(screenDx*.035);velPitch=limit(-screenDy*.032);
        coast((Math.abs(screenDx)+Math.abs(screenDy))*900);interact();render();
      }
    });
    canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);
    canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);
    canvas.addEventListener('touchstart',touchStart,{passive:false});canvas.addEventListener('touchmove',touchMove,{passive:false});
    canvas.addEventListener('touchend',touchEnd,{passive:false});canvas.addEventListener('touchcancel',touchEnd,{passive:false});
    canvas.addEventListener('wheel',wheel,{passive:false});
    canvas.addEventListener('dblclick',function(e){e.preventDefault();toggleDirection();});
    // Keyboard: only while the constellation is on screen, so arrow keys keep
    // scrolling the page everywhere else.
    addEventListener('keydown',function(e){
      if(!attached(canvas))return;
      var box=canvas.getBoundingClientRect();
      if(box.bottom<0||box.top>innerHeight)return;
      if(e.key==='Escape'){if(selected){e.preventDefault();focusGroup(null);}return;}
      if(e.key.indexOf('Arrow')!==0)return;
      if(/^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement||{}).tagName||''))return;
      e.preventDefault();interact();coast(30);
      if(e.key==='ArrowLeft')velYaw=-.0016;
      else if(e.key==='ArrowRight')velYaw=.0016;
      else if(e.key==='ArrowUp')velPitch=-.0014;
      else velPitch=.0014;
    });
    addEventListener('resize',size,{passive:true});size();render();
    (function frame(now){
      if(!attached(canvas)){canvas.dataset.galleryInit='0';removeEventListener('resize',size);return;}
      requestAnimationFrame(frame);
      var rect=canvas.getBoundingClientRect();
      // This is live instrument-state motion, like the Earth core and orbit cards,
      // rather than decorative page animation; it keeps drifting autonomously.
      if(document.hidden||rect.bottom<0||rect.top>innerHeight||now-lastFrame<FRAME_INTERVAL-0.75)return;
      var dt=lastFrame?Math.min(50,now-lastFrame):16;lastFrame=now;
      phase=reduceMotion()?0:now*.00008;
      if(!drag){
        var settle=1-Math.exp(-dt/(now<coastUntil?2600:900));
        velYaw+=(baseYaw-velYaw)*settle;velPitch+=(0-velPitch)*settle;velRoll+=(0-velRoll)*settle;
        yaw=wrap(yaw+velYaw*dt);pitch=wrap(pitch+velPitch*dt);roll=wrap(roll+velRoll*dt);
      }
      render();
    })(performance.now());
  }

  // Small offline adaptation of the supplied dotted globe. It uses an orthographic
  // projection, graticule and locally generated continent dots: no D3 or web fetch.
  function bootHomeGlobe(){
    var canvas=document.getElementById('home-module-globe');
    if(!canvas||canvas.dataset.globeInit==='1')return;
    canvas.dataset.globeInit='1';
    var ctx=canvas.getContext('2d');if(!ctx)return;
    var dpr=Math.min(devicePixelRatio||1,2),yaw=0,pitch=-12,roll=0,zoom=1;
    var spinMagnitude=.20,spinDirection=-1;
    var baseYaw=spinMagnitude*spinDirection,basePitch=0,baseRoll=0;
    var drag=false,lastX=0,lastY=0,velYaw=baseYaw,velPitch=0,velRoll=0;
    var touchGesture=null,lastTouchAt=-Infinity,coastUntil=0;
    var tapCandidate=null,lastTapAt=0,lastTouchToggleAt=0;
    var markerHits=[];
    var researchNodes=[
      {name:'TITLE \u00b7 01',lon:-105.27,lat:40.02,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 02',lon:-75.70,lat:45.42,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 03',lon:-0.34,lat:51.43,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 04',lon:10.53,lat:52.30,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 05',lon:2.23,lat:48.83,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 06',lon:140.10,lat:36.06,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 07',lon:127.37,lat:36.39,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 08',lon:77.17,lat:28.63,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 09',lon:151.21,lat:-33.87,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 10',lon:-43.31,lat:-22.79,summary:'Paragraph. Enter your text here.'},
      {name:'TITLE \u00b7 11',lon:28.28,lat:-25.75,summary:'Paragraph. Enter your text here.'}
    ];
    // Network topology drawn as exterior arcs. Each pair is an index into researchNodes.
    var researchLinks=[[0,1],[0,9],[0,10],[1,2],[2,3],[2,4],[3,4],[3,6],[4,7],[4,10],
      [6,5],[5,8],[7,6],[7,10],[8,9],[9,10],[2,7],[3,8],[0,2],[5,9]];
    function wrapAngle(v){return ((v+180)%360+360)%360-180;}
    function limitVelocity(v){return Math.max(-1.0,Math.min(1.0,v));}
    function markInteraction(){
      canvas.dataset.recovering='0';
    }
    function updateDirectionLabel(){
      canvas.dataset.spinDirection=spinDirection<0?'right-to-left':'left-to-right';
    }
    function toggleSpinDirection(){
      spinDirection*=-1;baseYaw=spinMagnitude*spinDirection;
      coastUntil=0;velYaw=baseYaw;markInteraction();updateDirectionLabel();render();
    }
    function doubleClick(e){
      if(performance.now()-lastTouchToggleAt<700)return;
      if(e&&e.preventDefault)e.preventDefault();toggleSpinDirection();
    }
    function armCoast(strength){
      var duration=Math.min(3200,360+Math.max(0,strength)*70);
      coastUntil=Math.max(coastUntil,performance.now()+duration);
    }
    var points=[];
    var landPolygons=[];
    function pointInPolygon(lon,lat,poly){
      var inside=false;
      for(var i=0,j=poly.length-1;i<poly.length;j=i++){
        var xi=poly[i][0],yi=poly[i][1],xj=poly[j][0],yj=poly[j][1];
        if(((yi>lat)!==(yj>lat))&&lon<(xj-xi)*(lat-yi)/(yj-yi)+xi)inside=!inside;
      }
      return inside;
    }
    function buildDots(polygons){
      var dots=[];
      for(var p=0;p<polygons.length;p++){
        var poly=polygons[p],minLon=180,maxLon=-180,minLat=90,maxLat=-90;
        for(var q=0;q<poly.length;q++){
          minLon=Math.min(minLon,poly[q][0]);maxLon=Math.max(maxLon,poly[q][0]);
          minLat=Math.min(minLat,poly[q][1]);maxLat=Math.max(maxLat,poly[q][1]);
        }
        for(var lat=Math.ceil(minLat/3)*3;lat<=maxLat;lat+=3){
          for(var lon=Math.ceil(minLon/3)*3;lon<=maxLon;lon+=3){
            if(pointInPolygon(lon,lat,poly))dots.push([lon,lat]);
          }
        }
      }
      return dots;
    }
    function installLand(polygons,dots){landPolygons=polygons;points=dots;render();}
    function size(){
      var w=Math.max(64,canvas.clientWidth||330),h=Math.max(64,canvas.clientHeight||330);
      canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    }
    var rotation=[1,0,1,0,1,0];
    function project(lon,lat,w,h,r){
      var la=lon*Math.PI/180,ph=lat*Math.PI/180,cp=Math.cos(ph);
      var x=cp*Math.sin(la),y=-Math.sin(ph),z=cp*Math.cos(la);
      var cy=rotation[0],sy=rotation[1],cx=rotation[2],sx=rotation[3],cz=rotation[4],sz=rotation[5];
      var x1=x*cy+z*sy,z1=-x*sy+z*cy;
      var y2=y*cx-z1*sx,z2=y*sx+z1*cx;
      var x3=x1*cz-y2*sz,y3=x1*sz+y2*cz;
      return [w/2+x3*r,h/2+y3*r,z2];
    }
    // An arbitrary point in space, rotated by the same matrix. Exterior link arcs
    // ride above the surface, so they are not on the unit sphere and cannot use project().
    function project3(v,w,h,r){
      var cy=rotation[0],sy=rotation[1],cx=rotation[2],sx=rotation[3],cz=rotation[4],sz=rotation[5];
      var x1=v[0]*cy+v[2]*sy,z1=-v[0]*sy+v[2]*cy;
      var y2=v[1]*cx-z1*sx,z2=v[1]*sx+z1*cx;
      var x3=x1*cz-y2*sz,y3=x1*sz+y2*cz;
      // Orthographic projection: a point is hidden by the globe when it is behind the
      // centre plane AND its screen radius falls inside the disc.
      return [w/2+x3*r,h/2+y3*r,z2,Math.sqrt(x3*x3+y3*y3)];
    }
    function unitVec(lon,lat){
      var la=lon*Math.PI/180,ph=lat*Math.PI/180,cp=Math.cos(ph);
      return [cp*Math.sin(la),-Math.sin(ph),cp*Math.cos(la)];
    }
    function render(){
      // Rotation is constant for every point in this frame.
      var ay=yaw*Math.PI/180,ax=pitch*Math.PI/180,az=roll*Math.PI/180;
      rotation=[Math.cos(ay),Math.sin(ay),Math.cos(ax),Math.sin(ax),Math.cos(az),Math.sin(az)];
      var w=canvas.width/dpr,h=canvas.height/dpr,r=Math.min(w,h)*.37*zoom;
      ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
      var TH=i3Theme();
      var ocean=ctx.createRadialGradient(w*.42,h*.36,2,w/2,h/2,r);
      ocean.addColorStop(0,TH.oceanIn);ocean.addColorStop(1,TH.oceanOut);
      ctx.beginPath();ctx.arc(w/2,h/2,r,0,Math.PI*2);ctx.fillStyle=ocean;ctx.fill();
      var visualScale=Math.max(.72,Math.min(1.35,w/300));
      ctx.save();ctx.shadowColor='rgba(49,215,230,.8)';ctx.shadowBlur=18*visualScale;
      ctx.strokeStyle=TH.limb;ctx.lineWidth=.8*visualScale;ctx.stroke();ctx.restore();
      ctx.strokeStyle=TH.grat;ctx.lineWidth=.6*visualScale;
      function curve(samples){
        ctx.beginPath();var drawing=false;
        for(var i=0;i<samples.length;i++){
          var p=project(samples[i][0],samples[i][1],w,h,r);
          if(p[2]<=0){drawing=false;continue;}
          if(!drawing){ctx.moveTo(p[0],p[1]);drawing=true;}else ctx.lineTo(p[0],p[1]);
        }
        ctx.stroke();
      }
      for(var glat=-60;glat<=60;glat+=30){var ls=[];for(var lo=-180;lo<=180;lo+=5)ls.push([lo,glat]);curve(ls);}
      for(var glon=-150;glon<=180;glon+=30){var ps=[];for(var la=-90;la<=90;la+=4)ps.push([glon,la]);curve(ps);}
      ctx.strokeStyle=TH.land;ctx.lineWidth=.85*visualScale;
      for(var k=0;k<landPolygons.length;k++)curve(landPolygons[k].concat([landPolygons[k][0]]));
      for(var j=0;j<points.length;j++){
        var q=project(points[j][0],points[j][1],w,h,r);if(q[2]<=0)continue;
        ctx.beginPath();ctx.arc(q[0],q[1],.92*visualScale,0,Math.PI*2);
        ctx.fillStyle='rgba('+TH.dot+','+(.46+q[2]*.46).toFixed(3)+')';ctx.fill();
      }
      /* Decorative research links; these are institutes, not live measurements.
         Each link is a great-circle arc lifted clear of the surface, so it reads as a
         span over the Earth rather than a line ruled across the picture. */
      var projected=researchNodes.map(function(node){return {node:node,p:project(node.lon,node.lat,w,h,r)};});
      var unitAt=researchNodes.map(function(node){return unitVec(node.lon,node.lat);});
      var arcSteps=26,lift=0.21;
      ctx.save();ctx.lineCap='round';
      for(var L=0;L<researchLinks.length;L++){
        var ia=researchLinks[L][0],ib=researchLinks[L][1];
        var va=unitAt[ia],vb=unitAt[ib];
        var dot=Math.max(-1,Math.min(1,va[0]*vb[0]+va[1]*vb[1]+va[2]*vb[2]));
        var omega=Math.acos(dot),sinO=Math.sin(omega);
        if(sinO<1e-4)continue;
        // Walk the arc, breaking the stroke wherever it passes behind the globe.
        var run=[],front=0,total=0;
        for(var t=0;t<=arcSteps;t++){
          var f=t/arcSteps;
          var c1=Math.sin((1-f)*omega)/sinO,c2=Math.sin(f*omega)/sinO;
          var h1=1+lift*Math.sin(Math.PI*f);
          var pt=project3([(va[0]*c1+vb[0]*c2)*h1,(va[1]*c1+vb[1]*c2)*h1,(va[2]*c1+vb[2]*c2)*h1],w,h,r);
          var hidden=pt[2]<0&&pt[3]<1;
          total++;if(!hidden)front++;
          if(hidden){if(run.length>1)strokeArc(run,front/Math.max(1,total));run=[];}
          else run.push(pt);
        }
        if(run.length>1)strokeArc(run,front/Math.max(1,total));
      }
      function strokeArc(pts,vis){
          var glow=(.30+vis*.55);
          ctx.save();
          ctx.shadowColor='rgba(64,214,255,'+(glow*.9).toFixed(3)+')';
          ctx.shadowBlur=9*visualScale;
          var g=ctx.createLinearGradient(pts[0][0],pts[0][1],pts[pts.length-1][0],pts[pts.length-1][1]);
          g.addColorStop(0,'rgba(88,226,255,'+(glow*.55).toFixed(3)+')');
          g.addColorStop(.5,'rgba(196,246,255,'+glow.toFixed(3)+')');
          g.addColorStop(1,'rgba(146,168,255,'+(glow*.6).toFixed(3)+')');
          ctx.strokeStyle=g;ctx.lineWidth=1.45*visualScale;
          ctx.beginPath();ctx.moveTo(pts[0][0],pts[0][1]);
          for(var q=1;q<pts.length;q++)ctx.lineTo(pts[q][0],pts[q][1]);
          ctx.stroke();
          ctx.restore();
      }
      ctx.restore();
      markerHits=[];
      for(var m=0;m<researchNodes.length;m++){
        var node=researchNodes[m],mp=projected[m].p;if(mp[2]<=0)continue;
        var depth=.45+mp[2]*.55;
        var pulse=(5.4+Math.sin(performance.now()*.0026+m*1.7)*1.5)*visualScale;
        ctx.save();
        ctx.shadowColor='rgba(120,236,255,'+(depth*.95).toFixed(3)+')';ctx.shadowBlur=16*visualScale;
        // Outer breathing ring, inner core: the node reads as a lit beacon on the limb.
        ctx.strokeStyle='rgba(96,226,255,'+(depth*.55).toFixed(3)+')';ctx.lineWidth=1.1*visualScale;
        ctx.beginPath();ctx.arc(mp[0],mp[1],pulse,0,Math.PI*2);ctx.stroke();
        ctx.fillStyle='rgba(214,250,255,'+depth.toFixed(3)+')';
        ctx.beginPath();ctx.arc(mp[0],mp[1],2.9*visualScale,0,Math.PI*2);ctx.fill();
        ctx.shadowBlur=26*visualScale;ctx.fillStyle='rgba(255,255,255,'+(depth*.85).toFixed(3)+')';
        ctx.beginPath();ctx.arc(mp[0],mp[1],1.35*visualScale,0,Math.PI*2);ctx.fill();
        ctx.restore();
        markerHits.push({x:mp[0],y:mp[1],r:14*visualScale,node:node});
      }
    }
    function selectResearchNode(e){var rect=canvas.getBoundingClientRect(),x=(e.clientX-rect.left),y=(e.clientY-rect.top),hit=null,best=1e9;for(var i=0;i<markerHits.length;i++){var d=Math.hypot(x-markerHits[i].x,y-markerHits[i].y);if(d<markerHits[i].r&&d<best){best=d;hit=markerHits[i];}}if(!hit)return;var out=document.getElementById('home-globe-research');if(out){out.hidden=false;out.querySelector('b').textContent=hit.node.name;out.querySelector('span').textContent=hit.node.summary;}e.preventDefault();e.stopPropagation();}
    function beginTouchGesture(t){
      if(!t||t.length!==2){touchGesture=null;drag=false;return;}
      markInteraction();
      var a=t[0],b=t[1],dx=b.x-a.x,dy=b.y-a.y;
      touchGesture={mode:2,cx:(a.x+b.x)/2,cy:(a.y+b.y)/2,d:Math.max(8,Math.sqrt(dx*dx+dy*dy)),
        a:Math.atan2(dy,dx),yaw:yaw,pitch:pitch,roll:roll,zoom:zoom};
      velYaw=velPitch=velRoll=0;drag=true;
    }
    function beginSingleTouch(t){
      if(!t||t.length!==1){touchGesture=null;drag=false;return;}
      markInteraction();
      touchGesture={mode:1,x:t[0].x,y:t[0].y,yaw:yaw,pitch:pitch};
      velYaw=velPitch=0;drag=true;
    }
    function down(e){wheelArmedUntil=performance.now()+3000;
      // Touch is handled by Touch Events below; compatibility PointerEvents are
      // ignored so a single physical gesture is never applied twice.
      if(e.pointerType==='touch'||e.pointerType==='pen'||
         (e.sourceCapabilities&&e.sourceCapabilities.firesTouchEvents)||
         performance.now()-lastTouchAt<900)return;
      try{canvas.setPointerCapture(e.pointerId);}catch(x){}
      markInteraction();
      drag=true;lastX=e.clientX;lastY=e.clientY;velYaw=velPitch=velRoll=0;
    }
    function move(e){
      if(e.pointerType==='touch'||e.pointerType==='pen'||
         (e.sourceCapabilities&&e.sourceCapabilities.firesTouchEvents)||
         performance.now()-lastTouchAt<900)return;
      if(!drag)return;
      markInteraction();
      var dx=e.clientX-lastX,dy=e.clientY-lastY;
      if(e.shiftKey){roll+=dx*.24;velRoll=limitVelocity(dx*.040);}
      else{
        // One-pointer direct manipulation: the globe follows the finger/cursor.
        yaw+=dx*.24;pitch-=dy*.22;
        velYaw=limitVelocity(dx*.040);velPitch=limitVelocity(-dy*.035);
      }
      lastX=e.clientX;lastY=e.clientY;render();
    }
    function up(e){
      if(e.pointerType==='touch'||e.pointerType==='pen'||
         (e.sourceCapabilities&&e.sourceCapabilities.firesTouchEvents)||
         performance.now()-lastTouchAt<900)return;
      drag=false;armCoast((Math.abs(velYaw)+Math.abs(velPitch)+Math.abs(velRoll))*18);
      try{canvas.releasePointerCapture(e.pointerId);}catch(x){}
    }
    function liveTouches(list){
      var out=[];for(var i=0;i<list.length;i++)out.push({x:list[i].clientX,y:list[i].clientY});
      return out;
    }
    function touchStart(e){
      lastTouchAt=performance.now();e.preventDefault();
      var tv=liveTouches(e.touches);
      if(tv.length===2){tapCandidate=null;beginTouchGesture(tv);}
      else if(tv.length===1){
        tapCandidate={x:tv[0].x,y:tv[0].y,t:lastTouchAt};beginSingleTouch(tv);
      }
      else{touchGesture=null;drag=false;}
    }
    function touchMove(e){
      lastTouchAt=performance.now();e.preventDefault();
      var tv=liveTouches(e.touches);
      if(tv.length===1){
        markInteraction();
        if(tapCandidate&&Math.hypot(tv[0].x-tapCandidate.x,tv[0].y-tapCandidate.y)>10)tapCandidate=null;
        if(!touchGesture||touchGesture.mode!==1){beginSingleTouch(tv);return;}
        var one=tv[0];
        var oneYaw=touchGesture.yaw+(one.x-touchGesture.x)*.20;
        var onePitch=touchGesture.pitch-(one.y-touchGesture.y)*.18;
        velYaw=limitVelocity((oneYaw-yaw)*.05);velPitch=limitVelocity((onePitch-pitch)*.05);
        yaw=oneYaw;pitch=onePitch;render();return;
      }
      tapCandidate=null;markInteraction();
      if(tv.length!==2){touchGesture=null;drag=false;return;}
      if(!touchGesture||touchGesture.mode!==2){beginTouchGesture(tv);return;}
      var ta=tv[0],tb=tv[1],tdx=tb.x-ta.x,tdy=tb.y-ta.y;
      var tcx=(ta.x+tb.x)/2,tcy=(ta.y+tb.y)/2;
      var dist=Math.max(8,Math.sqrt(tdx*tdx+tdy*tdy));
      var ang=Math.atan2(tdy,tdx),da=ang-touchGesture.a;
      while(da>Math.PI)da-=Math.PI*2;while(da< -Math.PI)da+=Math.PI*2;
      var newYaw=touchGesture.yaw-(tcx-touchGesture.cx)*.17;
      var newPitch=touchGesture.pitch+(tcy-touchGesture.cy)*.15;
      var newRoll=touchGesture.roll+da*180/Math.PI*.42;
      velYaw=limitVelocity((newYaw-yaw)*.045);velPitch=limitVelocity((newPitch-pitch)*.045);
      velRoll=limitVelocity((newRoll-roll)*.045);
      yaw=newYaw;pitch=newPitch;roll=newRoll;
      zoom=Math.max(.84,Math.min(1.08,touchGesture.zoom*Math.pow(dist/touchGesture.d,.72)));
      render();
    }
    function touchEnd(e){
      lastTouchAt=performance.now();e.preventDefault();
      var tv=liveTouches(e.touches);
      if(tv.length===2)beginTouchGesture(tv);
      else if(tv.length===1)beginSingleTouch(tv);
      else{
        armCoast((Math.abs(velYaw)+Math.abs(velPitch)+Math.abs(velRoll))*18);
        touchGesture=null;drag=false;
        if(tapCandidate&&lastTouchAt-tapCandidate.t<300){
          if(lastTouchAt-lastTapAt<380){
            toggleSpinDirection();lastTouchToggleAt=lastTouchAt;lastTapAt=0;
          }
          else lastTapAt=lastTouchAt;
        }
        tapCandidate=null;
      }
    }
    var wheelArmedUntil=0;
    function wheel(e){
      if(!e.ctrlKey&&!e.shiftKey&&performance.now()>wheelArmedUntil)return;   // let the page scroll unless grabbed
      e.preventDefault();
      markInteraction();
      // A trackpad's two-finger gesture is exposed as WheelEvent. Pinching carries
      // ctrlKey in modern browsers; ordinary two-finger travel controls yaw/pitch.
      var unit=e.deltaMode===1?10:(e.deltaMode===2?60:1);
      var rawX=Math.max(-28,Math.min(28,e.deltaX*unit));
      var rawY=Math.max(-28,Math.min(28,e.deltaY*unit));
      if(e.ctrlKey){
        zoom=Math.max(.84,Math.min(1.08,zoom*Math.exp(-rawY*.003)));
      }else if(e.shiftKey){
        var dr=(Math.abs(rawX)>Math.abs(rawY)?rawX:rawY)*.07;
        roll+=dr;velRoll=limitVelocity(velRoll+dr*.05);
        armCoast(Math.abs(rawX)+Math.abs(rawY));
      }else{
        // Direct-manipulation direction: the Earth follows the two-finger travel.
        var wy=Math.abs(rawX)<.28?0:-rawX*.075;
        var wp=Math.abs(rawY)<.28?0:-rawY*.065;
        yaw+=wy;pitch-=wp;
        velYaw=limitVelocity(velYaw+wy*.05);velPitch=limitVelocity(velPitch-wp*.05);
        armCoast(Math.abs(rawX)+Math.abs(rawY));
      }
      render();
    }
    registerMacHandZoom(canvas,{
      zoom:function(handScale){zoom=Math.max(.65,Math.min(1.35,handScale));render();},
      rotate:function(screenDx,screenDy){
        screenDy=screenDy||0;
        // Same gain and sign as a pointer drag, so the hand and the mouse move the
        // globe the same way, and both feed the same inertial coast.
        yaw+=screenDx*240;pitch-=screenDy*220;
        velYaw=limitVelocity(screenDx*16);velPitch=limitVelocity(-screenDy*14);
        armCoast((Math.abs(screenDx)+Math.abs(screenDy))*900);markInteraction();render();
      }
    });
    canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);
    canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);
    canvas.addEventListener('touchstart',touchStart,{passive:false});
    canvas.addEventListener('touchmove',touchMove,{passive:false});
    canvas.addEventListener('touchend',touchEnd,{passive:false});
    canvas.addEventListener('touchcancel',touchEnd,{passive:false});
    canvas.addEventListener('wheel',wheel,{passive:false});
    canvas.addEventListener('click',selectResearchNode);
    canvas.addEventListener('dblclick',doubleClick);
    size();updateDirectionLabel();canvas.dataset.recovering='0';canvas.dataset.recoveryCount='0';render();
    if(window.__i3NaturalEarth){
      installLand(window.__i3NaturalEarth.polygons,window.__i3NaturalEarth.points);
    }else{
      fetch('/_i3/natural-earth-land.json',{cache:'force-cache'}).then(function(response){
        if(!response.ok)throw new Error('Natural Earth asset unavailable');
        return response.json();
      }).then(function(data){
        var polygons=[];
        if(Array.isArray(data))polygons=data;
        else (data.features||[]).forEach(function(feature){
            var g=feature&&feature.geometry;if(!g)return;
            if(g.type==='Polygon'&&g.coordinates[0])polygons.push(g.coordinates[0]);
            else if(g.type==='MultiPolygon'){
              g.coordinates.forEach(function(poly){if(poly[0])polygons.push(poly[0]);});
            }
          });
        if(!polygons.length)throw new Error('Natural Earth geometry is empty');
        var dots=buildDots(polygons);
        window.__i3NaturalEarth={polygons:polygons,points:dots};
        if(attached(canvas))installLand(polygons,dots);
      }).catch(function(){
        // Graticule-only fallback remains fully functional if the local asset fails.
      });
    }
    var lastFrame=0;
    (function globeFrame(now){
      if(!attached(canvas)){canvas.dataset.globeInit='0';return;}
      requestAnimationFrame(globeFrame);
      var bounds=canvas.getBoundingClientRect();
      if(document.hidden||bounds.bottom<0||bounds.top>innerHeight||drag||reduceMotion()||now-lastFrame<FRAME_INTERVAL-0.75){if(document.hidden||bounds.bottom<0||bounds.top>innerHeight)lastFrame=0;return;}
      var dt=lastFrame?Math.min(70,now-lastFrame):33;lastFrame=now;
      var frame=dt/33;
      // Strong flicks earn a longer, lower-friction coast. Gentle gestures settle
      // quickly, so control remains precise instead of feeling permanently loose.
      var settleMs=now<coastUntil?2600:880;
      var settle=1-Math.exp(-dt/settleMs);
      // Inertia eases back into the permanent longitudinal drift. Every axis wraps
      // continuously, so motion can pass through either pole without a hard stop.
      velYaw+=(baseYaw-velYaw)*settle;
      velPitch+=(basePitch-velPitch)*settle;
      velRoll+=(baseRoll-velRoll)*settle;
      yaw=wrapAngle(yaw+velYaw*frame);
      pitch=wrapAngle(pitch+velPitch*frame);
      roll=wrapAngle(roll+velRoll*frame);render();
    })(performance.now());
  }

  // ── MTDI V2: responsive physics + same-element full-screen transition ─────
  function armMtdiOrbit(){
    var stage=document.getElementById('mtdi-orbit-stage-v2');
    if(!stage||stage.dataset.mtdiV2==='1')return;
    var cards=[].slice.call(stage.querySelectorAll('.mtdi-orbit-card'));
    var ring=stage.querySelector('.mtdi-orbit-ring-v2');
    if(cards.length<4||!ring)return;
    stage.dataset.mtdiV2='1';
    var angle=-Math.PI/2,active=null,transitioning=false,last=performance.now();
    var lastPaint=0,alive=true,returnRect=null,radiusNow=260,cardScaleNow=1;

    var wasLinear=null;
    function geometry(){
      var mobile=innerWidth<=760;
      var expanded=stage.classList.contains('is-constellation-expanded');
      // Clearance is measured against the constellation's real drawn size, which
      // grows when it is expanded — that growth is what used to push the cards
      // underneath it.
      var coreBox=expanded
        ? (mobile?Math.min(340,innerWidth*0.72):500)
        : (mobile?170:420);
      var fit=orbitFit({
        sceneW:stage.clientWidth||innerWidth,
        sceneH:stage.clientHeight||680,
        cardW:mobile?154:300, cardH:mobile?130:200,
        coreR:coreBox/2,
        ideal:expanded?(mobile?300:520):(mobile?148:360),
        scale:expanded?1.08:1});
      if(!fit){radiusNow=null;return null;}
      radiusNow=fit.r; cardScaleNow=fit.scale;
      ring.style.setProperty('--orbit-diameter',(fit.r*2)+'px');
      return fit.r;
    }

    function setLinear(on){
      if(wasLinear===on)return;
      wasLinear=on;
      stage.classList.toggle('is-linear',on);
      if(on)for(var j=0;j<cards.length;j++){
        cards[j].style.transform='';cards[j].style.zIndex='';cards[j].style.opacity='';
      }
    }

    function paint(){
      if(active||transitioning||!attached(stage))return;
      var radius=geometry();
      if(radius===null){setLinear(true);return;}
      setLinear(false);
      for(var i=0;i<cards.length;i++){
        var card=cards[i];
        var idx=parseFloat(card.getAttribute('data-mtdi-index'))||0;
        var theta=angle+idx*(Math.PI*2/cards.length);
        var x=Math.cos(theta)*radius,y=Math.sin(theta)*radius;
        var depth=(Math.sin(theta)+1)/2;
        card.style.transform='translate3d('+x.toFixed(2)+'px,'+y.toFixed(2)+'px,0) scale('+cardScaleNow.toFixed(3)+')';
        card.style.zIndex=String(Math.round(10+depth*20));
        card.style.opacity=String(.78+depth*.22);
      }
    }

    function afterTransition(card,fn){
      var done=false;
      function finish(){
        if(done)return;done=true;
        card.removeEventListener('transitionend',ended);
        fn();
      }
      function ended(e){if(e.target===card&&e.propertyName==='width')finish();}
      card.addEventListener('transitionend',ended);
      setTimeout(finish,reduceMotion()?30:840);
    }

    function openCard(card){
      if(!card||transitioning||active)return;
      transitioning=true;
      returnRect=card.getBoundingClientRect();
      document.body.classList.add('mtdi-detail-open');
      document.body.style.overflow='hidden';
      card.classList.add('is-detached');
      card.style.transform='none';
      card.style.opacity='1';
      card.style.zIndex='10020';
      card.style.left=returnRect.left+'px';
      card.style.top=returnRect.top+'px';
      card.style.width=returnRect.width+'px';
      card.style.height=returnRect.height+'px';
      card.getBoundingClientRect();
      requestAnimationFrame(function(){requestAnimationFrame(function(){
        // Use the visual viewport so the pillar reaches the actual top edge even on
        // mobile browsers whose address bar changes the layout viewport height.
        card.style.left='0px';card.style.top='0px';
        card.style.width='100vw';card.style.height='100dvh';card.style.borderRadius='0px';
      });});
      afterTransition(card,function(){
        if(!attached(card))return;
        card.classList.add('is-expanded');
        card.scrollTop=0;active=card;transitioning=false;
        schedulePlotResize();
        var close=card.querySelector('.mtdi-detail-close');
        if(close)try{close.focus({preventScroll:true});}catch(e){close.focus();}
      });
    }

    function clearTransitionStyles(card){
      ['left','top','width','height','border-radius','z-index'].forEach(function(name){
        card.style.removeProperty(name);
      });
    }

    function closeCard(card){
      if(!card||transitioning||active!==card)return;
      transitioning=true;card.classList.add('is-closing');
      setTimeout(function(){
        if(!attached(card))return;
        card.classList.remove('is-expanded','is-closing');
        card.scrollTop=0;
        card.style.left=returnRect.left+'px';card.style.top=returnRect.top+'px';
        card.style.width=returnRect.width+'px';card.style.height=returnRect.height+'px';
        card.style.borderRadius='12px';
        afterTransition(card,function(){
          card.classList.remove('is-detached');
          clearTransitionStyles(card);
          document.body.classList.remove('mtdi-detail-open');
          document.body.style.overflow='';
          active=null;transitioning=false;last=performance.now();paint();
          try{card.focus({preventScroll:true});}catch(e){card.focus();}
        });
      },reduceMotion()?0:190);
    }

    function clicked(e){
      var close=e.target.closest&&e.target.closest('.mtdi-detail-close');
      if(close){e.preventDefault();e.stopPropagation();closeCard(close.closest('.mtdi-orbit-card'));return;}
      var card=e.target.closest&&e.target.closest('.mtdi-orbit-card');
      if(card&&!card.classList.contains('is-detached'))openCard(card);
    }
    function keyed(e){
      var card=e.target.closest&&e.target.closest('.mtdi-orbit-card');
      if(card&&!card.classList.contains('is-detached')&&(e.key==='Enter'||e.key===' ')){
        e.preventDefault();openCard(card);
      }
    }
    function escape(e){if(e.key==='Escape'&&active&&!transitioning)closeCard(active);}
    function resized(){paint();if(active)schedulePlotResize();}
    stage.addEventListener('click',clicked);
    stage.addEventListener('keydown',keyed);
    document.addEventListener('keydown',escape);
    window.addEventListener('resize',resized,{passive:true});
    paint();
    (function tick(now){
      if(!alive||!attached(stage)){
        alive=false;document.body.classList.remove('mtdi-detail-open');
        document.body.style.overflow='';document.removeEventListener('keydown',escape);
        window.removeEventListener('resize',resized);return;
      }
      requestAnimationFrame(tick);
      if(document.hidden||active||transitioning){last=now;return;}
      if(now-lastPaint<FRAME_INTERVAL-0.75)return;
      var dt=Math.min(64,now-last);last=now;lastPaint=now;
      angle=(angle+dt*.000075)%(Math.PI*2);paint();
    })(performance.now());
    stage.__mtdiPaint=paint;
  }

  // ── run after every #page-content swap. DOM-scoped work only. ──────────────
  function onContentSwap(){
    document.documentElement.classList.remove('nav-busy');
    armHomeOrbit();
    bootHomeGlobe();
    bootInstrumentConstellation();
    armMtdiOrbit();
    disarmOrphans();
    armChipClicks();
    armDiscSvg();
    bootSplineRobot();
    syncSettingsSeg();
    schedulePlotResize();
  }

  // ══ STARTUP INTRO ════════════════════════════════════════════════════════
  // Self-contained, one boot per document load. The sticky stopper remains pure
  // CSS; the visual scrub is driven by one native requestAnimationFrame loop.
  // There is no external animation dependency and no late asset race.
  function bootStartupIntro(){
    if(window.__introBooted)return true;
    var intro=document.getElementById("startup-intro");
    if(!intro)return false;

    // Reduced motion, or a layout that hides the intro (phones hide it in CSS): skip it
    // entirely instead of waiting for a scroll on an element nobody can see.
    if(reduceMotion()||getComputedStyle(intro).display==='none'){
      window.__introBooted=true;
      intro.remove();
      document.body.classList.remove('intro-active');
      document.body.style.removeProperty('--intro-home-y');
      resetScroll();
      window.__introConsumed=true;
      return true;
    }

    window.__introBooted=true;
    document.body.classList.add('intro-active');
    document.body.style.setProperty('--intro-home-y','100vh');
    intro.scrollTop=0;
    var stage=intro.querySelector('.intro-stage');
    var card=intro.querySelector(".intro-card");
    var eyebrow=intro.querySelector(".intro-eyebrow");
    var topTitle=intro.querySelector(".intro-title-top");
    var bottomTitle=intro.querySelector(".intro-title-bottom");
    var canvas=document.getElementById("intro-shader");
    if(!stage||!card||!eyebrow||!topTitle||!bottomTitle||!canvas){
      intro.remove();
      document.body.classList.remove('intro-active');
      document.body.style.removeProperty('--intro-home-y');
      resetScroll();
      window.__introConsumed=true;
      return true;
    }

    // The supplied intro effect runs only on the landing scene. paint() removes it
    // before the spatial Home handoff starts, avoiding any second-page contamination.
    var stopShader=startIntroShader(canvas);
    var target=0,current=-1,raf=0,lastTs=0,introRange=1,alive=true;
    var clamp=function(v){return Math.max(0,Math.min(1,v));};
    var easeOut=function(v){return 1-Math.pow(1-v,2);};

    function measure(){
      introRange=Math.max(1,intro.scrollHeight-intro.clientHeight);
      updateTarget();
    }

    function updateTarget(){
      target=clamp(intro.scrollTop/introRange);
      // Finish on the same scroll event that reaches Home. Waiting for the damped
      // animation value to crawl from ~.99 to .999 left an invisible fixed overlay
      // intercepting input for roughly a second after Home was already visible.
      if(target>=0.985){consumeIntro();return;}
      if(!raf)raf=requestAnimationFrame(frame);
    }

    function consumeIntro(){
      if(intro.dataset.consuming==='1')return;
      intro.dataset.consuming='1';
      target=1;
      cleanup();
      intro.style.pointerEvents='none';

      // Complete the spatial handoff over a small, fixed interval. Removing the
      // overlay synchronously caused a visible snap when a wheel/trackpad event
      // jumped straight to the end; the old damped loop took about a second and
      // blocked input. This bounded finish is smooth but never feels frozen.
      var start=current<0?0:clamp(current);
      var started=performance.now();
      // A full-range flick gets a little more time than a near-complete scrub. This
      // prevents the old 220 ms whole-scene jump without bringing back the long,
      // input-blocking tail that made Home feel frozen.
      var finishDuration=Math.max(180,Math.min(420,(1-start)*420));
      function finishFrame(now){
        if(!attached(intro))return;
        var t=clamp((now-started)/finishDuration);
        var eased=1-Math.pow(1-t,3);
        paint(start+(1-start)*eased);
        if(t<1){requestAnimationFrame(finishFrame);return;}
        document.body.classList.remove('intro-active');
        document.body.style.removeProperty('--intro-home-y');
        intro.remove();
        window.__introConsumed=true;
      }
      requestAnimationFrame(finishFrame);
    }

    function paint(progress){
      // Original GSAP timing normalised to the complete scroll distance:
      // the titles clear first, the card holds, then it enlarges and fades.
      var enter=clamp(progress/0.385);
      var enterEase=easeOut(enter);
      var exit=clamp((progress-0.615)/0.385);
      var shaderExit=easeOut(clamp((progress-0.48)/0.24));
      // The final quarter is a literal spatial handoff: the intro travels upward
      // while the already-mounted Home shell rises from below at the same rate.
      var handoff=clamp((progress-0.72)/0.28);
      var scale=0.65+(0.70*enterEase)+(0.20*exit);
      var blur=16*(1-enterEase);
      var brightness=0.42+(1.18*enterEase);

      card.style.transform="translate3d(0,0,0) scale("+scale.toFixed(4)+")";
      // Keep a faint final frame present until the entire takeover crossfades out;
      // this prevents a background-only band at the end of the scrub.
      card.style.opacity=Math.max(0.16,1-exit).toFixed(4);
      card.style.filter="blur("+blur.toFixed(3)+"px) brightness("+brightness.toFixed(3)+")";
      eyebrow.style.transform="translate3d(0,"+(-500*enter).toFixed(2)+"px,0)";
      eyebrow.style.opacity=(1-enter).toFixed(4);
      topTitle.style.transform="translate3d("+(-130*enter).toFixed(3)+"%,0,0)";
      topTitle.style.opacity=(1-enter).toFixed(4);
      bottomTitle.style.transform="translate3d("+(130*enter).toFixed(3)+"%,0,0)";
      bottomTitle.style.opacity=(1-enter).toFixed(4);
      canvas.style.opacity=(.38*(1-shaderExit)).toFixed(4);
      stage.style.transform="translate3d(0,"+(-100*handoff).toFixed(4)+"%,0)";
      document.body.style.setProperty('--intro-home-y',((1-handoff)*100).toFixed(4)+'vh');
    }

    function frame(ts){
      raf=0;
      if(!alive||!attached(intro))return;
      if(current<0)current=target;
      var dt=lastTs?Math.min((ts-lastTs)/1000,0.05):0.016;
      lastTs=ts;
      // Time-based damping is consistent on 60/90/120/144 Hz displays.
      var follow=1-Math.exp(-dt/0.16);
      current+=(target-current)*follow;
      if(Math.abs(target-current)<0.00015)current=target;
      paint(current);
      if(current!==target)raf=requestAnimationFrame(frame);
    }

    function cleanup(){
      alive=false;
      if(raf)cancelAnimationFrame(raf);
      intro.removeEventListener("scroll",updateTarget);
      removeEventListener("resize",measure);
      stopShader();
    }

    intro.addEventListener("scroll",updateTarget,{passive:true});
    addEventListener("resize",measure,{passive:true});
    addEventListener("pagehide",cleanup,{once:true});
    measure();
    paint(0);
    return true;

    function startIntroShader(canvas){
      var gl=canvas.getContext("webgl",{
        alpha:false,
        antialias:true,
        depth:false,
        stencil:false,
        powerPreference:"high-performance",
        desynchronized:true
      })||canvas.getContext("experimental-webgl");

      if(!gl)return function(){};

      var vertexSource=
        "attribute vec2 a_pos;void main(){gl_Position=vec4(a_pos,0.0,1.0);}";

      var fragmentSource=[
        "precision highp float;",
        "uniform vec2 u_res;",
        "uniform float u_time;",
        "void main(){",
        "vec2 uv=(gl_FragCoord.xy*2.0-u_res)/min(u_res.x,u_res.y);",
        "float t=u_time*0.04;",
        "float lw=0.0025;",
        "vec3 col=vec3(0.0);",
        "for(int j=0;j<3;j++){",
        "for(int i=0;i<5;i++){",
        "float fi=float(i);",
        "float fj=float(j);",
        "col[j]+=lw*fi*fi/abs(fract(t-0.012*fj+fi*0.012)*5.0-length(uv)+mod(uv.x+uv.y,0.22));",
        "}}",
        "float total=col.r+col.g+col.b;",
        "col=vec3(total*0.14,total*0.42,total*0.95);",
        "gl_FragColor=vec4(col,1.0);",
        "}"
      ].join("\n");

      var compile=function(type,source){
        var shader=gl.createShader(type);
        gl.shaderSource(shader,source);
        gl.compileShader(shader);
        return shader;
      };

      var program=gl.createProgram();
      gl.attachShader(program,compile(gl.VERTEX_SHADER,vertexSource));
      gl.attachShader(program,compile(gl.FRAGMENT_SHADER,fragmentSource));
      gl.linkProgram(program);
      gl.useProgram(program);

      var buffer=gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
      gl.bufferData(
        gl.ARRAY_BUFFER,
        new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),
        gl.STATIC_DRAW
      );

      var position=gl.getAttribLocation(program,"a_pos");
      gl.enableVertexAttribArray(position);
      gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);

      var resolution=gl.getUniformLocation(program,"u_res");
      var time=gl.getUniformLocation(program,"u_time");
      var animationFrame;
      var shaderTime=0;
      var lastFrame=0;
      var stopped=false;

      var resize=function(){
        // Adaptive pixel budget keeps this host smooth while retaining supersampling
        // on laptops. The visual speed is independent of this render resolution.
        var w=Math.max(1,innerWidth),h=Math.max(1,innerHeight);
        var scale=Math.min(devicePixelRatio||1,1.75);
        var pixelBudget=2200000;
        if(w*h*scale*scale>pixelBudget){
          scale=Math.sqrt(pixelBudget/(w*h));
        }
        canvas.width=Math.round(w*scale);
        canvas.height=Math.round(h*scale);
        gl.viewport(0,0,canvas.width,canvas.height);
        gl.uniform2f(resolution,canvas.width,canvas.height);
      };

      var draw=function(now){
        if(stopped)return;
        animationFrame=requestAnimationFrame(draw);

        /*
          Render at the display's native requestAnimationFrame rate. Shader motion
          is delta-time based, so 60/90/120/144 Hz displays keep the original speed.
        */
        if(!lastFrame)lastFrame=now;
        var deltaSeconds=Math.min((now-lastFrame)/1000,0.05);
        lastFrame=now;
        shaderTime=Math.min(20,shaderTime+deltaSeconds*7.2); /* one complete pass */
        gl.uniform1f(time,shaderTime);
        gl.drawArrays(gl.TRIANGLES,0,6);

        // Play exactly once, then hold the final frame. Opacity remains governed by
        // paint(handoff), so stopping motion cannot cause a visual jump into Home.
        if(shaderTime>=20){
          stopped=true;
          canvas.dataset.oneShotComplete='1';
        }
      };

      resize();
      addEventListener("resize",resize,{passive:true});
      animationFrame=requestAnimationFrame(draw);

      return function(){
        stopped=true;
        cancelAnimationFrame(animationFrame);
        removeEventListener("resize",resize);
      };
    }
  }

  // One bounded waiter for Dash to mount app.layout. No external assets are needed.
  function armStartupIntro(){
    if(bootStartupIntro())return;
    var deadline=Date.now()+3000;
    var timer=setInterval(function(){
      if(bootStartupIntro()){clearInterval(timer);return;}
      if(Date.now()>deadline){
        clearInterval(timer);
        var intro=document.getElementById('startup-intro');
        if(intro){
          intro.remove();
          document.body.classList.remove('intro-active');
          document.body.style.removeProperty('--intro-home-y');
          window.__introBooted=true;                   // never retried
          window.__introConsumed=true;
          resetScroll();
          console.warn('[studio] startup intro disabled: Dash shell did not mount.');
        }
      }
    },25);
  }

  function boot(){
    if(window.__studioBooted)return;
    window.__studioBooted=true;

    // ── NAV JITTER FIX ──────────────────────────────────────────────────────
    // dcc.Link calls window.scrollTo(0,0) SYNCHRONOUSLY on click, before the new page
    // is fetched. That made the OLD page visibly jump to the top and only THEN switch.
    // Swallow exactly that scroll; our own instant reset runs on the content swap.
    try{
      var _realScrollTo=window.scrollTo.bind(window);
      window.scrollTo=function(){
        if(window.__suppressNavScroll)return;
        return _realScrollTo.apply(window,arguments);
      };
      try{history.scrollRestoration='manual';}catch(e){}
      // MTDI uses a FLIP-style launch transition. The real Dash click is replayed
      // only after a visual copy of the selected orbital card has travelled from its
      // exact screen position to the full-page content frame. This lets the landing
      // view disappear atomically when the selected live pane is ready.
      function launchMtdiPillar(card){
        if(!card||window.__mtdiTransitioning)return;
        window.__mtdiTransitioning=true;
        var rect=card.getBoundingClientRect();
        var ghost=card.cloneNode(true);
        ghost.removeAttribute('id');
        ghost.querySelectorAll('[id]').forEach(function(el){el.removeAttribute('id');});
        ghost.className='mtdi-launch-ghost';
        Object.assign(ghost.style,{
          left:rect.left+'px',top:rect.top+'px',width:rect.width+'px',height:rect.height+'px'
        });
        document.body.appendChild(ghost);
        var edge=Math.max(14,Math.min(28,window.innerWidth*.025));
        var targetTop=Math.max(68,document.querySelector('header')?.getBoundingClientRect().bottom||68);
        var target={
          left:edge+'px',top:targetTop+'px',width:(window.innerWidth-edge*2)+'px',
          height:Math.max(320,window.innerHeight-targetTop-edge)+'px',borderRadius:'16px'
        };
        if(ghost.animate){
          ghost.animate([
            {left:rect.left+'px',top:rect.top+'px',width:rect.width+'px',height:rect.height+'px',borderRadius:'12px'},
            target
          ],{duration:500,easing:'cubic-bezier(.16,1,.3,1)',fill:'forwards'});
        }else{Object.assign(ghost.style,target);}
        setTimeout(function(){
          window.__mtdiReplay=true;
          card.click();
          window.__mtdiReplay=false;
          setTimeout(function(){
            ghost.remove();
            window.__mtdiTransitioning=false;
          },180);
        },500);
      }
      // In-page view switches (MTDI pillars, BACK buttons) are plain buttons, not
      // links, so no Dash callback is involved in the scroll. Reset here instead of
      // via a pattern-matching clientside callback: Dash treats the FIRST fire of an
      // ALL-pattern input as the initial call and swallows it, so the first pillar
      // click after landing on /mtdi would keep the old scroll position.
      document.addEventListener('click',function(e){
        var t=e.target;
        var pillar=t&&t.closest&&t.closest('.mtdi-enter-card');
        if(pillar&&!window.__mtdiReplay){
          e.preventDefault();
          e.stopImmediatePropagation();
          launchMtdiPillar(pillar);
          return;
        }
        var exportLink=t&&t.closest&&t.closest('#export-btn');
        if(exportLink){
          exportLink.classList.add('export-generating');
          exportLink.textContent='GENERATING REPORT…';
          setTimeout(function(){
            if(exportLink&&exportLink.isConnected){
              exportLink.classList.remove('export-generating');
              exportLink.textContent='EXPORT PDF + NOTION';
            }
          },8000);
        }
        if(t&&t.closest&&(t.closest('.mtdi-enter-card')||t.closest('.back-btn'))){
          // Deliberately NOT requestAnimationFrame: rAF is suspended while the tab is
          // hidden, so a background tab would keep its old scroll offset and jump on
          // return. Reset now and once more after the style swap has been applied.
          resetScroll();
          setTimeout(resetScroll,0);
          setTimeout(resetScroll,250);
        }
        if(t&&t.closest&&(t.closest('#p1-tab-c1')||t.closest('#p1-tab-c2x')||
                         t.closest('#p1-tab-both'))){
          schedulePlotResize();
        }
      },true);
      document.addEventListener('click',function(e){
        var a=e.target&&e.target.closest&&e.target.closest('a[href^="/"]');
        if(!a)return;
        window.__suppressNavScroll=true;
        // The 2px bar is the entire loading affordance: the current page stays fully
        // visible and readable until Dash swaps in the new one.
        document.documentElement.classList.add('nav-busy');
        setTimeout(function(){window.__suppressNavScroll=false;},0);
        // Safety net: never leave the bar spinning if a callback fails.
        clearTimeout(window.__navBusyTimer);
        window.__navBusyTimer=setTimeout(function(){
          document.documentElement.classList.remove('nav-busy');
        },6000);
      },true);
    }catch(e){}

    // The permanent shader supplies the shared foundation; the original intro
    // shader runs above it only while the startup takeover exists.
    bootPageShader();
    armStartupIntro();      // once per document load, never again
    bootTypewriter();
    bootAlertStack();

    // Dash may resolve the first routed page before the direct-child observer is
    // attached. This tiny route-safe check closes that race and also handles a later
    // return to /mtdi; armMtdiOrbit is guarded, so an active stage is never restarted.
    setInterval(function(){
      var stage=document.getElementById('mtdi-orbit-stage-v2');
      if(stage&&stage.dataset.mtdiV2!=='1')armMtdiOrbit();
      var homeStage=document.getElementById('home-module-orbit-stage');
      if(homeStage&&homeStage.dataset.homeOrbit!=='1')armHomeOrbit();
      var globe=document.getElementById('home-module-globe');
      if(globe&&globe.dataset.globeInit!=='1')bootHomeGlobe();
      var gallery=document.getElementById('mtdi-constellation-canvas');
      if(gallery&&gallery.dataset.galleryInit!=='1')bootInstrumentConstellation();
      var splineHost=document.getElementById('nvtra-spline-host');
      if(splineHost&&splineHost.dataset.splineInit!=='1')bootSplineRobot();
    },500);

    // ONE observer, scoped to the routed container, childList only, debounced.
    // It never re-runs the global boots above — that is what made every Dash value
    // update restart the decorative effects.
    var pc=document.getElementById('page-content');
    if(pc){
      var timer=null;
      new MutationObserver(function(records){
        var structural=false;
        for(var i=0;i<records.length;i++){
          if(records[i].addedNodes&&records[i].addedNodes.length){structural=true;break;}
        }
        if(!structural)return;
        if(timer)return;
        timer=setTimeout(function(){timer=null;onContentSwap();},120);
      }).observe(pc,{childList:true});
    }
    onContentSwap();
  }

  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',boot);}
  else{boot();}
})();
"""
