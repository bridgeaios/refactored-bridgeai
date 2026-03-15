import { Engine, Scene, ArcRotateCamera, HemisphericLight, DirectionalLight, MeshBuilder, PBRMaterial, Vector3, SceneLoader } from '@babylonjs/core';
import '@babylonjs/loaders';

const MODEL_URLS = ['/model.glb', '/models/HumanFace.glb', '/models/RobotExpressive.glb'];

export class Renderer {
  constructor(container){
    this.container = container;
    this.engine = new Engine(document.createElement('canvas'), true, {preserveDrawingBuffer:true, stencil:true});
    this.canvas = this.engine.getRenderingCanvas();
    this.canvas.style.width = '100%';
    this.canvas.style.height = '100%';
    container.appendChild(this.canvas);
    this.scene = new Scene(this.engine);
    this.scene.autoClear = true;
    this.camera = new ArcRotateCamera('cam', Math.PI/2, Math.PI/2.8, 2.5, new Vector3(0,1.2,0), this.scene);
    this.camera.minZ = 0.05;
    this.camera.maxZ = 100;
    this.camera.attachControl(this.canvas, true);
    // Multi-light setup for proper GLTF PBR visibility
    const hemi = new HemisphericLight('hemi', new Vector3(0,1,0), this.scene);
    hemi.intensity = 1.2;
    hemi.groundColor = new Vector3(0.3, 0.28, 0.32);
    const dir1 = new DirectionalLight('dir1', new Vector3(-0.5,-1,0.5), this.scene);
    dir1.position = new Vector3(5,10,5);
    dir1.intensity = 1.4;
    const dir2 = new DirectionalLight('dir2', new Vector3(0.5,-0.5,-0.5), this.scene);
    dir2.position = new Vector3(-4,6,4);
    dir2.intensity = 0.8;
    this.face = null;
    this.morphTargets = {};
    this._loadModel();
    this._startRenderLoop();
  }

  _collectMorphTargets(mesh){
    const visit = (m) => {
      if(m.morphTargetManager){
        const mgr = m.morphTargetManager;
        for(let i=0;i<mgr.numTargets;i++){
          const t = mgr.getTarget(i);
          this.morphTargets[t.name] = {mesh:m, index:i};
        }
      }
      m.getChildMeshes().forEach(visit);
    };
    visit(mesh);
  }

  _fitCameraToModel(rootMeshes){
    const meshList = rootMeshes.filter(m => m.getHierarchyBoundingVectors);
    if(meshList.length === 0) return;
    const min = new Vector3(Infinity, Infinity, Infinity);
    const max = new Vector3(-Infinity, -Infinity, -Infinity);
    meshList.forEach(m => {
      m.computeWorldMatrix?.(true);
      const b = m.getHierarchyBoundingVectors(true);
      if(b?.min && b?.max){
        min.set(Math.min(min.x, b.min.x), Math.min(min.y, b.min.y), Math.min(min.z, b.min.z));
        max.set(Math.max(max.x, b.max.x), Math.max(max.y, b.max.y), Math.max(max.z, b.max.z));
      }
    });
    if(min.x === Infinity) return;
    const center = Vector3.Center(min, max);
    const size = max.subtract(min);
    const maxDim = Math.max(size.x, size.y, size.z);
    const radius = Math.max(maxDim * 1.1 + 0.5, 1.2);
    this.camera.setTarget(center);
    this.camera.radius = Math.max(1.2, Math.min(5, radius));
    this.camera.lowerRadiusLimit = Math.min(1.2, radius * 0.5);
    this.camera.upperRadiusLimit = Math.max(5, radius * 2);
  }

  async _loadModel(){
    let loaded = false;
    for(const url of MODEL_URLS){
      try{
        await SceneLoader.AppendAsync('', url, this.scene);
        loaded = true;
        break;
      }catch(_){}
    }
    if(!loaded){
      console.warn('No GLTF model found, falling back to sphere');
      const s = MeshBuilder.CreateSphere('fallback_face',{diameter:1.8}, this.scene);
      s.position.y = 1.2;
      const mat = new PBRMaterial('m', this.scene);
      mat.albedoColor = new Vector3(0.9,0.85,0.8);
      s.material = mat;
      this.face = s;
      return;
    }
    // Find primary face mesh: Head, face, or first mesh with morph targets
    const meshes = this.scene.meshes.filter(m => !m.name?.startsWith('BABYLON'));
    const byName = (name) => meshes.find(m => m.name && m.name.toLowerCase().includes(name));
    this.face = byName('head') || byName('face') || meshes.find(m => m.morphTargetManager?.numTargets > 0) || meshes[0];
    if(!this.face) this.face = meshes[0];

    // Ensure all meshes are visible and rendered
    meshes.forEach(m => {
      m.setEnabled(true);
      m.isVisible = true;
      if(m.material && 'backFaceCulling' in m.material) m.material.backFaceCulling = false;
    });

    this._collectMorphTargets(this.face);
    this._fitCameraToModel(meshes);
  }

  applyBlendshapes(map){
    for(const [k,v] of Object.entries(map)){
      const entry = this.morphTargets[k];
      if(!entry) continue;
      const {mesh,index} = entry;
      const mgr = mesh.morphTargetManager;
      const cur = mgr.getTarget(index).influence;
      mgr.getTarget(index).influence = cur * 0.8 + v * 0.2;
    }
  }

  _startRenderLoop(){
    let t=0;
    this.engine.runRenderLoop(()=>{
      t += this.engine.getDeltaTime()/1000;
      // breathing: small scale on Y
      if(this.face && this.face.scaling) {
        const base = this._baseScaleY ?? (this._baseScaleY = this.face.scaling.y);
        this.face.scaling.y = base * (1 + Math.sin(t*1.2)*0.005);
      }
      if(this.scene.activeCamera) this.scene.render();
    });
    window.addEventListener('resize', ()=> this.engine.resize());
  }
}
