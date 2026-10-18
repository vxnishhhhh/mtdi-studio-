/* I³ robotic hand. Presentation rig only; never writes calibration or sensor state. */
(function(){
'use strict';
function create(canvas){
 const T=window.THREE, scene=new T.Scene(), camera=new T.PerspectiveCamera(35,1,.1,50);
 const renderer=new T.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'high-performance'});
 renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.outputColorSpace=T.SRGBColorSpace;
 renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
 camera.position.set(0,.65,9);camera.lookAt(0,.65,0);
 scene.add(new T.HemisphereLight(0xd5efff,0x101521,1.5));
 for(const [color,intensity,pos] of [[0xffffff,3,[-3,5,6]],[0x52ddeb,2,[4,2,-3]],[0x6d83aa,1,[-4,-1,2]]]){const l=new T.DirectionalLight(color,intensity);l.position.set(...pos);scene.add(l);}
 const materials={shell:new T.MeshStandardMaterial({color:0xaab8c9,metalness:.72,roughness:.3}),dark:new T.MeshStandardMaterial({color:0x182332,metalness:.7,roughness:.35}),joint:new T.MeshStandardMaterial({color:0x53677b,metalness:.85,roughness:.25}),cyan:new T.MeshStandardMaterial({color:0x57e1e9,emissive:0x20b6c9,emissiveIntensity:.55,metalness:.5,roughness:.3})};
 const root=new T.Group(),hand=new T.Group();scene.add(root);root.add(hand);root.rotation.set(-.1,-.35,0);
 function mesh(geometry,material,parent,x=0,y=0,z=0){const m=new T.Mesh(geometry,materials[material]);m.position.set(x,y,z);parent.add(m);return m;}
 function plate(w,h,d,parent,x,y,z,material='shell'){
  const r=Math.min(w,h)*.15,s=new T.Shape();s.moveTo(-w/2+r,-h/2);s.lineTo(w/2-r,-h/2);s.quadraticCurveTo(w/2,-h/2,w/2,-h/2+r);s.lineTo(w/2,h/2-r);s.quadraticCurveTo(w/2,h/2,w/2-r,h/2);s.lineTo(-w/2+r,h/2);s.quadraticCurveTo(-w/2,h/2,-w/2,h/2-r);s.lineTo(-w/2,-h/2+r);s.quadraticCurveTo(-w/2,-h/2,-w/2+r,-h/2);
  const g=new T.ExtrudeGeometry(s,{depth:d,bevelEnabled:true,bevelSegments:2,steps:1,bevelSize:.035,bevelThickness:.035,curveSegments:5});g.translate(0,0,-d/2);return mesh(g,material,parent,x,y,z);
 }
 plate(1.62,1.55,.42,hand,0,0,0,'dark');plate(1.4,1.3,.13,hand,0,.04,.27);plate(1.32,1.22,.09,hand,0,.02,-.26,'joint');
 // Dorsal service plate, tactile palm pads, fasteners and a short wrist connector.
 plate(.63,.73,.035,hand,0,.1,.365,'dark');plate(.045,.48,.02,hand,0,.1,.397,'cyan');
 for(const x of [-.51,.51])for(const y of [-.45,.47]){const bolt=mesh(new T.CylinderGeometry(.06,.06,.045,12),'joint',hand,x,y,.36);bolt.rotation.x=Math.PI/2;}
 for(const x of [-.4,0,.4])plate(.22,.62,.04,hand,x,-.03,-.34,'dark');
 const cuff=mesh(new T.CylinderGeometry(.52,.52,.32,32),'joint',hand,0,-.92,0);mesh(new T.CylinderGeometry(.39,.39,.34,32),'dark',hand,0,-.94,0);
 function joint(parent,r){const axle=mesh(new T.CylinderGeometry(r,r,.34,20),'joint',parent);axle.rotation.z=Math.PI/2;for(const x of [-.18,.18]){const ring=mesh(new T.TorusGeometry(r*.74,.018,6,24),'cyan',parent,x,0,0);ring.rotation.y=Math.PI/2;}}
 function segment(parent,len,width,x,y,z){const g=new T.Group();g.position.set(x,y,z);parent.add(g);joint(g,width*.53);plate(width,len-.1,width*.76,g,0,len/2,0);plate(width*.66,len*.47,.035,g,0,len*.55,.17,'dark');const end=new T.Group();end.position.y=len;g.add(end);return {g,end};}
 const lengths=[[.62,.46,.34],[.72,.5,.36],[.66,.47,.34],[.52,.38,.29]], fingers=[];
 for(let i=0;i<4;i++){let parent=hand,chain=[];for(let j=0;j<3;j++){const seg=segment(parent,lengths[i][j],i===3?.26:.3,j?0:(i-1.5)*.4,j?0:.79,j?0:0);chain.push(seg.g);parent=seg.end;}fingers.push(chain);}
 const thumb=[],saddle=new T.Group();saddle.position.set(-.79,-.4,0);hand.add(saddle);joint(saddle,.2);let parent=saddle;
 for(const len of [.58,.45]){const seg=segment(parent,len,.34,0,0,0);thumb.push(seg.g);parent=seg.end;}
 const rig={renderer,scene,camera,root,hand,fingers,thumb,saddle,pose:'open',manual:null,playing:true,yaw:-.35,pitch:-.1,zoom:9,disposed:false};
 rig.resize=()=>{rig.lastPose=null;const w=canvas.clientWidth||300,h=canvas.clientHeight||300;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};rig.resize();
 rig.dispose=()=>{if(rig.disposed)return;rig.disposed=true;scene.traverse(o=>o.geometry?.dispose());Object.values(materials).forEach(m=>m.dispose());renderer.dispose();};
 return rig;
}
function pose(rig,P){
 const signature=JSON.stringify([P,rig.manual,rig.pitch,rig.yaw,rig.zoom]);if(signature===rig.lastPose)return;rig.lastPose=signature;
 rig.fingers.forEach((chain,i)=>{const c=rig.manual?.[i]??P.curl[i];chain[0].rotation.set(-c*1.15,0,-(i-1.5)*.1*P.spread);chain[1].rotation.x=-c*1.35;chain[2].rotation.x=-c*.95;});
 rig.saddle.rotation.set(0,-.3, .95*(1-Math.max(0,-P.thumb)));
 rig.thumb[0].rotation.set(-Math.max(0,P.thumb)*.8,-Math.max(0,P.thumb)*.6,0);rig.thumb[1].rotation.x=-Math.max(0,P.thumb)*1.1;
 if(P.pinch){const q=P.pinch;rig.saddle.rotation.set(.35*q,-.75*q,.95-.8*q);rig.thumb[0].rotation.set(-.8*q,0,0);rig.thumb[1].rotation.x=-.6*q;rig.fingers[0][0].rotation.set(-.65*q,-.18*q,.12*q);rig.fingers[0][1].rotation.x=-1.1*q;rig.fingers[0][2].rotation.x=-.65*q;}
 rig.hand.position.set(P.dx*.4,-P.dy*.65,0);rig.root.rotation.set(rig.pitch,rig.yaw,0);rig.camera.position.z=rig.zoom;rig.renderer.render(rig.scene,rig.camera);
}
window.I3RobotHand={create,pose};
})();
