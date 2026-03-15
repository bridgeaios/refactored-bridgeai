/**
 * Bridge AI OS Digital Twin — MetaHuman / Neuromuscular Face + Full Body
 * Twins share one XML. Backend is human. I am the Bridge. I am the Authority.
 * Face state bound to backend health: ALIVE | DEGRADED | OFFLINE
 * Twins mirror the latest AI human rendering (same skin/eye pipeline as main) to keep up to speed.
 */
import { createHighFidelitySkinMaterial, setupCinematicLighting } from './skinSystem.js';
import { buildBody } from './bodyBuilder.js';
import { createDetailedEyeMaterials } from './eyeBuilder.js';

const METAHUMAN_MODEL_URLS = ['/models/MetaHuman.glb', '/model.glb', '/models/HumanFace.glb'];

/**
 * Build one human twin avatar — head with detailed eyes, full body.
 * Twins mirror the latest AI human rendering (same pipeline as main avatar) to keep up to speed.
 */
function buildHumanTwinAvatar(scene, parent, skinMat, eyeMats, opts = {}) {
    const name = opts.name || 'twin';
    const pos = opts.position || new BABYLON.Vector3(0, 0, 0);
    const scale = opts.scale || 1;

    const face = new BABYLON.TransformNode(`${name}Face`, scene);
    face.position = pos;
    face.scaling = new BABYLON.Vector3(scale, scale, scale);
    if (parent) face.parent = parent;

    // Human head — slightly oval (more natural than sphere)
    const head = BABYLON.MeshBuilder.CreateSphere(`${name}Head`, { diameterX: 0.88, diameterY: 0.92, diameterZ: 0.85, segments: 28 }, scene);
    head.material = skinMat;
    head.parent = face;

    // Detailed human eyes (sclera, iris, pupil) — not simple spheres
    const eyeSize = 0.11;
    const leftEye = BABYLON.MeshBuilder.CreateSphere(`${name}EyeL`, { diameter: eyeSize, segments: 16 }, scene);
    leftEye.position.set(-0.17, 0.07, 0.4);
    leftEye.material = eyeMats?.corneaMat || eyeMats?.scleraMat || skinMat;
    leftEye.parent = face;
    const rightEye = leftEye.clone(`${name}EyeR`);
    rightEye.position.x = 0.17;
    rightEye.parent = face;

    // Human lips
    const mouthMat = new BABYLON.PBRMaterial(`${name}Mouth`, scene);
    mouthMat.albedoColor = new BABYLON.Color3(0.82, 0.35, 0.32);
    mouthMat.roughness = 0.3;
    mouthMat.subSurface.isTranslucencyEnabled = true;
    mouthMat.subSurface.translucencyIntensity = 0.25;
    const mouth = BABYLON.MeshBuilder.CreateSphere(`${name}Mouth`, { diameter: 0.14, segments: 14 }, scene);
    mouth.scaling.set(1, 0.45, 0.65);
    mouth.position.set(0, -0.18, 0.43);
    mouth.rotation.x = 0.18;
    mouth.material = mouthMat;
    mouth.parent = face;

    buildBody(scene, face, skinMat, true);
    return face;
}

/** Build procedural MetaHuman when no GLB — all twins look like humans: detailed eyes, high-fidelity skin, full body. */
function buildSimpleMetaHuman(scene, camera, faceState) {
    const face = new BABYLON.TransformNode("metaHuman", scene);
    face.scaling = new BABYLON.Vector3(1.2, 1.2, 1.2);

    // Always use high-fidelity human skin
    const skinMat = createHighFidelitySkinMaterial(scene, { albedoSize: 1024 });
    const irisColor = (typeof window !== 'undefined' && window.__BRIDGE_IRIS_COLOR) || 'blue';
    const eyeMats = createDetailedEyeMaterials(scene, irisColor);

    // Human head — oval proportions
    const head = BABYLON.MeshBuilder.CreateSphere("head", { diameterX: 0.88, diameterY: 0.92, diameterZ: 0.85, segments: 28 }, scene);
    head.material = skinMat;
    head.parent = face;

    // Detailed human eyes (sclera, iris, limbus, cornea)
    const leftEye = BABYLON.MeshBuilder.CreateSphere("eyeL", { diameter: 0.11, segments: 16 }, scene);
    leftEye.position.set(-0.18, 0.08, 0.38);
    leftEye.material = eyeMats.corneaMat;
    leftEye.parent = face;
    const rightEye = leftEye.clone("eyeR");
    rightEye.position.x = 0.18;
    rightEye.parent = face;

    const mouthMat = new BABYLON.PBRMaterial("metaMouth", scene);
    mouthMat.albedoColor = new BABYLON.Color3(0.82, 0.35, 0.32);
    mouthMat.roughness = 0.28;
    mouthMat.subSurface.isTranslucencyEnabled = true;
    mouthMat.subSurface.translucencyIntensity = 0.28;
    mouthMat.subSurface.tintColor = new BABYLON.Color3(0.9, 0.4, 0.38);
    const mouth = BABYLON.MeshBuilder.CreateSphere("mouth", { diameter: 0.15, segments: 14 }, scene);
    mouth.scaling.set(1, 0.4, 0.6);
    mouth.position.set(0, -0.2, 0.42);
    mouth.rotation.x = 0.2;
    mouth.material = mouthMat;
    mouth.parent = face;

    // Full human body
    buildBody(scene, face, skinMat, true);

    if (faceState === 'OFFLINE') {
        const wireMat = new BABYLON.StandardMaterial("wire", scene);
        wireMat.wireframe = true;
        wireMat.diffuseColor = new BABYLON.Color3(0.9, 0.1, 0.1);
        const allMeshes = face.getChildMeshes ? face.getChildMeshes(true) : [head, leftEye, rightEye, mouth];
        allMeshes.forEach(m => { if (m instanceof BABYLON.Mesh && m.material) m.material = wireMat; });
    } else if (faceState === 'DEGRADED') {
        skinMat.albedoColor = skinMat.albedoColor.multiply(new BABYLON.Color3(1, 0.75, 0.4));
    }

    scene._faceState = { smile: undefined, blink: undefined, jawOpen: undefined, eyeYaw: undefined, frown: undefined };
    scene._physiology = { baselineTone: 0.02, arousal: 1 };
    scene._backendFaceState = faceState;

    let blinkVal = 0, smileVal = 0.2, jawVal = 0.08;
    scene.registerBeforeRender(() => {
        const s = scene._faceState;
        blinkVal += (s.blink !== undefined ? s.blink : 0) - blinkVal * 0.15;
        smileVal += (s.smile !== undefined ? s.smile : 0.2) - smileVal * 0.1;
        jawVal += (s.jawOpen !== undefined ? s.jawOpen : 0.08) - jawVal * 0.1;
        leftEye.scaling.y = rightEye.scaling.y = 1 - blinkVal * 0.8;
        mouth.scaling.y = 0.4 + smileVal * 0.2;
        mouth.position.y = -0.2 - jawVal * 0.15;
    });

    window.setExpression = (opts = {}) => {
        if (!scene._faceState) return;
        if (opts.smile !== undefined) scene._faceState.smile = opts.smile;
        if (opts.blink !== undefined) scene._faceState.blink = opts.blink;
        if (opts.jawOpen !== undefined) scene._faceState.jawOpen = opts.jawOpen;
        if (opts.eyeYaw !== undefined) scene._faceState.eyeYaw = opts.eyeYaw;
        if (opts.frown !== undefined) scene._faceState.frown = opts.frown;
    };
    window.addEventListener('face:setExpression', (e) => { const o = e.detail || {}; if (window.setExpression) window.setExpression(o); });

    scene.onBeforeRenderObservable.addOnce(() => {
        try {
            const showAll = typeof window !== 'undefined' && window.__BRIDGE_SHOW_ALL_TWINS !== false;
            camera.setTarget(new BABYLON.Vector3(0, 0, 0.02));
            camera.radius = showAll ? 4.5 : 3.8;
            if (showAll) camera.upperRadiusLimit = 8;
        } catch (_) {}
    });

    // Add Alpha, Gamma twin avatars — twins mirror the latest human rendering (same fidelity as main)
    const showAllTwins = typeof window !== 'undefined' && window.__BRIDGE_SHOW_ALL_TWINS !== false;
    if (showAllTwins) {
        const irisColors = ['blue', 'brown'];
        const albedoSize = (typeof window !== 'undefined' && window.__BRIDGE_HIGH_FIDELITY_SKIN) ? 2048 : 1024;
        const positions = [new BABYLON.Vector3(-1.5, 0, 0), new BABYLON.Vector3(1.5, 0, 0)];
        const names = ['Alpha', 'Gamma'];
        for (let i = 0; i < 2; i++) {
            // Same high-fidelity skin pipeline as main avatar — twins keep up with latest AI human rendering
            const twinSkin = createHighFidelitySkinMaterial(scene, { albedoSize });
            const twinEyeMats = createDetailedEyeMaterials(scene, irisColors[i]);
            buildHumanTwinAvatar(scene, null, twinSkin, twinEyeMats, {
                name: names[i],
                position: positions[i],
                scale: 0.92,
            });
        }
    }
    return scene;
}

export async function initRenderer(engine, canvas, options = {}) {
    const faceState = options.faceState || 'OFFLINE';
    // Default: all twins look like humans (MetaHuman / procedural human)
    const useMetaHuman = options.useMetaHuman ?? (typeof window === 'undefined' || window.__BRIDGE_USE_METAHUMAN !== false);

    const scene = new BABYLON.Scene(engine);
    scene.useRightHandedSystem = true;
    scene.clearColor = new BABYLON.Color4(0.06, 0.08, 0.14, 1);

    // PBR environment for proper reflections and lighting
    try {
        scene.createDefaultEnvironment?.({ createGround: false });
    } catch (_) { /* fallback if unavailable */ }

    const camera = new BABYLON.ArcRotateCamera("camera", -Math.PI / 2, Math.PI / 2.4, 3.8, new BABYLON.Vector3(0, 0, 0.05), scene);
    camera.minZ = 0.05;
    camera.maxZ = 100;
    camera.lowerRadiusLimit = 2.0;
    camera.upperRadiusLimit = 7;
    camera.lowerBetaLimit = 0.3;
    camera.upperBetaLimit = Math.PI / 2 + 0.3;
    camera.wheelPrecision = 30;
    camera.panningSensibility = 50;
    camera.attachControl(canvas, true);

    const hemi = new BABYLON.HemisphericLight("hemi", new BABYLON.Vector3(0, 1, 0), scene);
    hemi.intensity = 1.1;
    hemi.groundColor = new BABYLON.Color3(0.4, 0.32, 0.35);
    const dir1 = new BABYLON.DirectionalLight("dir1", new BABYLON.Vector3(-1, -0.5, -0.8), scene);
    dir1.intensity = 1.4;
    dir1.position = new BABYLON.Vector3(3, 5, 3);
    const dir2 = new BABYLON.DirectionalLight("dir2", new BABYLON.Vector3(0.6, -0.3, -0.4), scene);
    dir2.intensity = 0.7;
    dir2.position = new BABYLON.Vector3(-2.5, 3, 2);
    const dir3 = new BABYLON.DirectionalLight("dir3", new BABYLON.Vector3(-0.3, -1, -0.5), scene);
    dir3.intensity = 0.5;
    dir3.position = new BABYLON.Vector3(1, 4, 2);
    const rim = new BABYLON.PointLight("rim", new BABYLON.Vector3(0, 0, -2), scene);
    rim.intensity = 0.4;
    rim.diffuse = new BABYLON.Color3(0.9, 0.85, 0.95);
    const rimDir = new BABYLON.DirectionalLight("rimDir", new BABYLON.Vector3(0.5, -0.2, -1), scene);
    rimDir.intensity = 0.35;
    rimDir.position = new BABYLON.Vector3(0, 2, 1);

    // Face render flow:
    // 1. useMetaHuman true, !lightweight → try GLB → if success, use GLB
    // 2. useMetaHuman true, GLB fail or lightweight → use procedural MetaHuman (head + eyes + mouth)
    // 3. useMetaHuman false → use full neuromuscular procedural face
    const lightweight = typeof window !== 'undefined' && window.__BRIDGE_LIGHTWEIGHT;
    if (useMetaHuman) {
        if (!lightweight) try {
            for (const url of METAHUMAN_MODEL_URLS) {
                const lastSlash = url.lastIndexOf('/');
                const rootUrl = lastSlash >= 0 ? url.slice(0, lastSlash + 1) : '';
                const sceneFile = lastSlash >= 0 ? url.slice(lastSlash + 1) : url;
                const result = await BABYLON.SceneLoader.ImportMeshAsync('', rootUrl || '/', sceneFile, scene);
                if (result && result.meshes && result.meshes.length > 0) {
                    const root = result.meshes[0];
                    root.parent = null;
                    root.position = new BABYLON.Vector3(0, 0, 0.05);
                    root.scaling = new BABYLON.Vector3(1.15, 1.15, 1.15);
                    scene.meshes.forEach(m => { m.setEnabled(true); m.isVisible = true; });
                    if (faceState === 'OFFLINE') {
                        const wireMat = new BABYLON.StandardMaterial("wireframe_offline", scene);
                        wireMat.wireframe = true;
                        wireMat.diffuseColor = new BABYLON.Color3(0.9, 0.1, 0.1);
                        scene.meshes.forEach(m => { if (m.material) m.material = wireMat; });
                    } else if (faceState === 'DEGRADED') {
                        scene.meshes.forEach(m => {
                            if (m.material && m.material.ambientColor) m.material.ambientColor = m.material.ambientColor.multiply(new BABYLON.Color3(1, 0.75, 0.4));
                        });
                    }
                    const morphTargets = {};
                    scene.meshes.forEach(m => {
                        if (m.morphTargetManager) for (let i = 0; i < m.morphTargetManager.numTargets; i++)
                            morphTargets[m.morphTargetManager.getTarget(i).name] = { mesh: m, index: i };
                    });
                    scene._faceState = { smile: undefined, blink: undefined, jawOpen: undefined, eyeYaw: undefined, frown: undefined };
                    scene._physiology = { baselineTone: 0.02, arousal: 1 };
                    scene._backendFaceState = faceState;
                    window.setExpression = (opts = {}) => {
                        if (!scene._faceState) return;
                        if (opts.smile !== undefined) scene._faceState.smile = opts.smile;
                        if (opts.blink !== undefined) scene._faceState.blink = opts.blink;
                        if (opts.jawOpen !== undefined) scene._faceState.jawOpen = opts.jawOpen;
                        if (opts.eyeYaw !== undefined) scene._faceState.eyeYaw = opts.eyeYaw;
                        if (opts.frown !== undefined) scene._faceState.frown = opts.frown;
                        const map = {};
                        if (opts.jawOpen !== undefined) { map.jawOpen = opts.jawOpen; map.Jaw_Open = opts.jawOpen; }
                        if (opts.smile !== undefined) { map.mouthSmile = opts.smile; map.Mouth_Smile = opts.smile; }
                        if (opts.blink !== undefined) { map.eyeBlinkLeft = opts.blink; map.eyeBlinkRight = opts.blink; }
                        Object.entries(map).forEach(([k, v]) => { const t = morphTargets[k]; if (t) t.mesh.morphTargetManager.getTarget(t.index).influence = v; });
                    };
                    window.addEventListener('face:setExpression', (e) => { const o = e.detail || {}; if (window.setExpression) window.setExpression(o); });
                    scene.onBeforeRenderObservable.addOnce(() => {
                        try {
                            const b = root.getHierarchyBoundingVectors?.(true);
                            if (b?.min && b?.max) {
                                const center = BABYLON.Vector3.Center(b.min, b.max);
                                const size = b.max.subtract(b.min);
                                const maxDim = Math.max(size.x, size.y, size.z);
                                camera.setTarget(center);
                                camera.radius = Math.min(Math.max(maxDim * 1.1 + 0.4, 2), 7);
                            }
                        } catch (_) {}
                    });
                    return scene;
                }
            }
        } catch (_) { /* fallback to procedural MetaHuman */ }
        // Build procedural MetaHuman (lightweight or GLB failed) — closes the loop
        const simpleFace = buildSimpleMetaHuman(scene, camera, faceState);
        if (simpleFace) return simpleFace;
    }

    const face = new BABYLON.TransformNode("face", scene);
    face.scaling = new BABYLON.Vector3(1.15, 1.15, 1.15);

    const perfMode = typeof window !== 'undefined' && (
        window.__BRIDGE_TWIN_PERFORMANCE_MODE ||
        (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.DEV) ||
        (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 8)
    );
    const useHighFidelitySkin = typeof window !== 'undefined' && window.__BRIDGE_HIGH_FIDELITY_SKIN !== false;
    const skinMat = useHighFidelitySkin
        ? createHighFidelitySkinMaterial(scene, { albedoSize: perfMode ? 512 : 1024 })
        : (() => {
            const m = new BABYLON.PBRMaterial("skin", scene);
            m.albedoColor = new BABYLON.Color3(0.96, 0.72, 0.6);
            m.roughness = 0.42;
            m.metallic = 0;
            m.ambientColor = new BABYLON.Color3(0.42, 0.3, 0.26);
            m.subSurface.isTranslucencyEnabled = true;
            m.subSurface.translucencyIntensity = 0.4;
            m.subSurface.tintColor = new BABYLON.Color3(0.9, 0.5, 0.45);
            const skinTex = new BABYLON.DynamicTexture("skinTexture", 256, scene, false);
            const ctx = skinTex.getContext();
            const baseR = 245, baseG = 184, baseB = 153;
            const imgData = ctx.createImageData(256, 256);
            const data = imgData.data;
            for (let y = 0; y < 256; y++) {
                for (let x = 0; x < 256; x++) {
                    const idx = (y * 256 + x) * 4;
                    const nx = x / 256, ny = y / 256;
                    let r = baseR, g = baseG, b = baseB;
                    for (let i = 0; i < 8; i++) {
                        const px = (Math.sin(nx * 47 + i) * 0.5 + 0.5) * 256;
                        const py = (Math.cos(ny * 31 + i * 1.3) * 0.5 + 0.5) * 256;
                        if (Math.hypot(x - px, y - py) < 1.5) { r -= 10; g -= 7; b -= 6; }
                    }
                    const noise = (Math.sin(x * 0.5) * Math.cos(y * 0.4) + 1) * 0.5;
                    r = Math.max(218, Math.min(255, r + (noise - 0.5) * 20));
                    g = Math.max(162, Math.min(198, g + (noise - 0.5) * 14));
                    b = Math.max(132, Math.min(172, b + (noise - 0.5) * 16));
                    data[idx] = r; data[idx + 1] = g; data[idx + 2] = b; data[idx + 3] = 255;
                }
            }
            ctx.putImageData(imgData, 0, 0);
            skinTex.update();
            m.albedoTexture = skinTex;
            return m;
        })();

    // Lip material: reddish, slightly glossy (vermillion)
    const lipMat = new BABYLON.PBRMaterial("lip", scene);
    lipMat.albedoColor = new BABYLON.Color3(0.82, 0.35, 0.32);
    lipMat.roughness = 0.25;
    lipMat.metallic = 0;
    lipMat.ambientColor = new BABYLON.Color3(0.5, 0.2, 0.18);
    lipMat.subSurface.isTranslucencyEnabled = true;
    lipMat.subSurface.translucencyIntensity = 0.3;
    lipMat.subSurface.tintColor = new BABYLON.Color3(0.9, 0.4, 0.38);

    // Teeth material: off-white, slightly glossy
    const teethMat = new BABYLON.PBRMaterial("teeth", scene);
    teethMat.albedoColor = new BABYLON.Color3(0.98, 0.96, 0.92);
    teethMat.roughness = 0.2;
    teethMat.metallic = 0;
    teethMat.ambientColor = new BABYLON.Color3(0.35, 0.33, 0.32);

    // Tongue material: pink
    const tongueMat = new BABYLON.PBRMaterial("tongue", scene);
    tongueMat.albedoColor = new BABYLON.Color3(0.88, 0.4, 0.38);
    tongueMat.roughness = 0.35;
    tongueMat.metallic = 0;
    tongueMat.subSurface.isTranslucencyEnabled = true;
    tongueMat.subSurface.translucencyIntensity = 0.25;

    const boneMat = new BABYLON.StandardMaterial("bone", scene);
    boneMat.diffuseColor = new BABYLON.Color3(0.9, 0.86, 0.82);
    boneMat.specularColor = new BABYLON.Color3(0.28, 0.26, 0.24);

    // ==========================
    // LAYER 0: SKULL (cranium base)
    // ==========================
    const skull = BABYLON.MeshBuilder.CreateSphere("skull", {
        diameterX: 0.75,
        diameterY: 0.98,
        diameterZ: 0.72,
        segments: 64
    }, scene);
    skull.position.z = -0.03;
    skull.material = boneMat;
    skull.parent = face;
    skull.isVisible = false;

    // ==========================
    // LAYER 1: FOREHEAD + TEMPLES (frontal shape, proportional)
    // ==========================
    const forehead = BABYLON.MeshBuilder.CreateSphere("forehead", { diameter: 0.45, segments: 24 }, scene);
    forehead.scaling.set(1.05, 1.25, 0.75);
    forehead.position.set(0, 0.35, 0.25);
    forehead.material = skinMat;
    forehead.parent = face;

    const templeL = BABYLON.MeshBuilder.CreateSphere("templeL", { diameter: 0.28, segments: 20 }, scene);
    templeL.scaling.set(0.55, 1, 0.85);
    templeL.position.set(-0.34, 0.15, 0.02);
    templeL.material = skinMat;
    templeL.parent = face;

    const templeR = templeL.clone("templeR");
    templeR.position.x = 0.34;
    templeR.parent = face;

    // ==========================
    // LAYER 1b: EARS
    // ==========================
    function createEar(side) {
        const earGroup = new BABYLON.TransformNode("earGroup", scene);
        earGroup.position.set(side === 'L' ? -0.42 : 0.42, 0.02, 0.08);
        earGroup.rotation.y = side === 'L' ? -0.25 : 0.25;
        earGroup.parent = face;

        const helix = BABYLON.MeshBuilder.CreateCylinder("helix", {
            height: 0.28,
            diameterTop: 0.05,
            diameterBottom: 0.07,
            tessellation: 12
        }, scene);
        helix.rotation.x = Math.PI / 2;
        helix.rotation.z = side === 'L' ? 0.15 : -0.15;
        helix.position.set(0, 0, 0.02);
        helix.material = skinMat;
        helix.parent = earGroup;

        const concha = BABYLON.MeshBuilder.CreateSphere("concha", { diameter: 0.12, segments: 16 }, scene);
        concha.scaling.set(0.6, 1.1, 0.4);
        concha.position.set(side === 'L' ? 0.03 : -0.03, -0.02, 0.04);
        concha.rotation.y = side === 'L' ? 0.2 : -0.2;
        concha.material = skinMat;
        concha.parent = earGroup;

        const lobe = BABYLON.MeshBuilder.CreateSphere("lobe", { diameter: 0.08, segments: 12 }, scene);
        lobe.scaling.set(0.7, 1.2, 0.5);
        lobe.position.set(side === 'L' ? 0.02 : -0.02, -0.18, 0.02);
        lobe.material = skinMat;
        lobe.parent = earGroup;

        return earGroup;
    }
    const earL = createEar('L');
    const earR = createEar('R');

    // ==========================
    // LAYER 2: STRUCTURED HEAD BASE (sculpted anatomy)
    // ==========================
    const headSegs = perfMode ? 32 : 40;
    const head = BABYLON.MeshBuilder.CreateSphere("head", {
        diameterX: 0.82,
        diameterY: 1.05,
        diameterZ: 0.8,
        segments: headSegs
    }, scene);
    head.material = skinMat;
    head.parent = face;

    let basePositions = head.getVerticesData(BABYLON.VertexBuffer.PositionKind);
    for (let i = 0; i < basePositions.length; i += 3) {
        const x = basePositions[i], y = basePositions[i + 1], z = basePositions[i + 2];
        if (y > 0.28) basePositions[i + 2] *= 0.88;
        if (y > 0.05 && y < 0.28) basePositions[i + 2] += 0.05;
        if (y > -0.1 && y < 0.05 && z > 0.2) basePositions[i + 2] += 0.07;
        if (Math.abs(x) < 0.04 && y > -0.08 && y < 0) basePositions[i + 2] -= 0.04;
        if (Math.abs(x) < 0.09 && y > 0 && y < 0.15) basePositions[i + 2] += 0.08;
        if (Math.abs(x) < 0.15 && y < -0.08 && y > -0.18) basePositions[i + 2] += 0.05;
        if (y < -0.2) basePositions[i + 2] *= 0.92;
        if (Math.abs(x) > 0.22 && y > -0.05 && y < 0.2) {
            basePositions[i] *= 1.12;
            basePositions[i + 2] += 0.05;
        }
        if (Math.abs(x) > 0.27 && y > 0.15) basePositions[i + 2] -= 0.05;
        if (y < -0.28 && z > 0.1) basePositions[i + 2] += 0.1;
        if (z < -0.15) basePositions[i + 2] *= 0.65;
        if (Math.abs(x) < 0.25 && y > 0.04 && y < 0.35 && z > 0.18) basePositions[i + 2] -= 0.12;
        if (Math.abs(x) > 0.18 && y > -0.08 && y < 0.25 && z > 0.08) {
            basePositions[i] *= 1.1;
            basePositions[i + 2] += 0.05;
        }
        if (y < -0.18 && Math.abs(x) > 0.18) basePositions[i] *= 1.12;
        if (Math.abs(x) < 0.12 && y > 0.08 && y < 0.25 && z > 0.15) basePositions[i + 2] -= 0.15;
        if (Math.abs(x) < 0.15 && y > 0.1 && y < 0.28 && z > 0.12) basePositions[i + 2] += 0.06;
        if (basePositions[i] > 0) basePositions[i] *= 1.008;
    }
    head.updateVerticesData(BABYLON.VertexBuffer.PositionKind, basePositions);

    // ==========================
    // CRANIUM / SCALP (top & back of head) - full spheres for reliable display
    // ==========================
    const cranium = BABYLON.MeshBuilder.CreateSphere("cranium", {
        diameterX: 0.8,
        diameterY: 0.85,
        diameterZ: 0.78,
        segments: 48
    }, scene);
    cranium.position.set(0, 0.35, 0.08);
    cranium.material = skinMat;
    cranium.parent = face;

    const occiput = BABYLON.MeshBuilder.CreateSphere("occiput", {
        diameterX: 0.76,
        diameterY: 0.88,
        diameterZ: 0.7,
        segments: 40
    }, scene);
    occiput.position.set(0, 0.02, -0.25);
    occiput.material = skinMat;
    occiput.parent = face;

    // ==========================
    // GLABELLA / CORRUGATOR (between brows)
    // ==========================
    const glabellaMat = new BABYLON.PBRMaterial("glabella", scene);
    glabellaMat.albedoColor = new BABYLON.Color3(0.85, 0.6, 0.52);
    glabellaMat.roughness = 0.85;
    const glabella = BABYLON.MeshBuilder.CreatePlane("glabella", { width: 0.07, height: 0.015, sideOrientation: BABYLON.Mesh.DOUBLESIDE }, scene);
    glabella.rotation.x = -0.15;
    glabella.position.set(0, 0.31, 0.38);
    glabella.material = glabellaMat;
    glabella.parent = face;

    // ==========================
    // CROW'S FEET (outer eye corners - orbicularis oculi)
    // ==========================
    const crowsFeetMat = new BABYLON.PBRMaterial("crowsFeet", scene);
    crowsFeetMat.albedoColor = new BABYLON.Color3(0.8, 0.58, 0.5);
    crowsFeetMat.roughness = 0.9;
    const crowsFeetL = BABYLON.MeshBuilder.CreatePlane("crowsFeetL", { width: 0.022, height: 0.004, sideOrientation: BABYLON.Mesh.DOUBLESIDE }, scene);
    crowsFeetL.rotation.set(-0.15, 0, 0.2);
    crowsFeetL.position.set(-0.32, 0.07, 0.38);
    crowsFeetL.material = crowsFeetMat;
    crowsFeetL.parent = face;
    const crowsFeetR = crowsFeetL.clone("crowsFeetR");
    crowsFeetR.rotation.z = -0.2;
    crowsFeetR.position.x = 0.32;
    crowsFeetR.parent = face;

    // ==========================
    // FRONTALIS LINES (forehead - expression lines)
    // ==========================
    const frontalisMat = new BABYLON.PBRMaterial("frontalis", scene);
    frontalisMat.albedoColor = new BABYLON.Color3(0.82, 0.6, 0.52);
    frontalisMat.roughness = 0.88;
    const frontalisLines = BABYLON.MeshBuilder.CreatePlane("frontalisLines", { width: 0.2, height: 0.006, sideOrientation: BABYLON.Mesh.DOUBLESIDE }, scene);
    frontalisLines.rotation.x = -0.1;
    frontalisLines.position.set(0, 0.42, 0.34);
    frontalisLines.material = frontalisMat;
    frontalisLines.parent = face;

    // ==========================
    // LAYER 3: BROW RIDGE (supraorbital)
    // ==========================
    const browRidge = BABYLON.MeshBuilder.CreateSphere("browRidge", { diameter: 0.32, segments: 20 }, scene);
    browRidge.scaling.set(1.15, 0.45, 0.85);
    browRidge.position.set(0, 0.26, 0.35);
    browRidge.rotation.x = -0.06;
    browRidge.material = skinMat;
    browRidge.parent = face;

    // ==========================
    // LAYER 4: ORBITAL RIMS (eye socket edges - subtle, behind eyes)
    // ==========================
    const orbitRimL = BABYLON.MeshBuilder.CreateTorus("orbitRimL", { diameter: 0.16, thickness: 0.018, tessellation: 24 }, scene);
    orbitRimL.rotation.x = Math.PI / 2;
    orbitRimL.rotation.z = 0.12;
    orbitRimL.position.set(-0.2, 0.12, 0.36);
    orbitRimL.material = skinMat;
    orbitRimL.parent = face;

    const orbitRimR = orbitRimL.clone("orbitRimR");
    orbitRimR.position.x = 0.2;
    orbitRimR.rotation.z = -0.12;
    orbitRimR.parent = face;

    // ==========================
    // LAYER 5: CHEEKBONES (zygomatic - proportional to face)
    // ==========================
    const cheekboneL = BABYLON.MeshBuilder.CreateSphere("cheekboneL", { diameter: 0.22, segments: 24 }, scene);
    cheekboneL.scaling.set(0.7, 0.9, 1.05);
    cheekboneL.position.set(-0.27, -0.02, 0.36);
    cheekboneL.rotation.y = 0.2;
    cheekboneL.material = skinMat;
    cheekboneL.parent = face;

    const cheekboneR = cheekboneL.clone("cheekboneR");
    cheekboneR.position.x = 0.27;
    cheekboneR.rotation.y = -0.2;
    cheekboneR.parent = face;

    // ==========================
    // LAYER 6: MALAR (below cheekbone)
    // ==========================
    const malarL = BABYLON.MeshBuilder.CreateSphere("malarL", { diameter: 0.1, segments: 16 }, scene);
    malarL.scaling.set(0.9, 1.1, 1);
    malarL.position.set(-0.24, -0.1, 0.33);
    malarL.material = skinMat;
    malarL.parent = face;

    const malarR = malarL.clone("malarR");
    malarR.position.x = 0.24;
    malarR.parent = face;

    // ==========================
    // LAYER 7: NASAL BRIDGE (dorsum - proportional)
    // ==========================
    const nasalRidge = BABYLON.MeshBuilder.CreateCylinder("nasalRidge", {
        height: 0.18,
        diameterTop: 0.018,
        diameterBottom: 0.05,
        tessellation: 16
    }, scene);
    nasalRidge.rotation.x = Math.PI / 2;
    nasalRidge.position.set(0, 0.06, 0.4);
    nasalRidge.material = skinMat;
    nasalRidge.parent = face;

    // ==========================
    // LAYER 8: MOUTH + LIPS (philtrum, cupid's bow, vermillion)
    // ==========================
    const philtrum = BABYLON.MeshBuilder.CreateBox("philtrum", { width: 0.08, height: 0.06, depth: 0.025 }, scene);
    philtrum.position.set(0, -0.18, 0.46);
    philtrum.rotation.x = 0.1;
    philtrum.material = skinMat;
    philtrum.parent = face;

    const upperLip = BABYLON.MeshBuilder.CreateSphere("upperLip", { diameter: 0.13, segments: 20 }, scene);
    upperLip.scaling.set(1.15, 0.45, 0.75);
    upperLip.position.set(0, -0.19, 0.48);
    upperLip.rotation.x = 0.22;
    upperLip.material = lipMat;
    upperLip.parent = face;

    const lowerLip = BABYLON.MeshBuilder.CreateSphere("lowerLip", { diameter: 0.12, segments: 20 }, scene);
    lowerLip.scaling.set(1.1, 0.42, 0.7);
    lowerLip.position.set(0, -0.255, 0.475);
    lowerLip.rotation.x = 0.12;
    lowerLip.material = lipMat;
    lowerLip.parent = face;

    const mouthCornerL = BABYLON.MeshBuilder.CreateSphere("mouthCornerL", { diameter: 0.028, segments: 12 }, scene);
    mouthCornerL.scaling.set(0.8, 1.2, 0.6);
    mouthCornerL.position.set(-0.15, -0.22, 0.46);
    mouthCornerL.material = lipMat;
    mouthCornerL.parent = face;

    const mouthCornerR = mouthCornerL.clone("mouthCornerR");
    mouthCornerR.position.x = 0.15;
    mouthCornerR.parent = face;

    // ==========================
    // TEETH (upper - fixed to head)
    // ==========================
    const upperTeeth = BABYLON.MeshBuilder.CreateBox("upperTeeth", { width: 0.18, height: 0.04, depth: 0.06 }, scene);
    upperTeeth.position.set(0, -0.18, 0.465);
    upperTeeth.rotation.x = 0.22;
    upperTeeth.material = teethMat;
    upperTeeth.renderingGroupId = 1;
    upperTeeth.parent = face;

    // ==========================
    // LAYER 9: CHIN + JAW ANGLES (proportional)
    // ==========================
    const chinBoss = BABYLON.MeshBuilder.CreateSphere("chinBoss", { diameter: 0.2, segments: 22 }, scene);
    chinBoss.scaling.set(0.9, 0.7, 1);
    chinBoss.position.set(0, -0.36, 0.36);
    chinBoss.rotation.x = -0.15;
    chinBoss.material = skinMat;
    chinBoss.parent = face;

    const mentalis = BABYLON.MeshBuilder.CreateSphere("mentalis", { diameter: 0.06, segments: 14 }, scene);
    mentalis.scaling.set(0.85, 0.7, 0.6);
    mentalis.position.set(0, -0.39, 0.38);
    mentalis.rotation.x = -0.12;
    mentalis.material = skinMat;
    mentalis.parent = face;

    const jawAngleL = BABYLON.MeshBuilder.CreateSphere("jawAngleL", { diameter: 0.08, segments: 14 }, scene);
    jawAngleL.scaling.set(0.85, 1.1, 0.95);
    jawAngleL.position.set(-0.28, -0.32, 0.24);
    jawAngleL.rotation.z = 0.08;
    jawAngleL.material = skinMat;
    jawAngleL.parent = face;

    const jawAngleR = jawAngleL.clone("jawAngleR");
    jawAngleR.position.x = 0.28;
    jawAngleR.rotation.z = -0.08;
    jawAngleR.parent = face;

    // ==========================
    // LAYER 10: NECK BASE (proportional)
    // ==========================
    const neckBase = BABYLON.MeshBuilder.CreateCylinder("neckBase", {
        height: 0.12,
        diameterTop: 0.3,
        diameterBottom: 0.32,
        tessellation: 22
    }, scene);
    neckBase.position.set(0, -0.48, 0.12);
    neckBase.rotation.x = 0.08;
    neckBase.material = skinMat;
    neckBase.parent = face;

    // ==========================
    // FULL BODY: torso, arms, legs, hands (fingers), feet (toes), hair
    // ==========================
    buildBody(scene, face, skinMat, perfMode);

    let current = basePositions.slice();
    const velocity = new Float32Array(basePositions.length);

    function isBoneLocked(vx, vy, vz) {
        if (vz < -0.1) return true;
        if (vy > 0.4) return true;
        return false;
    }

    function stiffness(x, y, z) {
        if (y > 0.22 && z > 0.15) return 0.4;
        if (Math.abs(x) < 0.06 && y > 0.1) return 0.3;
        if (y < -0.2 && Math.abs(x) > 0.18) return 0.5;
        if (Math.abs(x) > 0.22 && y > -0.05 && y < 0.2) return 0.6;
        return 1;
    }

    function planeLock(vx, vy, vz) {
        if (vy > 0.3) return new BABYLON.Vector3(0, 0, -0.025);
        if (vy < -0.25) return new BABYLON.Vector3(0, 0, 0.02);
        return null;
    }

    function accumulateForce(anchor, dir, radius, strength, forceArray, positions) {
        for (let i = 0; i < basePositions.length; i += 3) {
            const vx = positions[i], vy = positions[i + 1], vz = positions[i + 2];
            if (isBoneLocked(vx, vy, vz)) continue;
            const dx = vx - anchor.x, dy = vy - anchor.y, dz = vz - anchor.z;
            const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
            if (dist < radius) {
                const falloff = Math.exp(-(dist * dist) / (radius * radius));
                forceArray[i] += dir.x * strength * falloff;
                forceArray[i + 1] += dir.y * strength * falloff;
                forceArray[i + 2] += dir.z * strength * falloff;
            }
        }
    }

    const zygLeft = new BABYLON.Vector3(-0.2, -0.06, 0.3);
    const zygRight = new BABYLON.Vector3(0.2, -0.06, 0.3);
    const orbitLeft = new BABYLON.Vector3(-0.2, 0.1, 0.34);
    const orbitRight = new BABYLON.Vector3(0.2, 0.1, 0.34);
    const browLeft = new BABYLON.Vector3(-0.2, 0.24, 0.36);
    const browRight = new BABYLON.Vector3(0.2, 0.24, 0.36);

    // ==========================
    // EYES (detailed: sclera veins, iris stroma, limbus, pupil, cornea)
    // ==========================
    const irisColor = (typeof window !== 'undefined' && window.__BRIDGE_IRIS_COLOR) || "blue";
    const eyeMats = createDetailedEyeMaterials(scene, irisColor);
    const scleraMat = eyeMats.scleraMat;
    const irisMat = eyeMats.irisMat;
    const pupilMat = eyeMats.pupilMat;
    const corneaMat = eyeMats.corneaMat;

    function createEye(x) {
        const eyeGroup = new BABYLON.TransformNode("eyeGroup", scene);
        eyeGroup.position = new BABYLON.Vector3(x, 0.1, 0.39);
        eyeGroup.parent = face;

        const sclera = BABYLON.MeshBuilder.CreateSphere("sclera", { diameter: 0.19, segments: 48 }, scene);
        sclera.position = BABYLON.Vector3.Zero();
        sclera.material = scleraMat;
        sclera.renderingGroupId = 1;
        sclera.parent = eyeGroup;

        const iris = BABYLON.MeshBuilder.CreateDisc("iris", { radius: 0.058, tessellation: 48 }, scene);
        iris.rotation.y = x > 0 ? -Math.PI / 2 : Math.PI / 2;
        iris.position = new BABYLON.Vector3(0, 0, 0.096);
        iris.material = irisMat;
        iris.renderingGroupId = 1;
        iris.parent = eyeGroup;

        const pupil = BABYLON.MeshBuilder.CreateDisc("pupil", { radius: 0.02, tessellation: 32 }, scene);
        pupil.rotation.y = iris.rotation.y;
        pupil.position = new BABYLON.Vector3(0, 0, 0.097);
        pupil.material = pupilMat;
        pupil.renderingGroupId = 1;
        pupil.parent = eyeGroup;

        const limbus = BABYLON.MeshBuilder.CreateTorus("limbus", { diameter: 0.12, thickness: 0.008, tessellation: 48 }, scene);
        limbus.rotation.x = Math.PI / 2;
        limbus.rotation.y = x > 0 ? Math.PI / 2 : -Math.PI / 2;
        limbus.position = new BABYLON.Vector3(0, 0, 0.0965);
        limbus.material = eyeMats.limbusMat;
        limbus.renderingGroupId = 1;
        limbus.parent = eyeGroup;

        const cornea = BABYLON.MeshBuilder.CreateSphere("cornea", { diameter: 0.18, segments: 32 }, scene);
        cornea.scaling.set(1, 1, 0.65);
        cornea.position = new BABYLON.Vector3(0, 0, 0.095);
        cornea.material = corneaMat;
        cornea.renderingGroupId = 2;
        cornea.parent = eyeGroup;

        const upperLid = BABYLON.MeshBuilder.CreateSphere("upperLid", {
            diameter: 0.23,
            arc: 1,
            slice: 0.45,
            segments: 24
        }, scene);
        upperLid.scaling.set(1, 0.42, 0.6);
        upperLid.rotation.x = Math.PI * 0.55;
        upperLid.position.set(0, 0.058, 0.092);
        upperLid.material = skinMat;
        upperLid.parent = eyeGroup;

        const lowerLid = BABYLON.MeshBuilder.CreateSphere("lowerLid", {
            diameter: 0.21,
            arc: 1,
            slice: 0.4,
            segments: 20
        }, scene);
        lowerLid.scaling.set(0.95, 0.36, 0.55);
        lowerLid.rotation.x = -Math.PI * 0.55;
        lowerLid.position.set(0, -0.05, 0.082);
        lowerLid.material = skinMat;
        lowerLid.parent = eyeGroup;

        return { group: eyeGroup, sclera, iris, pupil, cornea, upperLid, lowerLid };
    }
    const leftEye = createEye(-0.2);
    const rightEye = createEye(0.2);

    // ==========================
    // EYEBROWS
    // ==========================
    function createBrow(side) {
        const brow = BABYLON.MeshBuilder.CreateCylinder("brow", {
            height: 0.25,
            diameterTop: 0.022,
            diameterBottom: 0.025,
            tessellation: 12
        }, scene);
        brow.rotation.x = Math.PI / 2;
        brow.rotation.z = side === 'L' ? 0.05 : -0.05;
        brow.position = new BABYLON.Vector3(side === 'L' ? -0.2 : 0.2, 0.24, 0.4);
        const browMat = new BABYLON.PBRMaterial("brow", scene);
        browMat.albedoColor = new BABYLON.Color3(0.2, 0.14, 0.1);
        browMat.roughness = 0.8;
        brow.material = browMat;
        brow.parent = face;
        return brow;
    }
    const leftBrow = createBrow('L');
    const rightBrow = createBrow('R');

    // ==========================
    // NOSE (realistic: bridge, dorsum, tip, alar wings)
    // ==========================
    const noseGroup = new BABYLON.TransformNode("noseGroup", scene);
    noseGroup.position = new BABYLON.Vector3(0, 0, 0.4);
    noseGroup.parent = face;

    const bridge = BABYLON.MeshBuilder.CreateSphere("bridge", { diameter: 0.14, segments: 24 }, scene);
    bridge.scaling.set(0.45, 1.4, 0.5);
    bridge.position.set(0, 0.08, 0.06);
    bridge.rotation.x = -0.12;
    bridge.material = skinMat;
    bridge.parent = noseGroup;

    const dorsum = BABYLON.MeshBuilder.CreateSphere("dorsum", { diameter: 0.12, segments: 20 }, scene);
    dorsum.scaling.set(0.55, 0.9, 0.7);
    dorsum.position.set(0, -0.02, 0.1);
    dorsum.rotation.x = -0.05;
    dorsum.material = skinMat;
    dorsum.parent = noseGroup;

    const tip = BABYLON.MeshBuilder.CreateSphere("tip", { diameter: 0.11, segments: 24 }, scene);
    tip.scaling.set(0.85, 0.75, 1);
    tip.position.set(0, -0.1, 0.14);
    tip.material = skinMat;
    tip.parent = noseGroup;

    const alaL = BABYLON.MeshBuilder.CreateSphere("alaL", { diameter: 0.05, segments: 16 }, scene);
    alaL.scaling.set(0.8, 0.5, 1.1);
    alaL.position.set(-0.032, -0.09, 0.12);
    alaL.rotation.z = 0.12;
    alaL.material = skinMat;
    alaL.parent = noseGroup;

    const alaR = alaL.clone("alaR");
    alaR.position.x = 0.032;
    alaR.rotation.z = -0.12;
    alaR.parent = noseGroup;

    const nostrilL = BABYLON.MeshBuilder.CreateSphere("nostrilL", { diameter: 0.025, segments: 12 }, scene);
    nostrilL.scaling.set(0.9, 0.6, 1);
    nostrilL.position.set(-0.025, -0.1, 0.14);
    nostrilL.material = skinMat;
    nostrilL.parent = noseGroup;
    const nostrilR = nostrilL.clone("nostrilR");
    nostrilR.position.x = 0.025;
    nostrilR.parent = noseGroup;

    const columella = BABYLON.MeshBuilder.CreateBox("columella", { width: 0.018, height: 0.035, depth: 0.04 }, scene);
    columella.position.set(0, -0.14, 0.15);
    columella.rotation.x = 0.2;
    columella.material = skinMat;
    columella.parent = noseGroup;

    const nose = noseGroup;

    // ==========================
    // TEAR DUCTS (inner canthus)
    // ==========================
    const tearDuctMat = new BABYLON.PBRMaterial("tearDuct", scene);
    tearDuctMat.albedoColor = new BABYLON.Color3(0.92, 0.88, 0.9);
    tearDuctMat.roughness = 0.25;
    const tearDuctL = BABYLON.MeshBuilder.CreateSphere("tearDuctL", { diameter: 0.03, segments: 12 }, scene);
    tearDuctL.position.set(-0.16, 0.08, 0.42);
    tearDuctL.scaling.set(0.6, 0.8, 0.5);
    tearDuctL.material = tearDuctMat;
    tearDuctL.parent = face;
    const tearDuctR = tearDuctL.clone("tearDuctR");
    tearDuctR.position.x = 0.16;
    tearDuctR.parent = face;

    // ==========================
    // EYELASHES (subtle cylinders)
    // ==========================
    const lashMat = new BABYLON.PBRMaterial("lash", scene);
    lashMat.albedoColor = new BABYLON.Color3(0.08, 0.05, 0.04);
    lashMat.roughness = 0.9;
    function createLashRow(side, isUpper) {
        const count = perfMode ? 5 : 8;
        const row = new BABYLON.TransformNode("lashRow", scene);
        row.position.set(side === 'L' ? -0.2 : 0.2, 0.1, 0.405);
        row.parent = face;
        for (let i = 0; i < count; i++) {
            const lash = BABYLON.MeshBuilder.CreateCylinder("lash", { height: 0.012, diameterTop: 0.002, diameterBottom: 0.003, tessellation: 6 }, scene);
            lash.rotation.x = Math.PI / 2;
            lash.rotation.z = (i / count - 0.5) * (side === 'L' ? 1 : -1) * 0.5;
            lash.position.set((i / count - 0.5) * 0.06 * (side === 'L' ? 1 : -1), isUpper ? 0.04 : -0.04, 0.02);
            lash.scaling.z = isUpper ? 1 : 0.7;
            lash.material = lashMat;
            lash.parent = row;
        }
        return row;
    }
    createLashRow('L', true);
    createLashRow('L', false);
    createLashRow('R', true);
    createLashRow('R', false);

    // ==========================
    // NASOLABIAL FOLDS (smile lines – subtle crease)
    // ==========================
    const nasolabialMat = new BABYLON.PBRMaterial("nasolabial", scene);
    nasolabialMat.albedoColor = new BABYLON.Color3(0.82, 0.6, 0.55);
    nasolabialMat.roughness = 0.9;
    nasolabialMat.ambientColor = new BABYLON.Color3(0.5, 0.35, 0.32);
    const nasolabialL = BABYLON.MeshBuilder.CreatePlane("nasolabialL", { width: 0.07, height: 0.02, sideOrientation: BABYLON.Mesh.DOUBLESIDE }, scene);
    nasolabialL.rotation.x = -0.3;
    nasolabialL.rotation.z = -0.15;
    nasolabialL.position.set(-0.14, -0.08, 0.42);
    nasolabialL.material = nasolabialMat;
    nasolabialL.parent = face;
    const nasolabialR = nasolabialL.clone("nasolabialR");
    nasolabialR.rotation.z = 0.15;
    nasolabialR.position.x = 0.14;
    nasolabialR.parent = face;

    // ==========================
    // JAW PIVOT + MANDIBLE
    // ==========================
    const jawPivot = new BABYLON.TransformNode("jawPivot", scene);
    jawPivot.position.set(0, -0.48, 0.12);
    jawPivot.parent = face;

    const jaw = BABYLON.MeshBuilder.CreateSphere("jaw", { diameter: 0.45, segments: 26 }, scene);
    jaw.scaling.set(1.15, 0.5, 1.05);
    jaw.position.set(0, 0.1, 0.16);
    jaw.rotation.x = 0.1;
    jaw.material = skinMat;
    jaw.parent = jawPivot;

    const tongue = BABYLON.MeshBuilder.CreateSphere("tongue", { diameter: 0.12, segments: 16 }, scene);
    tongue.scaling.set(1.1, 0.35, 0.7);
    tongue.position.set(0, 0.1, 0.36);
    tongue.rotation.x = 0.12;
    tongue.material = tongueMat;
    tongue.renderingGroupId = 1;
    tongue.parent = jawPivot;

    const lowerTeeth = BABYLON.MeshBuilder.CreateBox("lowerTeeth", { width: 0.17, height: 0.035, depth: 0.055 }, scene);
    lowerTeeth.position.set(0, 0.14, 0.34);
    lowerTeeth.rotation.x = 0.06;
    lowerTeeth.material = teethMat;
    lowerTeeth.renderingGroupId = 1;
    lowerTeeth.parent = jawPivot;

    // ==========================
    // SHADING: shadows + ambient occlusion (reduced for rAF perf)
    // ==========================
    const shadowMapSize = perfMode ? 256 : 384;
    const shadowGen = new BABYLON.ShadowGenerator(shadowMapSize, dir1);
    shadowGen.usePercentageCloserFiltering = !perfMode;  // PCF off in perf mode (reduces rAF cost)
    shadowGen.bias = 0.0001;
    const shadowGen2 = new BABYLON.ShadowGenerator(shadowMapSize >> 1, dir2);
    shadowGen2.usePercentageCloserFiltering = !perfMode;
    if (!perfMode) {
        scene.meshes.forEach(m => {
            if (m instanceof BABYLON.Mesh && m.isVisible !== false && m !== skull) {
                shadowGen.addShadowCaster(m);
                shadowGen2.addShadowCaster(m);
                m.receiveShadows = true;
            }
        });
    }

    scene._faceState = { smile: undefined, blink: undefined, jawOpen: undefined, eyeYaw: undefined, frown: undefined };
    scene._physiology = { baselineTone: 0.02, arousal: 1 };
    scene._backendFaceState = faceState;

    // Apply face rendering rules from backend health
    const faceMeshes = face.getChildMeshes ? face.getChildMeshes(true) : [];
    if (faceState === 'OFFLINE') {
        const wireMat = new BABYLON.StandardMaterial("wireframe_offline", scene);
        wireMat.wireframe = true;
        wireMat.diffuseColor = new BABYLON.Color3(0.9, 0.1, 0.1);
        wireMat.emissiveColor = new BABYLON.Color3(0.4, 0, 0);
        faceMeshes.forEach(m => {
            if (m instanceof BABYLON.Mesh && m.material) {
                m.material = wireMat;
                m.material.wireframe = true;
            }
        });
    } else if (faceState === 'DEGRADED') {
        const amberTint = new BABYLON.Color3(1, 0.75, 0.4);
        [skinMat, lipMat].forEach(mat => {
            if (mat && mat.ambientColor) mat.ambientColor = mat.ambientColor.multiply(amberTint);
            if (mat && mat.albedoColor) mat.albedoColor = mat.albedoColor.multiply(amberTint);
        });
        if (scleraMat) { scleraMat.albedoColor = new BABYLON.Color3(0.7, 0.65, 0.6); }
        if (irisMat) { irisMat.albedoColor = new BABYLON.Color3(0.35, 0.5, 0.6); }
    }

    let zygLeftActivation = 0, zygRightActivation = 0;
    let orbLeftActivation = 0, orbRightActivation = 0;
    let corrLeftActivation = 0, corrRightActivation = 0;
    let avgStrain = 0;
    let blinkPhase = 0;
    let eyeYawTarget = 0, eyeYawCurrent = 0;
    let eyeYawTimer = 0;
    let _frameSkip = 0;  // Run heavy vertex physics every 30th frame to avoid rAF violations
    let _warmupFrames = 8;  // Skip heavy loop for first frames to avoid initial rAF violation
    const ACT_RATE = 0.12;
    const ACT_DECAY = 0.995;
    const COUPLING = 0.025;
    const STRAIN_FEEDBACK = 0.08;
    const MICRO_ACT = 0.0008;

    // ==========================
    // LOOP (coupled neuromuscular → force → deformation)
    // Throttled: run every 2nd frame to keep rAF under 16ms
    // ==========================
    let _loopFrame = 0;
    scene.registerBeforeRender(() => {
        _loopFrame++;
        if (_loopFrame % 2 !== 0) return;  // Skip every other frame
        _frameSkip = (_frameSkip + 1) % 30;
        if (_warmupFrames > 0) _warmupFrames--;
        const skipHeavy = true;  // Vertex physics disabled to prevent rAF violations (transform-only animation)
        const t = performance.now() * 0.002;
        const s = scene._faceState;
        const phys = scene._physiology;

        const smileTarget = s.smile !== undefined ? s.smile : (Math.sin(t) + 1) / 2;
        blinkPhase += 0.016;
        if (blinkPhase > 8 + Math.random() * 6) blinkPhase = 0;
        const blinkEnabled = scene._backendFaceState !== 'DEGRADED' && scene._backendFaceState !== 'OFFLINE';
        const blinkTarget = !blinkEnabled ? 0 : (s.blink !== undefined ? s.blink : (blinkPhase < 0.15 ? Math.sin(blinkPhase * Math.PI / 0.15) : 0));
        const frownTarget = s.frown !== undefined ? s.frown : 0.12 * (1 - smileTarget);
        const baseline = (phys.baselineTone ?? 0.02) * (phys.arousal ?? 1);

        const orbAvg = (orbLeftActivation + orbRightActivation) * 0.5;
        const zygAvg = (zygLeftActivation + zygRightActivation) * 0.5;
        const strainFeedback = avgStrain * STRAIN_FEEDBACK;

        zygLeftActivation += (smileTarget - zygLeftActivation) * ACT_RATE
            + orbAvg * COUPLING - strainFeedback
            + (Math.random() - 0.5) * MICRO_ACT
            + baseline * 0.002;
        zygLeftActivation *= ACT_DECAY;

        zygRightActivation += (smileTarget - zygRightActivation) * ACT_RATE
            + orbAvg * COUPLING - strainFeedback
            + (Math.random() - 0.5) * MICRO_ACT
            + baseline * 0.002;
        zygRightActivation *= ACT_DECAY;

        orbLeftActivation += (blinkTarget - orbLeftActivation) * ACT_RATE
            + zygLeftActivation * COUPLING - strainFeedback
            + (Math.random() - 0.5) * MICRO_ACT
            + baseline * 0.002;
        orbLeftActivation *= ACT_DECAY;

        orbRightActivation += (blinkTarget - orbRightActivation) * ACT_RATE
            + zygRightActivation * COUPLING - strainFeedback
            + (Math.random() - 0.5) * MICRO_ACT
            + baseline * 0.002;
        orbRightActivation *= ACT_DECAY;

        zygLeftActivation = Math.max(0, Math.min(1, zygLeftActivation));
        zygRightActivation = Math.max(0, Math.min(1, zygRightActivation));
        orbLeftActivation = Math.max(0, Math.min(1, orbLeftActivation));
        orbRightActivation = Math.max(0, Math.min(1, orbRightActivation));

        corrLeftActivation += (frownTarget - corrLeftActivation) * 0.08 + baseline * 0.001;
        corrRightActivation += (frownTarget - corrRightActivation) * 0.08 + baseline * 0.001;
        corrLeftActivation = Math.max(0, Math.min(0.5, corrLeftActivation));
        corrRightActivation = Math.max(0, Math.min(0.5, corrRightActivation));

        if (skipHeavy) {
            // Light frame: skip vertex physics, update only transforms (cheap)
            eyeYawTimer += 0.02;
            if (eyeYawTimer > 2 + Math.random() * 3) {
                eyeYawTarget = (Math.random() - 0.5) * 0.6;
                eyeYawTimer = 0;
            }
            eyeYawCurrent += (eyeYawTarget - eyeYawCurrent) * 0.08;
            const eyeYaw = s.eyeYaw !== undefined ? s.eyeYaw : eyeYawCurrent;
            const blink = orbLeftActivation > 0.1 ? orbLeftActivation : orbRightActivation;
            const jawOpen = s.jawOpen !== undefined ? s.jawOpen : (Math.sin(t * 0.8) * 0.2 + 0.08);
            const zygAvg = (zygLeftActivation + zygRightActivation) * 0.5;
            leftEye.group.rotation.y = eyeYaw;
            rightEye.group.rotation.y = eyeYaw;
            leftEye.upperLid.position.y = 0.058 - blink * 0.055;
            leftEye.upperLid.scaling.y = 0.42 - blink * 0.2;
            rightEye.upperLid.position.y = 0.058 - blink * 0.055;
            rightEye.upperLid.scaling.y = 0.42 - blink * 0.2;
            leftEye.lowerLid.position.y = -0.05 + blink * 0.03;
            rightEye.lowerLid.position.y = -0.05 + blink * 0.03;
            jawPivot.rotation.x = 0.12 + jawOpen * 0.4 + zygAvg * 0.05;
            leftBrow.rotation.x = 0.02 - corrLeftActivation * 0.15 + zygLeftActivation * 0.06;
            rightBrow.rotation.x = 0.02 - corrRightActivation * 0.15 + zygRightActivation * 0.06;
            leftBrow.position.z = 0.42 - orbLeftActivation * 0.03;
            rightBrow.position.z = 0.42 - orbRightActivation * 0.03;
            noseGroup.scaling.x = 1 + (zygAvg * 0.03) + Math.sin(t * 1.5) * 0.015;
            tip.scaling.x = 0.85 + zygAvg * 0.08;
            alaL.scaling.y = 0.6 + zygAvg * 0.1;
            alaR.scaling.y = 0.6 + zygAvg * 0.1;
            cheekboneL.scaling.y = 0.95 + zygLeftActivation * 0.1;
            cheekboneR.scaling.y = 0.95 + zygRightActivation * 0.1;
            malarL.position.z = 0.33 + zygLeftActivation * 0.025;
            malarR.position.z = 0.33 + zygRightActivation * 0.025;
            browRidge.position.z = 0.35 - (corrLeftActivation + corrRightActivation) * 0.015;
            if (glabella) glabella.scaling.y = 1 + (corrLeftActivation + corrRightActivation) * 0.8;
            orbitRimL.position.z = 0.36 - orbLeftActivation * 0.015;
            orbitRimR.position.z = 0.36 - orbRightActivation * 0.015;
            if (crowsFeetL) { crowsFeetL.scaling.x = 0.6 + zygAvg * 0.8; crowsFeetR.scaling.x = 0.6 + zygAvg * 0.8; }
            if (frontalisLines) frontalisLines.scaling.y = 0.5 + (1 - corrLeftActivation - corrRightActivation) * 0.8;
            nasalRidge.scaling.x = 1 + zygAvg * 0.05;
            upperLip.position.z = 0.48 + zygAvg * 0.028;
            upperLip.scaling.y = 0.45 + zygAvg * 0.12;
            lowerLip.position.z = 0.475 + zygAvg * 0.02;
            lowerLip.position.y = -0.255 - jawOpen * 0.07;
            mouthCornerL.position.z = 0.46 + zygLeftActivation * 0.02;
            mouthCornerL.position.y = -0.22 + zygLeftActivation * 0.012;
            mouthCornerR.position.z = 0.46 + zygRightActivation * 0.02;
            mouthCornerR.position.y = -0.22 + zygRightActivation * 0.012;
            philtrum.position.z = 0.46 + zygAvg * 0.015;
            chinBoss.rotation.x = -0.15 - jawOpen * 0.35;
            jawAngleL.rotation.x = jawOpen * 0.2;
            jawAngleR.rotation.x = jawOpen * 0.2;
            tongue.position.z = 0.36 + jawOpen * 0.04;
            tongue.scaling.y = 0.35 + jawOpen * 0.05;
            return;
        }

        const force = new Float32Array(basePositions.length);
        const zygL = Math.min(1, zygLeftActivation * 1.02);
        const zygR = Math.min(1, zygRightActivation * 0.98);
        accumulateForce(zygLeft, new BABYLON.Vector3(-0.12, 0.18, 0.03), 0.36, 0.34 * zygL, force, current);
        accumulateForce(zygRight, new BABYLON.Vector3(0.12, 0.18, 0.03), 0.36, 0.34 * zygR, force, current);
        accumulateForce(orbitLeft, new BABYLON.Vector3(0, -0.15, 0.02), 0.26, 0.2 * orbLeftActivation, force, current);
        accumulateForce(orbitRight, new BABYLON.Vector3(0, -0.15, 0.02), 0.26, 0.2 * orbRightActivation, force, current);
        accumulateForce(browLeft, new BABYLON.Vector3(-0.04, -0.1, -0.03), 0.22, 0.15 * corrLeftActivation, force, current);
        accumulateForce(browRight, new BABYLON.Vector3(0.04, -0.1, -0.03), 0.22, 0.15 * corrRightActivation, force, current);

        let strainSum = 0;
        let strainCount = 0;
        const _v1 = new BABYLON.Vector3();
        const _v2 = new BABYLON.Vector3();
        for (let i = 0; i < basePositions.length; i += 3) {
            const vx = current[i], vy = current[i + 1], vz = current[i + 2];
            if (isBoneLocked(vx, vy, vz)) {
                current[i] = basePositions[i];
                current[i + 1] = basePositions[i + 1];
                current[i + 2] = basePositions[i + 2];
                velocity[i] = velocity[i + 1] = velocity[i + 2] = 0;
                continue;
            }
            let mag = Math.sqrt(force[i] * force[i] + force[i + 1] * force[i + 1] + force[i + 2] * force[i + 2]);
            if (mag > 0.24) {
                const sc = 0.24 / mag;
                force[i] *= sc;
                force[i + 1] *= sc;
                force[i + 2] *= sc;
            }
            _v1.set(vx, vy, vz).normalize();
            _v2.set(force[i], force[i + 1], force[i + 2]);
            const dotFn = BABYLON.Vector3.Dot(_v2, _v1);
            _v2.subtractInPlace(_v1.scale(dotFn));
            const s = stiffness(vx, vy, vz);
            velocity[i] = velocity[i] * 0.9 + _v2.x * 0.08 * s;
            velocity[i + 1] = velocity[i + 1] * 0.9 + _v2.y * 0.08 * s;
            velocity[i + 2] = velocity[i + 2] * 0.9 + _v2.z * 0.08 * s;

            _v1.set(basePositions[i], basePositions[i + 1], basePositions[i + 2]).normalize();
            _v2.set(current[i], current[i + 1], current[i + 2]).normalize();
            const edgeBias = 1 - BABYLON.Vector3.Dot(_v1, _v2);
            velocity[i] -= edgeBias * 0.02 * _v1.x;
            velocity[i + 1] -= edgeBias * 0.02 * _v1.y;
            velocity[i + 2] -= edgeBias * 0.02 * _v1.z;

            const lock = planeLock(vx, vy, vz);
            if (lock) {
                velocity[i] += lock.x;
                velocity[i + 1] += lock.y;
                velocity[i + 2] += lock.z;
            }

            const vvx = velocity[i], vvy = velocity[i + 1], vvz = velocity[i + 2];
            const nc = vvx * _v1.x + vvy * _v1.y + vvz * _v1.z;
            velocity[i] = vvx - nc * _v1.x + nc * 0.4 * _v1.x;
            velocity[i + 1] = vvy - nc * _v1.y + nc * 0.4 * _v1.y;
            velocity[i + 2] = vvz - nc * _v1.z + nc * 0.4 * _v1.z;

            current[i] += velocity[i];
            current[i + 1] += velocity[i + 1];
            current[i + 2] += velocity[i + 2];

            const dx = current[i] - basePositions[i], dy = current[i + 1] - basePositions[i + 1], dz = current[i + 2] - basePositions[i + 2];
            const strain = Math.sqrt(dx * dx + dy * dy + dz * dz);
            strainSum += strain;
            strainCount++;
            const maxStrain = 0.28;
            if (strain > maxStrain) {
                const ratio = maxStrain / strain;
                current[i] = basePositions[i] + dx * ratio;
                current[i + 1] = basePositions[i + 1] + dy * ratio;
                current[i + 2] = basePositions[i + 2] + dz * ratio;
            }
        }
        avgStrain = strainCount > 0 ? strainSum / strainCount : 0;

        head.updateVerticesData(BABYLON.VertexBuffer.PositionKind, current);

        eyeYawTimer += 0.02;
        if (eyeYawTimer > 2 + Math.random() * 3) {
            eyeYawTarget = (Math.random() - 0.5) * 0.6;
            eyeYawTimer = 0;
        }
        eyeYawCurrent += (eyeYawTarget - eyeYawCurrent) * 0.08;
        const eyeYaw = s.eyeYaw !== undefined ? s.eyeYaw : eyeYawCurrent;
        leftEye.group.rotation.y = eyeYaw;
        rightEye.group.rotation.y = eyeYaw;

        const blink = orbLeftActivation > 0.1 ? orbLeftActivation : orbRightActivation;
        leftEye.upperLid.position.y = 0.058 - blink * 0.055;
        leftEye.upperLid.scaling.y = 0.42 - blink * 0.2;
        rightEye.upperLid.position.y = 0.058 - blink * 0.055;
        rightEye.upperLid.scaling.y = 0.42 - blink * 0.2;
        leftEye.lowerLid.position.y = -0.05 + blink * 0.03;
        rightEye.lowerLid.position.y = -0.05 + blink * 0.03;

        const jawOpen = s.jawOpen !== undefined ? s.jawOpen : (Math.sin(t * 0.8) * 0.2 + 0.08);
        jawPivot.rotation.x = 0.12 + jawOpen * 0.4 + zygAvg * 0.05;

        leftBrow.rotation.x = 0.02 - corrLeftActivation * 0.15 + zygLeftActivation * 0.06;
        rightBrow.rotation.x = 0.02 - corrRightActivation * 0.15 + zygRightActivation * 0.06;

        leftBrow.position.z = 0.42 - orbLeftActivation * 0.03;
        rightBrow.position.z = 0.42 - orbRightActivation * 0.03;

        noseGroup.scaling.x = 1 + (zygAvg * 0.03) + Math.sin(t * 1.5) * 0.015;
        tip.scaling.x = 0.85 + zygAvg * 0.08;
        alaL.scaling.y = 0.6 + zygAvg * 0.1;
        alaR.scaling.y = 0.6 + zygAvg * 0.1;

        cheekboneL.scaling.y = 0.95 + zygLeftActivation * 0.1;
        cheekboneR.scaling.y = 0.95 + zygRightActivation * 0.1;
        malarL.position.z = 0.33 + zygLeftActivation * 0.025;
        malarR.position.z = 0.33 + zygRightActivation * 0.025;
        browRidge.position.z = 0.35 - (corrLeftActivation + corrRightActivation) * 0.015;
        if (glabella) glabella.scaling.y = 1 + (corrLeftActivation + corrRightActivation) * 0.8;
        orbitRimL.position.z = 0.36 - orbLeftActivation * 0.015;
        orbitRimR.position.z = 0.36 - orbRightActivation * 0.015;
        if (crowsFeetL) { crowsFeetL.scaling.x = 0.6 + zygAvg * 0.8; crowsFeetR.scaling.x = 0.6 + zygAvg * 0.8; }
        if (frontalisLines) frontalisLines.scaling.y = 0.5 + (1 - corrLeftActivation - corrRightActivation) * 0.8;
        nasalRidge.scaling.x = 1 + zygAvg * 0.05;
        upperLip.position.z = 0.48 + zygAvg * 0.028;
        upperLip.scaling.y = 0.45 + zygAvg * 0.12;
        lowerLip.position.z = 0.475 + zygAvg * 0.02;
        lowerLip.position.y = -0.255 - jawOpen * 0.07;
        mouthCornerL.position.z = 0.46 + zygLeftActivation * 0.02;
        mouthCornerL.position.y = -0.22 + zygLeftActivation * 0.012;
        mouthCornerR.position.z = 0.46 + zygRightActivation * 0.02;
        mouthCornerR.position.y = -0.22 + zygRightActivation * 0.012;
        philtrum.position.z = 0.46 + zygAvg * 0.015;
        chinBoss.rotation.x = -0.15 - jawOpen * 0.35;
        jawAngleL.rotation.x = jawOpen * 0.2;
        jawAngleR.rotation.x = jawOpen * 0.2;
        tongue.position.z = 0.36 + jawOpen * 0.04;
        tongue.scaling.y = 0.35 + jawOpen * 0.05;
    });

    // Fit avatar to view after first frame (bounds computed)
    let _fitted = false;
    scene.onBeforeRenderObservable.addOnce(() => {
        if (_fitted) return;
        try {
            const b = face.getHierarchyBoundingVectors?.(true);
            if (b && b.min && b.max) {
                const center = BABYLON.Vector3.Center(b.min, b.max);
                const size = b.max.subtract(b.min);
                const maxDim = Math.max(size.x, size.y, size.z);
                const radius = Math.max(maxDim * 1.1 + 0.4, camera.lowerRadiusLimit);
                camera.setTarget(center);
                camera.radius = Math.min(Math.max(radius, camera.lowerRadiusLimit), camera.upperRadiusLimit);
            }
            _fitted = true;
        } catch (_) {}
    });

    window.setExpression = (opts = {}) => {
        if (!scene._faceState) return;
        if (opts.smile !== undefined) scene._faceState.smile = opts.smile;
        if (opts.blink !== undefined) scene._faceState.blink = opts.blink;
        if (opts.jawOpen !== undefined) scene._faceState.jawOpen = opts.jawOpen;
        if (opts.eyeYaw !== undefined) scene._faceState.eyeYaw = opts.eyeYaw;
        if (opts.frown !== undefined) scene._faceState.frown = opts.frown;
    };

    window.addEventListener('face:setExpression', (e) => {
        const opts = e.detail || {};
        if (opts && window.setExpression) window.setExpression(opts);
    });

    window.setPhysiology = (opts = {}) => {
        const p = scene._physiology;
        if (!p) return;
        if (opts.baselineTone !== undefined) p.baselineTone = opts.baselineTone;
        if (opts.arousal !== undefined) p.arousal = opts.arousal;
    };

    window.getActivation = () => ({ zygLeft: zygLeftActivation, zygRight: zygRightActivation, orbLeft: orbLeftActivation, orbRight: orbRightActivation });

    return scene;
}
