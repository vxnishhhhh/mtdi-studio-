/* Lunar Gravity: a moon with a particle ring and an asteroid belt, ported from the
   React Three Fiber component to plain three.js so it runs inside the Dash page.
   The canvas registers the same hand-control contract as the Earth and the
   constellation (canvas.__ivLegacyHandControls = {physics, rotate, zoom}), so a pinch
   takes hold of it, the shared GesturePhysics momentum spins it, a peace sign rotates
   it directly and two hands zoom it. Clicking (or the first hold) releases the ring. */
(function(){
  if(window.__ivLunarMount)return;
  var RADIUS=2.0,COUNT=40000,ASTEROIDS=75;

  function buildRing(){
    var pos=new Float32Array(COUNT*3),col=new Float32Array(COUNT*3),rnd=new Float32Array(COUNT);
    for(var i=0;i<COUNT;i++){
      var angle=Math.random()*Math.PI*2;
      var rDist=Math.pow(Math.random(),1.5);
      var radius=2.2+rDist*2.2;
      var thickness=0.4-rDist*0.2;
      var ySpread=(Math.random()+Math.random()+Math.random()-1.5);
      pos[i*3]=Math.cos(angle)*radius;pos[i*3+1]=ySpread*thickness;pos[i*3+2]=Math.sin(angle)*radius;
      var intensity=1.0-rDist,p=Math.random(),r,g,b;
      if(p<0.80){r=0.25;g=0.30;b=0.35;}else if(p<0.92){r=0.0;g=0.6;b=0.8;}else{r=0.6;g=0.2;b=0.8;}
      r=Math.min(1,Math.max(0,r+(Math.random()-0.5)*0.1));g=Math.min(1,Math.max(0,g+(Math.random()-0.5)*0.1));b=Math.min(1,Math.max(0,b+(Math.random()-0.5)*0.1));
      var sparkle=Math.random()>0.95?2.5:1.0;
      col[i*3]=r*intensity*sparkle;col[i*3+1]=g*intensity*sparkle;col[i*3+2]=b*intensity*sparkle;
      rnd[i]=Math.random();
    }
    return {pos:pos,col:col,rnd:rnd};
  }

  function generateAsteroids(count){
    var data=[];
    for(var i=0;i<count;i++){
      data.push({
        angle:Math.random()*Math.PI*2,
        baseRadius:2.8+Math.random()*2.0,
        radialAmplitude:0.5+Math.random()*1.5,
        radialSpeed:0.15+Math.random()*0.25,
        phase:Math.random()*Math.PI*2,
        zOffset:(Math.random()-0.5)*0.8,
        speed:(0.04+Math.random()*0.08)*(Math.random()>0.5?1:-1),
        rx:Math.random()*Math.PI,ry:Math.random()*Math.PI,rz:Math.random()*Math.PI,
        rsx:(Math.random()-0.5)*0.05,rsy:(Math.random()-0.5)*0.05,rsz:(Math.random()-0.5)*0.05,
        scale:0.02+Math.pow(Math.random(),4)*0.18
      });
    }
    data.sort(function(a,b){return b.scale-a.scale;});
    return data;
  }

  window.__ivLunarMount=function(host){
    if(!window.THREE||host.dataset.lunarInit==='1')return;
    host.dataset.lunarInit='1';
    var THREE=window.THREE;
    var canvas=document.createElement('canvas');canvas.className='iv-lunar-canvas';canvas.setAttribute('aria-label','Lunar gravity: pinch to hold, click to release the ring');host.appendChild(canvas);
    var renderer;
    try{renderer=new THREE.WebGLRenderer({canvas:canvas,antialias:true,alpha:true,powerPreference:'high-performance'});}
    catch(e){host.textContent='WebGL is not available in this browser.';return;}
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
    var scene=new THREE.Scene();
    var camera=new THREE.PerspectiveCamera(45,1,0.1,100);camera.position.set(0,4,10);camera.lookAt(0,0,0);
    var camDist=camera.position.length(),camDir=camera.position.clone().normalize();

    /* Lighting: one hard sun from the upper right, a cool earthshine fill on the dark limb,
       a cyan rim so the silhouette reads against the page's field-line background. */
    scene.add(new THREE.AmbientLight(0x9fb8ff,0.10));
    scene.add(new THREE.HemisphereLight(0x6f9cff,0x0a0614,0.22));
    var sun=new THREE.DirectionalLight(0xfff4e0,3.2);sun.position.set(9,4,6);scene.add(sun);
    var fill=new THREE.DirectionalLight(0x3b6fd6,0.35);fill.position.set(-6,-2,-4);scene.add(fill);
    var rim=new THREE.DirectionalLight(0x31d7e6,1.1);rim.position.set(-4,3,-7);scene.add(rim);

    var group=new THREE.Group();group.rotation.x=Math.PI/8;scene.add(group);
    var tex=new THREE.TextureLoader().load('/assets/lunar/moon.jpg');tex.colorSpace=THREE.SRGBColorSpace;

    tex.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy?renderer.capabilities.getMaxAnisotropy():1);tex.colorSpace=THREE.SRGBColorSpace;
    var moon=new THREE.Mesh(new THREE.SphereGeometry(RADIUS,96,96),new THREE.MeshStandardMaterial({map:tex,bumpMap:tex,bumpScale:0.045,roughness:0.92,metalness:0.0}));
    group.add(moon);
    /* soft corona behind the disc: an additive sprite that keeps the moon from looking pasted on */
    (function(){var c=document.createElement('canvas');c.width=c.height=256;var g=c.getContext('2d');var grd=g.createRadialGradient(128,128,70,128,128,128);grd.addColorStop(0,'rgba(120,190,255,0.32)');grd.addColorStop(.55,'rgba(80,150,255,0.08)');grd.addColorStop(1,'rgba(40,90,200,0)');g.fillStyle=grd;g.fillRect(0,0,256,256);
      var halo=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));halo.scale.setScalar(RADIUS*3.3);halo.position.z=-RADIUS*0.6;scene.add(halo);})();

    /* ring */
    var ringState='hidden';var uniforms={uProgress:{value:0},uAsteroids:{value:new Float32Array(ASTEROIDS*4)},time:{value:0}};
    var ring=buildRing();var geo=new THREE.BufferGeometry();
    geo.setAttribute('position',new THREE.BufferAttribute(ring.pos,3));
    geo.setAttribute('color',new THREE.BufferAttribute(ring.col,3));
    geo.setAttribute('aRandom',new THREE.BufferAttribute(ring.rnd,1));
    var pmat=new THREE.PointsMaterial({size:0.008,vertexColors:true,transparent:true,opacity:0.8,sizeAttenuation:true,blending:THREE.AdditiveBlending,depthWrite:false});
    pmat.onBeforeCompile=function(shader){
      shader.uniforms.uProgress=uniforms.uProgress;shader.uniforms.uAsteroids=uniforms.uAsteroids;shader.uniforms.time=uniforms.time;
      shader.vertexShader='uniform float uProgress;\nuniform vec4 uAsteroids['+ASTEROIDS+'];\nuniform float time;\nattribute float aRandom;\nvarying float vProgress;\n'+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>',[
        'vec3 transformed = vec3(position);',
        'float angle = atan(transformed.x, transformed.z);',
        'float normalizedAngle = abs(angle) / 3.14159265359;',
        'float spawnThreshold = 1.0 - normalizedAngle;',
        'float progressValue = (uProgress * 1.4) - spawnThreshold;',
        'float particleProgress = smoothstep(0.0, 0.4, progressValue);',
        'vProgress = particleProgress;',
        'transformed.y += sin(angle * 10.0 + time) * 0.05 * aRandom;',
        'if (uProgress > 0.5) {',
        '  for(int i = 0; i < '+ASTEROIDS+'; i++) {',
        '    vec4 astData = uAsteroids[i];',
        '    vec3 delta = transformed - astData.xyz;',
        '    float dist = length(delta);',
        '    float rad = astData.w * 2.0 + 0.15;',
        '    if (dist < rad) {',
        '      float force = pow((rad - dist) / rad, 2.0);',
        '      transformed += normalize(delta) * force * 0.4;',
        '      transformed.y += force * 0.20 * (aRandom - 0.5);',
        '    }',
        '  }',
        '}',
        'float swirl = (1.0 - particleProgress) * 4.0;',
        'float s = sin(swirl); float c = cos(swirl);',
        'transformed.xz = mat2(c, -s, s, c) * transformed.xz;',
        'transformed.y += (1.0 - particleProgress) * (transformed.y >= 0.0 ? 1.0 : -1.0);',
        'vec3 moonSurface = normalize(transformed) * 2.1;',
        'transformed = mix(moonSurface, transformed, particleProgress);'
      ].join('\n'));
      shader.fragmentShader='varying float vProgress;\n'+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\ndiffuseColor.a *= vProgress;');
    };
    var points=new THREE.Points(geo,pmat);points.rotation.x=-Math.PI/2;group.add(points);

    /* asteroid belt */
    var asteroids=generateAsteroids(ASTEROIDS);var massive=new Float32Array(ASTEROIDS*4);
    var belt=new THREE.InstancedMesh(new THREE.DodecahedronGeometry(1,0),new THREE.MeshStandardMaterial({map:tex,bumpMap:tex,bumpScale:0.08,color:0xffffff,roughness:0.7,metalness:0.1}),ASTEROIDS);
    belt.visible=false;group.add(belt);
    var dummy=new THREE.Object3D(),beltScale=0;

    function release(){if(ringState==='hidden'){ringState='animating';host.classList.add('is-live');}}

    /* pointer: drag spins the whole group (OrbitControls stand-in), a clean click releases the ring */
    var drag=null,ray=new THREE.Raycaster(),ndc=new THREE.Vector2();
    function pick(e){var r=canvas.getBoundingClientRect();ndc.set(((e.clientX-r.left)/r.width)*2-1,-((e.clientY-r.top)/r.height)*2+1);ray.setFromCamera(ndc,camera);return ray.intersectObject(moon,false).length>0;}
    canvas.addEventListener('pointerdown',function(e){drag={x:e.clientX,y:e.clientY,moved:0};canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',function(e){
      if(drag){var dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;drag.moved+=Math.abs(dx)+Math.abs(dy);group.rotation.y+=dx*0.006;group.rotation.x+=dy*0.006;}
      canvas.style.cursor=pick(e)?'pointer':'grab';
    });
    function up(e){if(drag&&drag.moved<6&&pick(e))release();drag=null;}
    canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',function(){drag=null;});

    /* hand control: the shared contract every 3D object on the site speaks */
    canvas.__ivLegacyHandControls={
      physics:function(delta){group.rotation.x+=delta[0];group.rotation.y+=delta[1];group.rotation.z+=delta[2];},
      rotate:function(screenDx){group.rotation.y+=screenDx*3.8;},
      zoom:function(handScale){var d=camDist/Math.max(.65,Math.min(1.4,handScale));camera.position.copy(camDir).multiplyScalar(d);camera.lookAt(0,0,0);}
    };
    var held=false;
    new MutationObserver(function(){var now=canvas.classList.contains('iv-rotating');if(now&&!held)release();held=now;}).observe(canvas,{attributes:true,attributeFilter:['class']});

    function size(){var r=host.getBoundingClientRect(),w=Math.max(1,Math.round(r.width)),h=Math.max(1,Math.round(r.height));renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
    addEventListener('resize',size,{passive:true});size();

    var last=performance.now(),inv=new THREE.Matrix4(),v=new THREE.Vector3(),localAst=new Float32Array(ASTEROIDS*4);
    function frame(now){
      if(!host.isConnected){removeEventListener('resize',size);renderer.dispose();geo.dispose();return;}
      requestAnimationFrame(frame);
      if(document.hidden)return;
      var delta=Math.min(.1,(now-last)/1000);last=now;
      var rect=host.getBoundingClientRect();if(rect.bottom<0||rect.top>innerHeight)return;
      moon.rotation.y+=delta*0.05;
      points.rotation.y-=delta*0.02;points.updateMatrix();
      uniforms.time.value=now/1000;
      if(ringState==='animating'){uniforms.uProgress.value=Math.min(1,uniforms.uProgress.value+delta*0.35);if(uniforms.uProgress.value>=1)ringState='visible';}
      else uniforms.uProgress.value=ringState==='visible'?1:0;

      var target=ringState==='hidden'?0:1;beltScale=THREE.MathUtils.lerp(beltScale,target,delta*(ringState==='hidden'?5:2));
      if(beltScale<0.01){belt.visible=false;}else{
        belt.visible=true;
        for(var i=0;i<ASTEROIDS;i++){var a=asteroids[i];
          a.angle+=a.speed*delta;a.phase+=a.radialSpeed*delta;
          var cr=a.baseRadius+Math.sin(a.phase)*a.radialAmplitude;if(cr<2.15)cr=2.15+(2.15-cr)*0.85;
          var x=Math.cos(a.angle)*cr,y=Math.sin(a.angle)*cr;
          massive[i*4]=x;massive[i*4+1]=y;massive[i*4+2]=a.zOffset;massive[i*4+3]=a.scale;
          a.rx+=a.rsx;a.ry+=a.rsy;a.rz+=a.rsz;
          dummy.position.set(x,y,a.zOffset);dummy.rotation.set(a.rx,a.ry,a.rz);dummy.scale.setScalar(a.scale*beltScale);dummy.updateMatrix();
          belt.setMatrixAt(i,dummy.matrix);
        }
        belt.instanceMatrix.needsUpdate=true;
        inv.copy(points.matrix).invert();
        for(var j=0;j<ASTEROIDS;j++){v.set(massive[j*4],massive[j*4+1],massive[j*4+2]).applyMatrix4(inv);localAst[j*4]=v.x;localAst[j*4+1]=v.y;localAst[j*4+2]=v.z;localAst[j*4+3]=massive[j*4+3];}
        uniforms.uAsteroids.value=localAst;
      }
      renderer.render(scene,camera);
    }
    requestAnimationFrame(frame);
  };
})();
