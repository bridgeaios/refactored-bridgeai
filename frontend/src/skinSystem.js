/**
 * High-Fidelity MetaHuman Skin System — BRIDGE AI OS Digital Twin
 * Surface fidelity, SSS, anatomical anchoring, imperfection layer, dynamic response.
 * Rejects: over-smoothing, uniform repetition, plastic specular, flat albedo.
 */

const SKIN_TEX_SIZE = (typeof window !== 'undefined' && window.__BRIDGE_HIGH_FIDELITY_SKIN) ? 2048 : 1024;

/** Seeded pseudo-random for reproducible variation */
function seeded(seed) {
  return () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
}

/**
 * Generate high-fidelity skin albedo with:
 * - Micro color variation (reds, blues, yellows in dermal layers)
 * - Asymmetrical pore density
 * - Minor pigmentation variation
 * - Micro freckles / capillary breakup
 * - T-zone oil sheen (subtle)
 * - Randomized micro scars
 */
export function createSkinAlbedoTexture(scene, size = SKIN_TEX_SIZE) {
  const tex = new BABYLON.DynamicTexture("skinAlbedo", size, scene, false);
  const ctx = tex.getContext();
  const imgData = ctx.createImageData(size, size);
  const data = imgData.data;

  const rng = seeded(12345);
  const baseR = 245; const baseG = 184; const baseB = 153;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (y * size + x) * 4;
      const nx = x / size; const ny = y / size;

      let r = baseR; let g = baseG; let b = baseB;

      // Pores — asymmetrical density (more on nose/cheeks)
      const poreBias = 0.3 + 0.4 * Math.sin(nx * 12) * Math.cos(ny * 8);
      for (let i = 0; i < 12; i++) {
        const px = (Math.sin(nx * 47 + i * 1.7) * 0.5 + 0.5) * size;
        const py = (Math.cos(ny * 31 + i * 2.1) * 0.5 + 0.5) * size;
        const d = Math.hypot(x - px, y - py);
        if (d < 1.2 + poreBias) {
          r -= 12; g -= 8; b -= 7;
        }
      }

      // Micro color variation — dermal reds, blues, yellows
      const redShift = (rng() - 0.5) * 18;
      const blueShift = (rng() - 0.5) * 10;
      const yellowShift = (rng() - 0.5) * 8;
      r = r + redShift + yellowShift * 0.5;
      g = g - blueShift * 0.3 + yellowShift;
      b = b + blueShift;

      // Pigmentation variation (subtle)
      const pigment = Math.sin(nx * 23) * Math.cos(ny * 19) * 6;
      r += pigment; g += pigment * 0.7; b += pigment * 0.5;

      // Micro freckles (sparse)
      if (rng() > 0.985) {
        r -= 15; g -= 10; b -= 8;
      }

      // T-zone oil sheen (center-upper) — slight yellow warmth
      const tZone = Math.exp(-((nx - 0.5) ** 2 + (ny - 0.35) ** 2) * 8);
      r += tZone * 4; g += tZone * 3; b -= tZone * 2;

      r = Math.max(200, Math.min(255, r));
      g = Math.max(155, Math.min(210, g));
      b = Math.max(125, Math.min(185, b));
      data[idx] = r;
      data[idx + 1] = g;
      data[idx + 2] = b;
      data[idx + 3] = 255;
    }
  }

  // Second pass: micro scars (sparse, irregular)
  const scarRng = seeded(99999);
  for (let i = 0; i < size * size * 0.0008; i++) {
    if (scarRng() > 0.7) continue;
    const x = Math.floor(scarRng() * size);
    const y = Math.floor(scarRng() * size);
    const len = 2 + Math.floor(scarRng() * 4);
    for (let s = 0; s < len; s++) {
      const sx = Math.max(0, Math.min(size - 1, x + Math.floor((scarRng() - 0.5) * 4)));
      const sy = Math.max(0, Math.min(size - 1, y + Math.floor((scarRng() - 0.5) * 4)));
      const si = (sy * size + sx) * 4;
      data[si] = Math.max(0, data[si] - 8);
      data[si + 1] = Math.max(0, data[si + 1] - 6);
      data[si + 2] = Math.max(0, data[si + 2] - 5);
    }
  }

  ctx.putImageData(imgData, 0, 0);
  tex.update();
  return tex;
}

/**
 * Generate micro-normal map for pores and fine detail.
 */
export function createSkinNormalTexture(scene, size = Math.min(1024, SKIN_TEX_SIZE)) {
  const tex = new BABYLON.DynamicTexture("skinNormal", size, scene, false);
  const ctx = tex.getContext();
  const imgData = ctx.createImageData(size, size);
  const data = imgData.data;
  const rng = seeded(67890);

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (y * size + x) * 4;
      let nx = 0.5; let ny = 0.5; let nz = 1;

      // Pore depressions
      for (let i = 0; i < 8; i++) {
        const px = (Math.sin((x / size) * 47 + i) * 0.5 + 0.5) * size;
        const py = (Math.cos((y / size) * 31 + i * 1.3) * 0.5 + 0.5) * size;
        const d = Math.hypot(x - px, y - py);
        if (d < 1.5) {
          const n = 1 - d / 1.5;
          nx += (x - px) / size * n * 0.15;
          ny += (y - py) / size * n * 0.15;
          nz -= n * 0.08;
        }
      }

      // Fine wrinkle micro-normals
      const wrinkle = Math.sin((x / size) * 80) * Math.cos((y / size) * 60) * 0.03;
      nx += wrinkle; ny += wrinkle * 0.7;

      const len = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
      nx /= len; ny /= len; nz /= len;
      data[idx] = Math.floor((nx * 0.5 + 0.5) * 255);
      data[idx + 1] = Math.floor((ny * 0.5 + 0.5) * 255);
      data[idx + 2] = Math.floor((nz * 0.5 + 0.5) * 255);
      data[idx + 3] = 255;
    }
  }
  ctx.putImageData(imgData, 0, 0);
  tex.update();
  return tex;
}

/**
 * Roughness map — high-frequency variation, no uniform flat.
 */
export function createSkinRoughnessTexture(scene, size = Math.min(1024, SKIN_TEX_SIZE)) {
  const tex = new BABYLON.DynamicTexture("skinRoughness", size, scene, false);
  const ctx = tex.getContext();
  const imgData = ctx.createImageData(size, size);
  const data = imgData.data;
  const rng = seeded(11111);

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (y * size + x) * 4;
      let rough = 0.42;
      rough += (rng() - 0.5) * 0.12;
      rough += Math.sin((x / size) * 90) * Math.cos((y / size) * 70) * 0.06;
      rough = Math.max(0.25, Math.min(0.65, rough));
      const v = Math.floor(rough * 255);
      data[idx] = data[idx + 1] = data[idx + 2] = v;
      data[idx + 3] = 255;
    }
  }
  ctx.putImageData(imgData, 0, 0);
  tex.update();
  return tex;
}

/**
 * Create high-fidelity PBR skin material with SSS.
 * Physically accurate diffusion, epidermal/dermal, no plastic/wax.
 */
export function createHighFidelitySkinMaterial(scene, options = {}) {
  const albedoSize = options.albedoSize ?? SKIN_TEX_SIZE;
  const mat = new BABYLON.PBRMaterial("metaHumanSkin", scene);

  mat.albedoColor = new BABYLON.Color3(0.96, 0.72, 0.6);
  mat.roughness = 0.42;
  mat.metallic = 0;
  mat.ambientColor = new BABYLON.Color3(0.42, 0.3, 0.26);
  mat.environmentIntensity = 1.15;

  // Subsurface Scattering — physically plausible
  mat.subSurface.isTranslucencyEnabled = true;
  mat.subSurface.translucencyIntensity = 0.45;
  mat.subSurface.translucencyDiffusionDistance = 0.08;
  mat.subSurface.tintColor = new BABYLON.Color3(0.92, 0.55, 0.48);
  mat.subSurface.minimumThickness = 0.08;
  mat.subSurface.maximumThickness = 0.55;
  mat.subSurface.useThicknessFromDepth = true;

  // No plastic specular — reduce environment, avoid blown highlights
  mat.environmentIntensity = 1.0;
  mat.specularIntensity = 0.15;
  mat.metallicF0Factor = 0.04;

  mat.albedoTexture = createSkinAlbedoTexture(scene, albedoSize);
  mat.albedoTexture.uScale = mat.albedoTexture.vScale = 2;
  mat.normalTexture = createSkinNormalTexture(scene, Math.min(1024, albedoSize));
  mat.normalTexture.uScale = mat.normalTexture.vScale = 2;
  mat.roughnessTexture = createSkinRoughnessTexture(scene, Math.min(1024, albedoSize));
  mat.roughnessTexture.uScale = mat.roughnessTexture.vScale = 2;

  return mat;
}

/**
 * 3-point cinematic lighting for validation.
 */
export function setupCinematicLighting(scene) {
  const dir1 = new BABYLON.DirectionalLight("key", new BABYLON.Vector3(-1, -0.5, -0.8), scene);
  dir1.intensity = 1.6;
  dir1.position = new BABYLON.Vector3(3, 5, 3);
  dir1.diffuse = new BABYLON.Color3(1, 0.98, 0.96);

  const dir2 = new BABYLON.DirectionalLight("fill", new BABYLON.Vector3(0.6, -0.3, -0.4), scene);
  dir2.intensity = 0.6;
  dir2.position = new BABYLON.Vector3(-2.5, 3, 2);
  dir2.diffuse = new BABYLON.Color3(0.9, 0.92, 1);

  const dir3 = new BABYLON.DirectionalLight("rim", new BABYLON.Vector3(0.5, -0.2, -1), scene);
  dir3.intensity = 0.4;
  dir3.position = new BABYLON.Vector3(0, 2, -1);
  dir3.diffuse = new BABYLON.Color3(0.95, 0.95, 1);

  return { key: dir1, fill: dir2, rim: dir3 };
}
