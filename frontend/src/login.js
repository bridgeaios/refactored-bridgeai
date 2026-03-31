/**
 * BRIDGE AI OS — Immersive 3D Login
 * Babylon.js nebula scene + Clerk authentication
 */

// ─── CSS Particle System ───────────────────────────────────────────
function spawnParticles() {
  const container = document.getElementById('particles');
  if (!container) return;
  const COLORS = ['#63ffda', '#38bdf8', '#a78bfa', '#f472b6'];
  for (let i = 0; i < 50; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    p.style.left = Math.random() * 100 + '%';
    p.style.width = p.style.height = (1 + Math.random() * 3) + 'px';
    p.style.background = COLORS[Math.floor(Math.random() * COLORS.length)];
    p.style.animationDuration = (6 + Math.random() * 12) + 's';
    p.style.animationDelay = (Math.random() * 10) + 's';
    container.appendChild(p);
  }
}

// ─── 3D Card Tilt (mouse parallax) ────────────────────────────────
function initCardTilt() {
  const card = document.getElementById('loginCard');
  if (!card) return;

  document.addEventListener('mousemove', (e) => {
    const cx = window.innerWidth / 2;
    const cy = window.innerHeight / 2;
    const dx = (e.clientX - cx) / cx;
    const dy = (e.clientY - cy) / cy;
    const rotateY = dx * 6;   // max 6deg horizontal
    const rotateX = -dy * 4;  // max 4deg vertical
    card.style.transform = `rotateY(${rotateY}deg) rotateX(${rotateX}deg)`;
  });

  document.addEventListener('mouseleave', () => {
    card.style.transform = 'rotateY(0) rotateX(0)';
  });
}

// ─── Babylon.js 3D Nebula Scene ───────────────────────────────────
function initScene() {
  const canvas = document.getElementById('renderCanvas');
  if (!canvas || typeof BABYLON === 'undefined') return;

  // Skip heavy 3D scene for users who prefer reduced motion
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  const engine = new BABYLON.Engine(canvas, true, {
    preserveDrawingBuffer: false,
    stencil: false,
    antialias: true,
    powerPreference: 'low-power',
  });

  const scene = new BABYLON.Scene(engine);
  scene.clearColor = new BABYLON.Color4(0.024, 0.031, 0.063, 1); // #060810

  // Camera — slow orbit
  const camera = new BABYLON.ArcRotateCamera('cam', 0, Math.PI / 2.5, 20, BABYLON.Vector3.Zero(), scene);
  camera.lowerRadiusLimit = 18;
  camera.upperRadiusLimit = 22;
  camera.fov = 0.8;

  // ── Nebula particle system ──
  const emitter = new BABYLON.TransformNode('emitter', scene);
  const nebula = new BABYLON.ParticleSystem('nebula', 1200, scene);
  // Use a procedural texture for particles (avoids WebGL texImage2D warnings)
  const particleTex = new BABYLON.DynamicTexture('particleTex', 32, scene, false);
  const ctx = particleTex.getContext();
  const grad = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.4, 'rgba(255,255,255,0.6)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 32, 32);
  particleTex.update();
  nebula.particleTexture = particleTex;
  nebula.emitter = emitter;

  // Shape — sphere volume
  nebula.createSphereEmitter(12);

  // Particle props
  nebula.minLifeTime = 4;
  nebula.maxLifeTime = 8;
  nebula.minSize = 0.05;
  nebula.maxSize = 0.25;
  nebula.emitRate = 150;
  nebula.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;

  // Colors: cyan → blue → purple fade
  nebula.color1 = new BABYLON.Color4(0.39, 1, 0.85, 0.15);       // cyan
  nebula.color2 = new BABYLON.Color4(0.22, 0.74, 0.97, 0.1);     // blue
  nebula.colorDead = new BABYLON.Color4(0.65, 0.55, 0.98, 0);     // purple fade

  nebula.minEmitPower = 0.02;
  nebula.maxEmitPower = 0.08;
  nebula.updateSpeed = 0.008;

  nebula.start();

  // ── Floating wireframe shapes ──
  const shapes = [];
  const meshConfigs = [
    { type: 'icosphere', opts: { radius: 1.2, subdivisions: 1 }, pos: [-6, 2, -3] },
    { type: 'torus', opts: { diameter: 2, thickness: 0.15, tessellation: 24 }, pos: [5, -1, -4] },
    { type: 'box', opts: { size: 1.5 }, pos: [-4, -3, 2] },
    { type: 'torus', opts: { diameter: 1.5, thickness: 0.1, tessellation: 32 }, pos: [6, 3, 1] },
    { type: 'icosphere', opts: { radius: 0.8, subdivisions: 2 }, pos: [3, 4, -5] },
    { type: 'box', opts: { size: 1 }, pos: [-5, 0, 5] },
  ];

  meshConfigs.forEach((cfg, i) => {
    let mesh;
    if (cfg.type === 'icosphere') {
      mesh = BABYLON.MeshBuilder.CreateIcoSphere('shape' + i, cfg.opts, scene);
    } else if (cfg.type === 'torus') {
      mesh = BABYLON.MeshBuilder.CreateTorus('shape' + i, cfg.opts, scene);
    } else {
      mesh = BABYLON.MeshBuilder.CreateBox('shape' + i, cfg.opts, scene);
    }

    const mat = new BABYLON.StandardMaterial('mat' + i, scene);
    mat.wireframe = true;
    mat.emissiveColor = new BABYLON.Color3(0.39, 1, 0.85).scale(0.25 + Math.random() * 0.15);
    mat.disableLighting = true;
    mat.alpha = 0.15 + Math.random() * 0.15;
    mesh.material = mat;

    mesh.position = new BABYLON.Vector3(...cfg.pos);
    mesh.rotation = new BABYLON.Vector3(Math.random() * Math.PI, Math.random() * Math.PI, 0);

    shapes.push({
      mesh,
      speedY: 0.002 + Math.random() * 0.005,
      speedX: 0.001 + Math.random() * 0.003,
      bobSpeed: 0.3 + Math.random() * 0.5,
      bobAmp: 0.3 + Math.random() * 0.5,
      baseY: cfg.pos[1],
    });
  });

  // ── Central energy ring ──
  const centralRing = BABYLON.MeshBuilder.CreateTorus('centralRing', {
    diameter: 4, thickness: 0.05, tessellation: 64,
  }, scene);
  const ringMat = new BABYLON.StandardMaterial('ringMat', scene);
  ringMat.emissiveColor = new BABYLON.Color3(0.39, 1, 0.85);
  ringMat.disableLighting = true;
  ringMat.alpha = 0.2;
  ringMat.wireframe = false;
  centralRing.material = ringMat;

  const centralRing2 = BABYLON.MeshBuilder.CreateTorus('centralRing2', {
    diameter: 5, thickness: 0.03, tessellation: 64,
  }, scene);
  const ringMat2 = new BABYLON.StandardMaterial('ringMat2', scene);
  ringMat2.emissiveColor = new BABYLON.Color3(0.65, 0.55, 0.98);
  ringMat2.disableLighting = true;
  ringMat2.alpha = 0.12;
  centralRing2.material = ringMat2;

  // ── Glow layer ──
  const glow = new BABYLON.GlowLayer('glow', scene, { blurKernelSize: 64 });
  glow.intensity = 0.4;

  // ── Render loop ──
  let t = 0;
  engine.runRenderLoop(() => {
    t += engine.getDeltaTime() * 0.001;

    // Slowly rotate camera
    camera.alpha += 0.0008;

    // Animate shapes
    shapes.forEach(s => {
      s.mesh.rotation.y += s.speedY;
      s.mesh.rotation.x += s.speedX;
      s.mesh.position.y = s.baseY + Math.sin(t * s.bobSpeed) * s.bobAmp;
    });

    // Rotate central rings
    centralRing.rotation.y += 0.003;
    centralRing.rotation.x = Math.sin(t * 0.5) * 0.3;
    centralRing2.rotation.y -= 0.002;
    centralRing2.rotation.z = Math.cos(t * 0.3) * 0.4;

    // Pulse ring alpha
    ringMat.alpha = 0.15 + Math.sin(t * 1.5) * 0.08;
    ringMat2.alpha = 0.08 + Math.cos(t * 1.2) * 0.06;

    scene.render();
  });

  window.addEventListener('resize', () => engine.resize());
}

// ─── Clerk Authentication ─────────────────────────────────────────
async function initClerk() {
  const mountEl = document.getElementById('clerk-auth');
  const fallbackEl = document.getElementById('fallbackForm');

  try {
    // Read Clerk publishable key from env or window config
    const publishableKey =
      (typeof import.meta !== 'undefined' && import.meta.env?.VITE_CLERK_PUBLISHABLE_KEY) ||
      (typeof window !== 'undefined' && window.__CLERK_PK) ||
      '';

    if (!publishableKey) {
      throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY');
    }

    // Load Clerk from their official CDN with the publishable key
    const clerk = await new Promise((resolve, reject) => {
      // If already loaded by a previous attempt
      if (window.Clerk && window.Clerk.isReady?.()) {
        return resolve(window.Clerk);
      }
      const s = document.createElement('script');
      s.setAttribute('data-clerk-publishable-key', publishableKey);
      s.async = true;
      // Decode the frontend API from the publishable key (base64 after last _)
      const encoded = publishableKey.split('_').pop();
      const frontendApi = atob(encoded.replace(/\$$/,'')).replace(/\$$/,'');
      s.src = `https://${frontendApi}/npm/@clerk/clerk-js@6.3.3/dist/clerk.browser.js`;
      s.crossOrigin = 'anonymous';
      s.addEventListener('load', () => {
        // Wait for Clerk to self-initialize
        const poll = setInterval(() => {
          if (window.Clerk && typeof window.Clerk.load === 'function') {
            clearInterval(poll);
            resolve(window.Clerk);
          }
        }, 50);
        setTimeout(() => { clearInterval(poll); reject(new Error('Clerk init timeout')); }, 10000);
      });
      s.onerror = () => reject(new Error('Failed to load Clerk script'));
      document.head.appendChild(s);
    });
    await clerk.load({
      appearance: {
        variables: {
          colorPrimary: '#63ffda',
          colorText: '#e2e8f0',
          colorTextSecondary: '#94a3b8',
          colorBackground: 'transparent',
          colorInputBackground: 'rgba(255,255,255,0.04)',
          colorInputText: '#e2e8f0',
          borderRadius: '12px',
          fontFamily: "'Outfit', sans-serif",
        },
        elements: {
          rootBox: { width: '100%' },
          card: {
            background: 'transparent',
            boxShadow: 'none',
            border: 'none',
            padding: '0',
          },
        },
      },
    });

    // If already signed in, redirect to main app
    if (clerk.user) {
      window.location.href = '/';
      return;
    }

    // Mount sign-in component
    mountEl.innerHTML = '';
    clerk.mountSignIn(mountEl, {
      afterSignInUrl: '/',
      afterSignUpUrl: '/',
      signUpUrl: '/login.html#signup',
    });

  } catch (err) {
    console.warn('[BridgeAI] Clerk init failed, using fallback form:', err.message);
    mountEl.style.display = 'none';
    fallbackEl.classList.add('active');
    initFallbackForm();
  }
}

// ─── CSRF Token Management ────────────────────────────────────────
let currentCSRFToken = '';

async function initCSRFToken() {
  // Initialize CSRF token by making a safe OPTIONS request
  // CSRFMiddleware generates and sends token in X-CSRF-Token header
  try {
    const res = await fetch('/api/auth/login', {
      method: 'OPTIONS',
      credentials: 'include',
    });
    // Extract token from response header
    currentCSRFToken = res.headers.get('X-CSRF-Token') || '';
  } catch (err) {
    console.warn('CSRF token initialization failed:', err);
  }
}

// ─── Fallback form (when Clerk key is missing / offline) ──────────
function initFallbackForm() {
  const btn = document.getElementById('loginBtn');
  const emailInput = document.getElementById('email');
  const passInput = document.getElementById('password');

  if (!btn) return;

  // Initialize CSRF token on form load
  initCSRFToken();

  btn.addEventListener('click', async () => {
    const email = emailInput?.value?.trim();
    const password = passInput?.value;

    if (!email || !password) {
      shakeCard();
      return;
    }

    // Ensure CSRF token is initialized
    if (!currentCSRFToken) {
      await initCSRFToken();
    }

    btn.textContent = 'Authenticating...';
    btn.disabled = true;

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': currentCSRFToken,
        },
        body: JSON.stringify({ email, password }),
        credentials: 'include',  // Send/receive cookies
      });

      if (!res.ok) throw new Error('Auth failed');

      // Server sets httpOnly secure cookie on response
      // No need to manually store token — browser handles it automatically
      // Success animation
      const card = document.getElementById('loginCard');
      if (card) {
        card.style.transition = 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
        card.style.transform = 'scale(0.95) translateY(-20px)';
        card.style.opacity = '0';
      }
      setTimeout(() => { window.location.href = '/'; }, 600);

    } catch (err) {
      btn.textContent = 'Enter The System';
      btn.disabled = false;
      shakeCard();
    }
  });

  // Enter key submits
  [emailInput, passInput].forEach(input => {
    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') btn.click();
    });
  });
}

function shakeCard() {
  const card = document.getElementById('loginCard');
  if (!card) return;
  card.style.animation = 'none';
  card.offsetHeight; // force reflow
  card.style.animation = 'shake 0.5s ease';
  setTimeout(() => { card.style.animation = ''; }, 500);

  // Add shake keyframes dynamically
  if (!document.getElementById('shakeStyle')) {
    const style = document.createElement('style');
    style.id = 'shakeStyle';
    style.textContent = `
      @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 50%, 90% { transform: translateX(-6px); }
        30%, 70% { transform: translateX(6px); }
      }
    `;
    document.head.appendChild(style);
  }
}

// ─── Init Everything ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  spawnParticles();
  initCardTilt();
  initScene();
  initClerk();
});
