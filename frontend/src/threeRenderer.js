export async function initThreeRenderer(container) {
    // Placeholder Three.js renderer fallback. Loads model and returns simple scene object.
    try {
        const scene = { threeFallback: true };
        console.log('Three.js fallback initialized');
        return scene;
    } catch (e) {
        console.error('Three renderer failed', e);
        return null;
    }
}
