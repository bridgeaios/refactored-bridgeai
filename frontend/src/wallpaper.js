export function startWallpaperMode(renderer){
  // remove UI chrome
  document.body.requestFullscreen?.();
  const el = document.querySelector('#ui'); if(el) el.style.display='none';
  const fpsCap = 60; let last = performance.now();
  function loop(now){
    const dt = now - last;
    if(dt >= (1000/fpsCap)){
      last = now;
      // renderer.tick handled by engine run loop
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
}
