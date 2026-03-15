/**
 * WebXR/AR-VR init. Call window.enterARVR(scene) on user gesture.
 * Ensures scene renders correctly in XR (face, lights, camera).
 */
export async function initARVR() {
  window.enterARVR = async (scene) => {
    const s = scene || window.__babylonScene;
    if (!s?.createDefaultXRExperienceAsync) return;
    if (typeof navigator?.xr?.isSessionSupported !== 'function') return;

    let mode = null;
    try {
      if (await navigator.xr.isSessionSupported('immersive-ar')) mode = 'immersive-ar';
      else if (await navigator.xr.isSessionSupported('immersive-vr')) mode = 'immersive-vr';
    } catch (_) {
      return;
    }
    if (!mode) return;
    try {
      const xr = await s.createDefaultXRExperienceAsync({
        optionalFeatures: true,
        ignoreTrackedInput: true,
        disableTeleportation: true,
        useStablePlugins: true,
      });
      if (xr?.baseExperience?.camera) {
        xr.baseExperience.camera.minZ = 0.05;
        xr.baseExperience.camera.maxZ = 100;
      }
      s.autoClear = true;
      s.autoClearDepthAndStencil = true;
    } catch (e) {
      console.warn('WebXR init failed:', e);
    }
  };
}
