/* Two circuit boards in 3D: the SRC1/GY-271 ch1probe breakout and the Ch2
   board. Adapted from the operator's own three.js scene so the geometry, the
   procedural surface textures and the lighting are his, unchanged in substance.

   Differences from the standalone file, all of them required to live inside the
   instrument rather than in a blank page:
     - it mounts into a given <canvas> instead of taking over the document, so
       sizing, hit testing and the two viewports come from the canvas rectangle;
     - the clear colour is transparent, because the instrument is dark and the
       original page was white;
     - it only renders while the canvas is on screen and the tab is visible, so a
       scrolled-away board costs nothing on a small board.

   THREE is expected on window; the loader below fetches it once. */
(function(){
  if (window.__i3Boards) return;
  const THREE = null; // resolved at mount time from window.THREE

  function build(T, canvas){
    const renderer=new T.WebGLRenderer({canvas,antialias:true,alpha:true});
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
    renderer.setClearColor(0x000000,0);
    renderer.outputColorSpace=T.SRGBColorSpace;
    renderer.toneMapping=T.ACESFilmicToneMapping;
    renderer.toneMappingExposure=1.05;
    renderer.shadowMap.enabled=true;
    renderer.shadowMap.type=T.PCFSoftShadowMap;

    const mat=(c,metal=0,rough=.5)=>new T.MeshStandardMaterial({color:c,metalness:metal,roughness:rough});
    const M={gold:mat('#bba45b',.72,.32),silver:mat('#c8ccca',.83,.27),solder:mat('#a7aca8',.8,.3),
      black:mat('#222629'),ceramic:mat('#c4bca3'),blue:mat('#087deb',.04,.32),disc:mat('#009ee8',0,.25),
      copper:mat('#cc834e',.8,.3),wire:mat('#e9e3b7'),core:mat('#1689c7'),dark:mat('#333638'),
      pcb:mat('#d5b852',.06,.63),navy:mat('#004779',.1,.45),trace:mat('#bc875e',.65,.4)};

    function mesh(g,geo,m,x=0,y=0,z=0){let o=new T.Mesh(geo,m);o.position.set(x,y,z);g.add(o);return o}
    const roundedCache=new Map();
    function box(g,x,y,z,w,d,h,m){
      let r=Math.min(w,d,h)*.10,key=[w,d,h,r].join(',');let geo=roundedCache.get(key);
      if(!geo){let shape=new T.Shape(),a=-w/2,b=-d/2;
        shape.moveTo(a+r,b);shape.lineTo(a+w-r,b);shape.quadraticCurveTo(a+w,b,a+w,b+r);
        shape.lineTo(a+w,b+d-r);shape.quadraticCurveTo(a+w,b+d,a+w-r,b+d);
        shape.lineTo(a+r,b+d);shape.quadraticCurveTo(a,b+d,a,b+d-r);
        shape.lineTo(a,b+r);shape.quadraticCurveTo(a,b,a+r,b);
        geo=new T.ExtrudeGeometry(shape,{depth:Math.max(.001,h-2*r),bevelEnabled:true,bevelThickness:r,
          bevelSize:r*.35,bevelSegments:2,curveSegments:3,steps:1});
        geo.translate(0,0,-h/2+r);roundedCache.set(key,geo)}
      let o=mesh(g,geo,m,x,y,z);o.castShadow=true;o.receiveShadow=true;return o}
    function cyl(g,x,y,z,r,h,m,r2=r){let o=mesh(g,new T.CylinderGeometry(r2,r,h,32),m,x,y,z);o.rotation.x=Math.PI/2;return o}
    function ball(g,x,y,z,rx,ry,rz,m){let o=mesh(g,new T.SphereGeometry(1,16,12),m,x,y,z);o.scale.set(rx,ry,rz);return o}
    function line(g,points,r,m){let p=points.map(p=>new T.Vector3(...p));
      return mesh(g,new T.TubeGeometry(new T.CatmullRomCurve3(p),Math.max(12,points.length*8),r,8,false),m)}
    function ring(g,x,y,z,outer,inner,m){let s=new T.Shape();s.absarc(0,0,outer,0,Math.PI*2,false);
      let h=new T.Path();h.absarc(0,0,inner,0,Math.PI*2,true);s.holes.push(h);
      return mesh(g,new T.ExtrudeGeometry(s,{depth:.07,bevelEnabled:false,curveSegments:32}),m,x,y,z)}
    function boardPlate(g,w,h,t,m,holes){let s=new T.Shape();
      s.moveTo(-w/2,-h/2);s.lineTo(w/2,-h/2);s.lineTo(w/2,h/2);s.lineTo(-w/2,h/2);s.closePath();
      holes.forEach(([x,y,r])=>{let p=new T.Path();p.absarc(x,y,r,0,Math.PI*2,true);s.holes.push(p)});
      return mesh(g,new T.ExtrudeGeometry(s,{depth:t,bevelEnabled:false,curveSegments:24}),m,0,0,-t)}
    function label(g,text,x,y,z,w,h,color='#deded4',back=false){
      let c=document.createElement('canvas');c.width=512;c.height=128;let ctx=c.getContext('2d');
      ctx.fillStyle=color;ctx.font='bold 72px Arial';ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText(text,256,64);let tex=new T.CanvasTexture(c);tex.colorSpace=T.SRGBColorSpace;
      let o=mesh(g,new T.PlaneGeometry(w,h),new T.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false,side:T.DoubleSide}),x,y,z);
      if(back)o.rotation.y=Math.PI;return o}
    let seed=2817;function rnd(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296}
    function pad(g,x,y,z=.03){let o=ball(g,x,y,z,.6,.73,.18,M.solder);o.rotation.z=rnd()*3;ring(g,x,y,z-.07,.69,.22,M.gold)}
    function dip(g,x,y){box(g,x,y,1.3,4.8,9.4,2.5,M.black);
      for(let side of [-1,1])for(let k=0;k<4;k++){let yy=y+(k-1.5)*2.54;
        line(g,[[x+side*2.2,yy,1.2],[x+side*3.2,yy,1],[x+side*3.4,yy,.12]],.21,M.silver);pad(g,x+side*3.4,yy)}
      label(g,'TL072CP',x,y+1,2.565,3.8,1);label(g,'22M   36',x,y-.45,2.568,3.5,.7);cyl(g,x,y-4,2.56,.6,.03,M.dark)}
    function resistor(g,x,y,vertical=false){let q=new T.Group();q.position.set(x,y,0);
      if(vertical)q.rotation.z=Math.PI/2;g.add(q);
      line(q,[[-4,0,.1],[-3.1,0,1],[3.1,0,1],[4,0,.1]],.14,M.silver);
      let o=cyl(q,0,0,1,.67,4.8,mat('#68b9da'));o.rotation.z=Math.PI/2;
      for(let [i,c] of ['#775135','#16191e','#ed3434','#28409d','#835833'].entries()){
        let b=cyl(q,-1.65+i*.78,0,1,.682,.28,mat(c));b.rotation.z=Math.PI/2}
      pad(q,-4,0);pad(q,4,0)}
    function disc(g,x,y){line(g,[[x-.65,y,.05],[x-.65,y,1.25],[x+.65,y,1.25],[x+.65,y,.05]],.12,M.silver);
      ball(g,x,y,1.5,1.35,.65,.86,M.disc)}
    function terminal(g,x,y,n){box(g,x,y,2.8,6.8,n*5.08,5.6,M.blue);box(g,x-.8,y,5.2,5.2,n*5.08,1.45,M.blue);
      box(g,x-3.4,y,.5,.65,n*5.08,1,M.blue);
      for(let i=0;i<n;i++){let yy=y+(i-(n-1)/2)*5.08;
        ring(g,x-.65,yy,5.91,1.92,1.58,M.blue);cyl(g,x-.65,yy,5.9,1.59,.03,M.dark);cyl(g,x-.65,yy,5.96,1.34,.14,M.silver);
        let slot=box(g,x-.65,yy,6.045,2.15,.22,.055,M.dark);slot.rotation.z=.2+(i%2)*.55;
        box(g,x+3.41,yy,2.6,.03,3.65,3.1,M.dark);box(g,x+3.44,yy,2.45,.03,2.9,2.5,M.silver);
        box(g,x+3.47,yy,2.5,.03,2.15,1.65,M.dark);
        for(let sign of [-1,1])box(g,x+3.5,yy+sign*1.65,2.6,.12,.32,3.3,M.blue);
        for(let k=0;k<3;k++)box(g,x+3.51,yy,1.55+k*.25,.025,2.5,.07,M.silver);
        if(i<n-1)box(g,x-.8,yy+2.54,5.97,5,.055,.035,mat('#0766ac'));
        cyl(g,x,yy,-.8,.35,2.1,M.silver)}}
    function bulkcap(g,x,y,r=3.5,h=10){
      cyl(g,x,y,.35,r+.08,.55,M.dark);cyl(g,x,y,h/2+.3,r,h,M.black);
      for(let z of [.9,h-.15])mesh(g,new T.TorusGeometry(r-.12,.13,8,40),M.dark,x,y,z);
      cyl(g,x,y,h+.33,r*.87,.1,M.silver);cyl(g,x,y,h+.4,r*.74,.035,M.silver);
      for(let a of [-.72,.72]){let slit=box(g,x,y,h+.44,r*1.45,.055,.015,M.dark);slit.rotation.z=a}
      let c=document.createElement('canvas');c.width=1024;c.height=512;let ctx=c.getContext('2d');
      ctx.fillStyle='#171b1b';ctx.fillRect(0,0,1024,512);ctx.fillStyle='#a4aaa6';ctx.fillRect(70,0,135,512);
      ctx.fillStyle='#242a29';ctx.font='bold 72px Arial';for(let yy=50;yy<500;yy+=100)ctx.fillText('−',112,yy);
      ctx.fillStyle='#d6dbd4';ctx.font='bold 43px Arial';
      for(let xx of [250,650]){ctx.fillText('HITANO',xx,125);ctx.fillText('220µF 16V',xx,220);
        ctx.fillText('105°C',xx,320);ctx.font='30px Arial';ctx.fillText('ECR   09',xx,410);ctx.font='bold 43px Arial'}
      let tex=new T.CanvasTexture(c);tex.colorSpace=T.SRGBColorSpace;
      let sleeve=mesh(g,new T.CylinderGeometry(r+.016,r+.016,h-.9,64,1,true),new T.MeshStandardMaterial({map:tex,roughness:.38}),x,y,h/2+.3);
      sleeve.rotation.x=Math.PI/2;
      for(let dx of [-1,1])cyl(g,x+dx,y,-.2,.22,1,M.silver)}
    function inductor(g,x,y,h=8){cyl(g,x,y,.6,3.3,1.1,M.dark);cyl(g,x,y,h/2,2.8,h-1,M.dark);
      cyl(g,x,y,h-.6,3.4,1.2,M.dark);cyl(g,x,y,h+.02,2.8,.05,mat('#595c5a'));label(g,'101',x,y,h+.06,3.6,1.4)}
    function trace(g,pts,z=-1.64,width=.55,material=M.trace){
      for(let i=1;i<pts.length;i++){let a=pts[i-1],b=pts[i],dx=b[0]-a[0],dy=b[1]-a[1];
        let o=box(g,(a[0]+b[0])/2,(a[1]+b[1])/2,z,Math.hypot(dx,dy)+width,width,.045,material);
        o.rotation.z=Math.atan2(dy,dx)}}
    function smd(g,x,y,w,d,h,m){box(g,x,y,h/2+.08,w,d,h,m);
      box(g,x-w/2+.15,y,h/2+.08,.3,d+.05,h+.08,M.silver);box(g,x+w/2-.15,y,h/2+.08,.3,d+.05,h+.08,M.silver)}

    function big(){let g=new T.Group();
      boardPlate(g,45,112,1.6,M.pcb,[[-19,-52,1.5],[19,-52,1.5],[-19,52,1.5],[19,52,1.5]]);
      for(let y of [-38,-14,10]){dip(g,1,y);terminal(g,-15,y,2);terminal(g,15,y,3);
        resistor(g,1,y+8);resistor(g,1,y+5.8);resistor(g,1,y-7);resistor(g,-7,y,true);resistor(g,8,y,true);
        disc(g,-2,y-9);disc(g,5,y-9)}
      terminal(g,15,46,2);box(g,-7,44,3,6,2.7,5,M.blue);box(g,4,44,3,6,2.7,5,M.blue);
      inductor(g,-2,50,11);inductor(g,12,37,9);inductor(g,-10,29,8);inductor(g,10,27,8);
      for(let p of [[-18,34],[-18,24],[19,33],[19,25]])bulkcap(g,p[0],p[1],3.2,9.5);
      for(let x of [-5,4]){box(g,x,41,2.9,3,2.2,3.5,M.black);
        for(let a of [-.8,0,.8])line(g,[[x+a,40,2],[x+a,39.2,.1]],.13,M.silver)}
      resistor(g,-9,39);resistor(g,8,39);disc(g,-1,25);disc(g,5,23);disc(g,1,44);
      mesh(g,new T.TorusGeometry(4.8,2.1,20,64),M.core,0,35,4);
      for(let i=0;i<48;i++){let a=i/48*Math.PI*2,p=[];
        for(let j=0;j<=28;j++){let b=j/28*Math.PI*2,aa=a+b/48;let r=4.8+2.18*Math.cos(b);
          p.push([r*Math.cos(aa),35+r*Math.sin(aa),4+2.18*Math.sin(b)])}
        line(g,p,.18,M.copper)}
      for(let dy of [-2.54,2.54]){
        line(g,[[18.4,46+dy,2.8],[24,46+dy,3],[32,48+dy,5],[39,53+dy,6],[49,56+dy,5]],.42,M.wire);
        line(g,[[49,56+dy,5],[52,57+dy,5.4]],.21,M.copper)}
      trace(g,[[-21,-54],[-21,54],[21,54],[21,-54],[-21,-54]],-1.64,1.6);
      trace(g,[[-2,-51],[-2,21],[-5,21],[-5,48],[13,48]],-1.64,1.1);
      trace(g,[[1,-51],[1,21],[19,21]],-1.64,1.1);
      for(let y of [-38,-14,10]){
        for(let side of [-1,1]){
          for(let k=0;k<4;k++){let yy=y+(k-1.5)*2.54,xx=1+side*3.4;
            ball(g,xx,yy,-1.85,.9,.8,.42,M.solder);
            trace(g,[[xx,yy],[xx+side*(2+k*.75),yy],[xx+side*(2+k*.75),y+(k-1.5)*4],[side*15,y+(k-1.5)*4]],-1.64,.6)}
          for(let k=0;k<(side===1?3:2);k++)ball(g,side*15,y+(k-(side===1?1:.5))*5.08,-1.85,1.6,1.6,.5,M.solder)}
        trace(g,[[-21,y-11],[-5,y-11],[-5,y-7]],-1.64,.9);
        trace(g,[[21,y+11],[4,y+11],[4,y+8]],-1.64,.9)}
      for(let k=0;k<25;k++){let x=-16+(k%5)*7,y=26+Math.floor(k/5)*5;
        ball(g,x,y,-1.9,1,.75,.4,M.solder);
        if(k%3)trace(g,[[x,y],[x+3,y],[x+3,y+3]],-1.64,.8)}
      label(g,'CH2F',-18,44,-1.72,8,1.9,'#bd8555',true);return g}

    function small(){let g=new T.Group(),holes=[];
      for(let i=0;i<5;i++)holes.push([-5.08+i*2.54,-6.2,.62]);
      boardPlate(g,14,14,1,M.navy,holes);
      for(let h of holes){ring(g,h[0],h[1],.02,1.02,h[2],M.gold);ring(g,h[0],h[1],-1.075,1.02,h[2],M.gold)}
      box(g,.3,1.5,.55,4,4,1,M.black);label(g,'HMC5883',.3,1.8,1.07,3.3,.6);
      for(let s of [-1,1])for(let i=0;i<4;i++){
        box(g,.3+s*2.13,.3+i*.8,.24,.48,.34,.35,M.silver);
        box(g,-.9+i*.8,1.5+s*2.13,.24,.34,.48,.35,M.silver)}
      smd(g,-5,0,2,3.2,1.3,mat('#dba04d'));smd(g,-3.4,5.25,1.5,1.8,.9,M.ceramic);smd(g,.5,5.65,1.8,1,.6,M.ceramic);
      box(g,-3.2,-3.2,.6,2.7,1.65,1.05,M.black);
      for(let x of [-4.1,-3.2,-2.3]){box(g,x,-4.25,.27,.38,.65,.25,M.silver);box(g,x,-2.2,.27,.38,.6,.25,M.silver)}
      for(let p of [[4.8,4.7],[4.8,2.8],[4.8,1],[4,-1],[2.5,-3],[.1,-3.5],[-.8,-1.6]])smd(g,p[0],p[1],1.55,.75,.42,M.black);
      label(g,'X →',-3.3,2.8,.025,2.8,1);label(g,'Y ↑',-3,1.4,.025,2.5,.9);
      for(let i=0;i<5;i++){let x=-5.08+i*2.54;
        trace(g,[[x,-5.05],[x,-4.5+i*.55],[x*.4,-4.5+i*.55],[x*.4,-.6+i*.45]],-1.06,.16,mat('#105984',.25,.48));
        let l=label(g,['VCC','GND','SCL','SDA','DRDY'][i],x,-3.55,-1.1,2.1,.7,'#ffffff',true);l.rotation.z=Math.PI/2}
      label(g,'GY-271',0,4.5,-1.09,6.5,1.4,'#ffffff',true);
      for(let p of [[-4,5],[-4,4.2],[2,.2],[0,-.3],[-2,-1.5]]){
        cyl(g,p[0],p[1],-1.08,.19,.05,M.dark);ring(g,p[0],p[1],-1.1,.3,.18,M.gold)}
      return g}

    function surface(base,grain,weave=false){
      let c=document.createElement('canvas');c.width=c.height=512;let ctx=c.getContext('2d');
      let im=ctx.createImageData(512,512),rgb=new T.Color(base);
      for(let y=0;y<512;y++)for(let x=0;x<512;x++){
        let n=(rnd()-.5)*grain+(weave?Math.sin(x*Math.PI/2)*2+Math.sin(y*Math.PI/2)*2:0),i=(y*512+x)*4;
        im.data[i]=Math.max(0,Math.min(255,rgb.r*255+n));
        im.data[i+1]=Math.max(0,Math.min(255,rgb.g*255+n));
        im.data[i+2]=Math.max(0,Math.min(255,rgb.b*255+n));im.data[i+3]=255}
      ctx.putImageData(im,0,0);let t=new T.CanvasTexture(c);
      t.wrapS=t.wrapT=T.RepeatWrapping;t.colorSpace=T.SRGBColorSpace;return t}
    for(let spec of [['pcb','#e3ce70',16,true,.58,.055],['navy','#075386',9,false,.35,.012],
      ['black','#303333',15,false,.62,.025],['blue','#1489e8',6,false,.28,.018],
      ['dark','#4b4d4b',22,false,.78,.08],['copper','#d79c66',8,false,.26,.012],
      ['silver','#d9dcd9',8,false,.24,.012],['solder','#b9bbb5',20,false,.31,.055]]){
      let t=surface(spec[1],spec[2],spec[3]);M[spec[0]].color.set('white');M[spec[0]].map=t;
      M[spec[0]].bumpMap=t;M[spec[0]].bumpScale=spec[5];M[spec[0]].roughness=spec[4]}
    M.gold.roughness=.28;M.gold.metalness=.85;

    function detailBoard(g,smallBoard){
      let t=smallBoard?1:1.6,w=smallBoard?14:45,h=smallBoard?14:112;
      const edge=mat(smallBoard?'#94b5a4':'#e5d6a0',0,.8);
      for(let z of [-t*.3,-t*.65]){box(g,0,h/2+.004,z,w,.013,.045,edge);box(g,0,-h/2-.004,z,w,.013,.045,edge);
        box(g,-w/2-.004,0,z,.013,h,.045,edge);box(g,w/2+.004,0,z,.013,h,.045,edge)}
      if(smallBoard){const tr=mat('#105984',.25,.48);
        for(let pts of [[[-4,4],[-2,4],[-2,2]],[[-4,-2],[-4,-1],[-1,-1]],[[2,4],[3.8,4],[3.8,2]],
          [[0,-4.8],[0,-4.3],[2,-4.3],[2,-2]],[[5,-4.8],[5,-2],[3,-2]]])trace(g,pts,.025,.13,tr);
        for(let p of [[-5.8,5.7],[-5.8,4.8],[3.4,3.6],[3.4,-3.8],[-1,-4.5]]){
          ring(g,p[0],p[1],.028,.24,.1,M.gold);cyl(g,p[0],p[1],.025,.10,.025,M.dark)}
        label(g,'104',4.8,4.7,.52,1,.32);label(g,'472',4.8,2.8,.52,1,.32);label(g,'472',4.8,1,.52,1,.32);
        label(g,'106',-5,0,1.405,1.45,.55,'#68512b');cyl(g,-1.1,2.85,1.075,.15,.018,M.dark)}
      else{for(let y of [-38,-14,10]){
          for(let x of [-8,9])for(let dy of [-8,8]){ring(g,x,y+dy,.015,.35,.16,M.gold);cyl(g,x,y+dy,.02,.15,.02,M.dark)}
          for(let x of [-5,7]){let o=ball(g,x,y-9,.06,.75,.48,.065,mat('#bfa753',.1,.75));o.rotation.z=rnd()*3}}
        for(let i=0;i<70;i++){let x=(rnd()-.5)*41,y=(rnd()-.5)*107;
          if(Math.abs(x)<17&&y<21)continue;
          box(g,x,y,.015,.06+rnd()*.14,.07+rnd()*.17,.012,mat('#cbbb72',0,.9))}}
      g.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;
        if(o.material.metalness>.5)o.material.envMapIntensity=.9}})}

    const studio=new T.Scene();studio.background=new T.Color('#aaaeb2');
    function panel(x,y,z,w,h,power){let o=new T.Mesh(new T.PlaneGeometry(w,h),
      new T.MeshBasicMaterial({color:new T.Color(power,power,power)}));o.position.set(x,y,z);o.lookAt(0,0,0);studio.add(o)}
    panel(-25,25,35,25,45,5);panel(30,10,10,12,50,3);panel(0,-30,20,40,9,2);
    const pmrem=new T.PMREMGenerator(renderer);const environment=pmrem.fromScene(studio,.07).texture;pmrem.dispose();

    /* Which board this canvas shows. The Sensor Showcase wants both side by
       side; the Ch1 and Ch2 tabs each want only the sensor that
       actually takes that measurement, so a canvas can ask for one. Building
       only what is asked for also means a single-board canvas pays for one
       scene rather than two. */
    const which=(canvas.getAttribute('data-i3-boards')||'both').toLowerCase();
    const wantMag=(which==='both'||which==='c1'||which==='ch1'||which==='true');
    const wantEf=(which==='both'||which==='ef'||which==='ch2f'||which==='ch2'||which==='true');
    const specs=[];
    if(wantMag)specs.push([small(),20]);
    if(wantEf)specs.push([big(),118]);
    const views=[];
    for(let spec of specs){
      const model=spec[0],size=spec[1];
      let scene=new T.Scene();scene.environment=environment;
      detailBoard(model,size<30);
      scene.add(new T.HemisphereLight(0xffffff,0x77796c,.7));
      let light=new T.DirectionalLight(0xffffff,2.6);light.position.set(-60,80,120);light.castShadow=true;
      light.shadow.mapSize.set(2048,2048);
      let extent=size<30?14:80;
      Object.assign(light.shadow.camera,{left:-extent,right:extent,top:extent,bottom:-extent,near:1,far:300});
      light.shadow.bias=-.00012;light.shadow.normalBias=size<30?.015:.045;light.shadow.radius=3;
      scene.add(light);
      let fill=new T.DirectionalLight(0xd6e6ff,.6);fill.position.set(60,-40,35);scene.add(fill);
      let pivot=new T.Group();pivot.add(model);pivot.rotation.set(-.48,.30,-.16);scene.add(pivot);
      let camera=new T.PerspectiveCamera(35,1,.1,1500);camera.position.set(0,0,size*1.75);
      views.push({scene,pivot,camera,size,zoom:1})}

    /* Both boards share one canvas, split the long way. The hit test uses the
       canvas rectangle rather than the window, so the split follows the panel. */
    function rects(){const w=canvas.clientWidth,h=canvas.clientHeight;
      if(views.length<2)return[[0,0,w,h]];
      return (w>=h*1.25)?[[0,0,w*.36,h],[w*.36,0,w*.64,h]]
                        :[[0,h*.55,w,h*.45],[0,0,w,h*.55]]}
    function pick(clientX,clientY){if(views.length<2)return 0;
      const r=canvas.getBoundingClientRect();
      const x=clientX-r.left,y=clientY-r.top,w=canvas.clientWidth;
      return (w>=canvas.clientHeight*1.25)?(x<w*.36?0:1):(y<canvas.clientHeight*.45?0:1)}

    let active=null,last={x:0,y:0};
    canvas.addEventListener('pointerdown',e=>{active=views[pick(e.clientX,e.clientY)];
      last={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);e.preventDefault()});
    canvas.addEventListener('pointermove',e=>{if(!active)return;
      let q=new T.Quaternion().setFromEuler(new T.Euler((e.clientY-last.y)*.009,(e.clientX-last.x)*.009,0));
      active.pivot.quaternion.premultiply(q);last={x:e.clientX,y:e.clientY}});
    for(const t of ['pointerup','pointercancel','pointerleave'])canvas.addEventListener(t,()=>{active=null});
    canvas.addEventListener('wheel',e=>{e.preventDefault();let v=views[pick(e.clientX,e.clientY)];
      v.zoom=Math.max(.35,Math.min(2.5,v.zoom*Math.exp(e.deltaY*.001)))},{passive:false});
    canvas.addEventListener('dblclick',e=>{let v=views[pick(e.clientX,e.clientY)];
      v.pivot.rotation.set(-.48,.30,-.16);v.zoom=1});
    /* Same hand-control contract used by the Earth and Plotly scenes. A pinch
       selects this canvas; palm motion supplies inertial rotation and two-hand
       spread supplies zoom. */
    canvas.__i3LegacyHandControls={
      physics(delta){const v=active||views[0];if(!v)return;const q=new T.Quaternion().setFromEuler(new T.Euler(delta[1],delta[0],delta[2]||0));v.pivot.quaternion.premultiply(q)},
      rotate(dx,dy){const v=active||views[0];if(!v)return;const q=new T.Quaternion().setFromEuler(new T.Euler(dy*.009,dx*.009,0));v.pivot.quaternion.premultiply(q)},
      zoom(delta){for(const v of views)v.zoom=Math.max(.35,Math.min(2.5,v.zoom*Math.exp(delta*.001)))},
      reset(){for(const v of views){v.pivot.rotation.set(-.48,.30,-.16);v.zoom=1}}
    };

    let onScreen=true,raf=0;
    const io=new IntersectionObserver(en=>{onScreen=en[0].isIntersecting;},{rootMargin:'120px'});
    io.observe(canvas);
    function frame(){
      raf=requestAnimationFrame(frame);
      if(!onScreen||document.hidden||!canvas.isConnected)return;
      const w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h)return;
      const need=Math.floor(w*renderer.getPixelRatio());
      if(canvas.width!==need)renderer.setSize(w,h,false);
      renderer.setScissorTest(true);
      const rs=rects();
      views.forEach((v,i)=>{const r=rs[i];
        renderer.setViewport(r[0],r[1],r[2],r[3]);renderer.setScissor(r[0],r[1],r[2],r[3]);
        v.camera.aspect=r[2]/r[3];
        v.camera.position.z=v.size*1.75*v.zoom*Math.max(1,1/v.camera.aspect);
        v.camera.updateProjectionMatrix();renderer.render(v.scene,v.camera)});
    }
    frame();
    return {dispose(){cancelAnimationFrame(raf);io.disconnect();delete canvas.__i3LegacyHandControls;renderer.dispose()}};
  }

  let loading=null;
  function ensureThree(){
    if(window.THREE)return Promise.resolve(window.THREE);
    if(loading)return loading;
    loading=new Promise((res,rej)=>{const s=document.createElement('script');
      s.src='/_i3/three.js';s.onload=()=>res(window.THREE);
      s.onerror=()=>rej(new Error('three.js failed to load'));document.head.appendChild(s)});
    return loading;
  }

  function mount(canvas){
    if(!canvas||canvas.dataset.boardsInit==='1')return;
    canvas.dataset.boardsInit='1';
    ensureThree().then(T=>{try{canvas.__i3Boards=build(T,canvas)}
      catch(err){console.error('[studio] boards scene failed',err);canvas.dataset.boardsInit='0'}})
      .catch(err=>{console.error('[studio]',err);canvas.dataset.boardsInit='0'});
  }
  function scan(){document.querySelectorAll('canvas[data-i3-boards]').forEach(mount)}
  window.__i3Boards={mount,scan};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',scan);else scan();
  new MutationObserver(scan).observe(document.documentElement,{childList:true,subtree:true});
})();
