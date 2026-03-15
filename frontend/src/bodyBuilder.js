/**
 * BRIDGE AI OS Digital Twin — Full Body Builder
 * Torso, neck, arms, legs, hands (fingers), feet (toes), hair.
 */
export function buildBody(scene, face, skinMat, perfMode = false) {
  const segs = perfMode ? 16 : 24;

  // ==========================
  // TORSO (chest + abdomen) — connects below neck base
  // ==========================
  const torsoRoot = new BABYLON.TransformNode("torsoRoot", scene);
  torsoRoot.position.set(0, -0.64, 0.08);
  torsoRoot.parent = face;

  const chest = BABYLON.MeshBuilder.CreateCylinder("chest", {
    height: 0.28,
    diameterTop: 0.38,
    diameterBottom: 0.42,
    tessellation: segs
  }, scene);
  chest.rotation.x = Math.PI / 2;
  chest.position.set(0, 0, 0);
  chest.material = skinMat;
  chest.parent = torsoRoot;

  const abdomen = BABYLON.MeshBuilder.CreateCylinder("abdomen", {
    height: 0.22,
    diameterTop: 0.4,
    diameterBottom: 0.36,
    tessellation: segs
  }, scene);
  abdomen.rotation.x = Math.PI / 2;
  abdomen.position.set(0, -0.25, 0);
  abdomen.material = skinMat;
  abdomen.parent = torsoRoot;

  // ==========================
  // SHOULDERS
  // ==========================
  const shoulderL = BABYLON.MeshBuilder.CreateSphere("shoulderL", { diameter: 0.16, segments: segs }, scene);
  shoulderL.position.set(-0.28, 0.08, 0.02);
  shoulderL.material = skinMat;
  shoulderL.parent = torsoRoot;

  const shoulderR = shoulderL.clone("shoulderR");
  shoulderR.position.x = 0.28;
  shoulderR.parent = torsoRoot;

  // ==========================
  // ARMS (upper arm → forearm → hand)
  // ==========================
  function createArm(side) {
    const armRoot = new BABYLON.TransformNode(`armRoot${side}`, scene);
    armRoot.position.set(side === 'L' ? -0.32 : 0.32, 0.06, -0.02);
    armRoot.rotation.z = side === 'L' ? 0.15 : -0.15;
    armRoot.parent = torsoRoot;

    const upperArm = BABYLON.MeshBuilder.CreateCylinder("upperArm", {
      height: 0.32,
      diameterTop: 0.1,
      diameterBottom: 0.08,
      tessellation: 12
    }, scene);
    upperArm.rotation.x = Math.PI / 2;
    upperArm.position.set(0, 0, -0.16);
    upperArm.material = skinMat;
    upperArm.parent = armRoot;

    const elbow = new BABYLON.TransformNode("elbow", scene);
    elbow.position.set(0, 0, -0.32);
    elbow.rotation.x = 0.2;
    elbow.parent = armRoot;

    const forearm = BABYLON.MeshBuilder.CreateCylinder("forearm", {
      height: 0.26,
      diameterTop: 0.08,
      diameterBottom: 0.06,
      tessellation: 12
    }, scene);
    forearm.rotation.x = Math.PI / 2;
    forearm.position.set(0, 0, -0.13);
    forearm.material = skinMat;
    forearm.parent = elbow;

    const wrist = new BABYLON.TransformNode("wrist", scene);
    wrist.position.set(0, 0, -0.26);
    wrist.parent = elbow;

    // Hand (palm + fingers)
    const palm = BABYLON.MeshBuilder.CreateBox("palm", { width: 0.08, height: 0.1, depth: 0.03 }, scene);
    palm.position.set(0, 0, -0.04);
    palm.rotation.x = -0.1;
    palm.material = skinMat;
    palm.parent = wrist;

    const fingerLen = [0.04, 0.05, 0.045, 0.035, 0.025];
    const fingerNames = ["thumb", "index", "middle", "ring", "pinky"];
    for (let i = 0; i < 5; i++) {
      const finger = BABYLON.MeshBuilder.CreateCylinder(`finger${fingerNames[i]}`, {
        height: fingerLen[i],
        diameterTop: 0.012,
        diameterBottom: 0.014,
        tessellation: 8
      }, scene);
      finger.rotation.x = Math.PI / 2;
      const xOff = (i - 2) * 0.022 * (side === 'L' ? 1 : -1);
      finger.position.set(xOff, 0, -0.02 - fingerLen[i] / 2);
      finger.material = skinMat;
      finger.parent = wrist;
    }

    return armRoot;
  }
  createArm('L');
  createArm('R');

  // ==========================
  // HIPS + LEGS
  // ==========================
  const hipRoot = new BABYLON.TransformNode("hipRoot", scene);
  hipRoot.position.set(0, -0.55, 0.02);
  hipRoot.parent = torsoRoot;

  const hipL = BABYLON.MeshBuilder.CreateSphere("hipL", { diameter: 0.14, segments: 16 }, scene);
  hipL.position.set(-0.12, 0, 0);
  hipL.material = skinMat;
  hipL.parent = hipRoot;

  const hipR = hipL.clone("hipR");
  hipR.position.x = 0.12;
  hipR.parent = hipRoot;

  function createLeg(side) {
    const legRoot = new BABYLON.TransformNode(`legRoot${side}`, scene);
    legRoot.position.set(side === 'L' ? -0.1 : 0.1, -0.08, 0);
    legRoot.parent = hipRoot;

    const thigh = BABYLON.MeshBuilder.CreateCylinder("thigh", {
      height: 0.4,
      diameterTop: 0.14,
      diameterBottom: 0.1,
      tessellation: 12
    }, scene);
    thigh.rotation.x = Math.PI / 2;
    thigh.position.set(0, 0, -0.2);
    thigh.material = skinMat;
    thigh.parent = legRoot;

    const knee = new BABYLON.TransformNode("knee", scene);
    knee.position.set(0, 0, -0.4);
    knee.rotation.x = 0.08;
    knee.parent = legRoot;

    const shin = BABYLON.MeshBuilder.CreateCylinder("shin", {
      height: 0.36,
      diameterTop: 0.1,
      diameterBottom: 0.08,
      tessellation: 12
    }, scene);
    shin.rotation.x = Math.PI / 2;
    shin.position.set(0, 0, -0.18);
    shin.material = skinMat;
    shin.parent = knee;

    const ankle = new BABYLON.TransformNode("ankle", scene);
    ankle.position.set(0, 0, -0.36);
    ankle.parent = knee;

    // Foot + toes
    const foot = BABYLON.MeshBuilder.CreateBox("foot", { width: 0.12, height: 0.06, depth: 0.2 }, scene);
    foot.position.set(0, 0, -0.08);
    foot.rotation.x = 0.15;
    foot.material = skinMat;
    foot.parent = ankle;

    const toeLen = [0.03, 0.035, 0.032, 0.028, 0.02];
    for (let i = 0; i < 5; i++) {
      const toe = BABYLON.MeshBuilder.CreateSphere(`toe${i}`, { diameter: 0.025, segments: 8 }, scene);
      toe.scaling.set(1, 0.6, 1.2);
      const xOff = (i - 2) * 0.022 * (side === 'L' ? 1 : -1);
      toe.position.set(xOff, 0, -0.12 - toeLen[i] * 0.5);
      toe.material = skinMat;
      toe.parent = ankle;
    }

    return legRoot;
  }
  createLeg('L');
  createLeg('R');

  // ==========================
  // HAIR (scalp + strands)
  // ==========================
  const hairMat = new BABYLON.PBRMaterial("hair", scene);
  hairMat.albedoColor = new BABYLON.Color3(0.12, 0.08, 0.06);
  hairMat.roughness = 0.9;
  hairMat.metallic = 0;

  // Scalp hair (crown + top)
  const scalp = BABYLON.MeshBuilder.CreateSphere("scalp", {
    diameterX: 0.84,
    diameterY: 0.5,
    diameterZ: 0.82,
    arc: 1,
    slice: 0.6,
    segments: perfMode ? 24 : 32
  }, scene);
  scalp.position.set(0, 0.42, 0.02);
  scalp.rotation.x = -0.12;
  scalp.material = hairMat;
  scalp.parent = face;

  // Hair volume (back and sides — nape)
  const hairBack = BABYLON.MeshBuilder.CreateSphere("hairBack", {
    diameterX: 0.76,
    diameterY: 0.45,
    diameterZ: 0.7,
    arc: 1,
    slice: 0.45,
    segments: 20
  }, scene);
  hairBack.position.set(0, 0.12, -0.22);
  hairBack.rotation.x = -0.25;
  hairBack.material = hairMat;
  hairBack.parent = face;

  return { torsoRoot, scalp, hairBack };
}
