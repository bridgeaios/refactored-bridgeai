/**
 * BRIDGE AI OS — Detailed Human Eye Materials
 * Sclera (veins, color variation), limbus, iris (stroma, collarette, crypts), pupil, cornea.
 */

const SCLERA_SIZE = 256;
const IRIS_SIZE = 256;

function seeded(seed) {
  return () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
}

/** Sclera albedo — subtle veins, slight pink/blue tint variation */
export function createScleraTexture(scene) {
  const tex = new BABYLON.DynamicTexture("scleraAlbedo", SCLERA_SIZE, scene, false);
  const ctx = tex.getContext();
  const img = ctx.createImageData(SCLERA_SIZE, SCLERA_SIZE);
  const d = img.data;
  const rng = seeded(12345);

  const baseR = 248, baseG = 242, baseB = 238;

  for (let y = 0; y < SCLERA_SIZE; y++) {
    for (let x = 0; x < SCLERA_SIZE; x++) {
      const i = (y * SCLERA_SIZE + x) * 4;
      const nx = x / SCLERA_SIZE, ny = y / SCLERA_SIZE;

      let r = baseR, g = baseG, b = baseB;

      // Subtle veins (branching, reddish)
      for (let v = 0; v < 8; v++) {
        const vx = (Math.sin(nx * 31 + v * 7) * 0.5 + 0.5) * SCLERA_SIZE;
        const vy = (Math.cos(ny * 23 + v * 5) * 0.5 + 0.5) * SCLERA_SIZE;
        const dist = Math.hypot(x - vx, y - vy);
        if (dist < 2 + rng() * 3) {
          r -= 18; g -= 22; b -= 20;
        }
      }

      // Micro color variation
      const noise = (rng() - 0.5) * 12;
      r += noise; g += noise * 0.9; b += noise * 1.1;

      // Slight pink tint near inner canthus
      const innerBias = Math.exp(-((nx - 0.5) ** 2 + (ny - 0.5) ** 2) * 2);
      r += innerBias * 4; g -= innerBias * 2; b -= innerBias * 3;

      d[i] = Math.max(220, Math.min(255, r));
      d[i + 1] = Math.max(218, Math.min(250, g));
      d[i + 2] = Math.max(210, Math.min(248, b));
      d[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  tex.update();
  return tex;
}

/** Iris albedo — radial stroma, collarette, crypts, color variation (blue/green/brown) */
export function createIrisTexture(scene, color = "blue") {
  const tex = new BABYLON.DynamicTexture("irisAlbedo", IRIS_SIZE, scene, false);
  const ctx = tex.getContext();
  const img = ctx.createImageData(IRIS_SIZE, IRIS_SIZE);
  const d = img.data;
  const rng = seeded(67890);

  const centerX = IRIS_SIZE / 2, centerY = IRIS_SIZE / 2;
  const irisRadius = IRIS_SIZE * 0.45;
  const pupilRadius = IRIS_SIZE * 0.18;
  const collaretteRadius = IRIS_SIZE * 0.32;

  const colorMap = {
    blue: { base: [0.18, 0.38, 0.65], outer: [0.12, 0.28, 0.55], crypt: [0.25, 0.45, 0.72] },
    green: { base: [0.22, 0.48, 0.35], outer: [0.15, 0.38, 0.28], crypt: [0.28, 0.55, 0.42] },
    brown: { base: [0.45, 0.32, 0.22], outer: [0.35, 0.24, 0.15], crypt: [0.52, 0.38, 0.28] },
  };
  const c = colorMap[color] || colorMap.blue;

  for (let y = 0; y < IRIS_SIZE; y++) {
    for (let x = 0; x < IRIS_SIZE; x++) {
      const i = (y * IRIS_SIZE + x) * 4;
      const dx = x - centerX, dy = y - centerY;
      const r = Math.hypot(dx, dy);
      const theta = Math.atan2(dy, dx);

      if (r < pupilRadius) {
        d[i] = 4; d[i + 1] = 4; d[i + 2] = 6; d[i + 3] = 255;
        continue;
      }
      if (r > irisRadius) {
        const edge = (r - irisRadius) / (IRIS_SIZE / 2 - irisRadius);
        const blend = Math.max(0, 1 - edge * 2);
        d[i] = Math.floor(220 + blend * 35);
        d[i + 1] = Math.floor(218 + blend * 37);
        d[i + 2] = Math.floor(228 + blend * 27);
        d[i + 3] = 255;
        continue;
      }

      const t = (r - pupilRadius) / (irisRadius - pupilRadius);
      const radial = Math.sin(theta * 24 + r * 0.15) * 0.5 + 0.5;
      const stroma = Math.sin(theta * 36 + r * 0.2) * 0.3 + 0.7;

      let fr = c.base[0], fg = c.base[1], fb = c.base[2];
      fr = fr + (c.outer[0] - c.base[0]) * t;
      fg = fg + (c.outer[1] - c.base[1]) * t;
      fb = fb + (c.outer[2] - c.base[2]) * t;

      fr += radial * 0.08 + stroma * 0.05;
      fg += radial * 0.06 + stroma * 0.04;
      fb += radial * 0.1 + stroma * 0.06;

      if (r < collaretteRadius && r > pupilRadius * 1.3) {
        const coll = Math.sin(theta * 48) * 0.5 + 0.5;
        fr += coll * 0.06; fg += coll * 0.05; fb += coll * 0.08;
      }

      if (rng() > 0.92) {
        fr = c.crypt[0]; fg = c.crypt[1]; fb = c.crypt[2];
      }

      d[i] = Math.floor(Math.max(0, Math.min(255, fr * 255)));
      d[i + 1] = Math.floor(Math.max(0, Math.min(255, fg * 255)));
      d[i + 2] = Math.floor(Math.max(0, Math.min(255, fb * 255)));
      d[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  tex.update();
  return tex;
}

/** Limbus texture — dark ring at corneoscleral junction */
export function createLimbusTexture(scene) {
  const tex = new BABYLON.DynamicTexture("limbus", 128, scene, false);
  const ctx = tex.getContext();
  const img = ctx.createImageData(128, 128);
  const d = img.data;
  const cx = 64, cy = 64;

  for (let y = 0; y < 128; y++) {
    for (let x = 0; x < 128; x++) {
      const i = (y * 128 + x) * 4;
      const r = Math.hypot(x - cx, y - cy);
      const t = r / 64;
      const ring = Math.exp(-((t - 0.85) ** 2) * 80) * 0.6;
      const v = Math.floor(255 - ring * 180);
      d[i] = d[i + 1] = d[i + 2] = Math.max(200, Math.min(255, v));
      d[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  tex.update();
  return tex;
}

/** Create detailed eye materials */
export function createDetailedEyeMaterials(scene, irisColor = "blue") {
  const scleraMat = new BABYLON.PBRMaterial("scleraDetailed", scene);
  scleraMat.albedoTexture = createScleraTexture(scene);
  scleraMat.albedoTexture.uScale = scleraMat.albedoTexture.vScale = 1.5;
  scleraMat.albedoColor = new BABYLON.Color3(0.98, 0.96, 0.94);
  scleraMat.roughness = 0.35;
  scleraMat.metallic = 0;
  scleraMat.subSurface.isTranslucencyEnabled = true;
  scleraMat.subSurface.translucencyIntensity = 0.2;
  scleraMat.subSurface.tintColor = new BABYLON.Color3(0.95, 0.75, 0.7);
  scleraMat.ambientColor = new BABYLON.Color3(0.4, 0.35, 0.38);

  const irisMat = new BABYLON.PBRMaterial("irisDetailed", scene);
  irisMat.albedoTexture = createIrisTexture(scene, irisColor);
  irisMat.albedoTexture.uScale = irisMat.albedoTexture.vScale = 1;
  irisMat.roughness = 0.25;
  irisMat.metallic = 0;
  irisMat.ambientColor = new BABYLON.Color3(0.3, 0.28, 0.35);
  irisMat.emissiveColor = new BABYLON.Color3(0.02, 0.02, 0.03);

  const pupilMat = new BABYLON.PBRMaterial("pupilDetailed", scene);
  pupilMat.albedoColor = new BABYLON.Color3(0.008, 0.008, 0.012);
  pupilMat.roughness = 0.1;
  pupilMat.metallic = 0;
  pupilMat.ambientColor = new BABYLON.Color3(0.01, 0.01, 0.02);

  const limbusMat = new BABYLON.PBRMaterial("limbus", scene);
  limbusMat.albedoTexture = createLimbusTexture(scene);
  limbusMat.roughness = 0.3;
  limbusMat.metallic = 0;

  const corneaMat = new BABYLON.PBRMaterial("corneaDetailed", scene);
  corneaMat.albedoColor = new BABYLON.Color3(0.99, 0.99, 1);
  corneaMat.roughness = 0.03;
  corneaMat.metallic = 0;
  corneaMat.subSurface.isTranslucencyEnabled = true;
  corneaMat.subSurface.translucencyIntensity = 0.35;
  corneaMat.subSurface.tintColor = new BABYLON.Color3(0.9, 0.92, 1);
  corneaMat.environmentIntensity = 1.5;
  corneaMat.specularIntensity = 0.4;

  return { scleraMat, irisMat, pupilMat, limbusMat, corneaMat };
}
