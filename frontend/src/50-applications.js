/**
 * 50 Applications — Bridge AI OS. Renders nav, hero, features, category filter, cards, TAM, top 5, wins, CTAs.
 * Tooltip note: any capability display must use (capabilityNames[key] || key) for correct operator precedence.
 */

import './50-applications.css';
import {
  CATEGORIES,
  APPLICATIONS,
  TOP_FIVE,
  TAM_DESCRIPTION,
  BRIDGE_WINS_PILLARS,
  SOURCES,
} from './applicationsData.js';

const appEl = document.getElementById('app');
if (!appEl) throw new Error('#app not found');

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

const FEATURES = [
  { title: 'AI Agents & Digital Twins', desc: 'Coordinate agents, workflows, and digital twin evolution.', icon: true },
  { title: 'Real-Time Data Ingestion', desc: 'Live data from IoT sensors and networks into intelligent replicas.', icon: true },
  { title: 'Decentralized Task Marketplace', desc: 'Enable a decentralized AI economy and task allocation.', icon: true },
  { title: 'Secure Wallet Authentication', desc: 'SIWE and wallet-based identity for secure participation.', icon: true },
];

function renderNav(baseUrl) {
  return `
    <nav class="app-nav">
      <a href="${baseUrl}" class="app-nav-logo">
        <span class="app-nav-logo-icon"></span>
        Bridge AI OS
      </a>
      <div class="app-nav-links">
        <a href="/">Digital Twin</a>
        <a href="#platform">Platform</a>
        <a href="#app-content">Use Cases</a>
        <a href="#wins">Technology</a>
        <a href="#top5">Resources</a>
        <a href="/executive-dashboard.html">Dashboard</a>
        <a href="/agents.html">Agents</a>
        <a href="/settings.html">Settings</a>
        <a href="/docs.html">Docs</a>
        <a href="/landing.html">Landing</a>
        <a href="/gateway/">Gateway</a>
        <a href="/join.html">Join as Agent</a>
        <a href="/" class="btn-primary">Get Started</a>
      </div>
    </nav>
  `;
}

function renderHero(baseUrl) {
  return `
    <header class="app-hero">
      <div class="app-hero-inner">
        <span class="app-realtime-badge">Live</span>
        <h1>Orchestrating the Future of AI</h1>
        <p class="subtitle">Decentralized AI Operating System for Digital Twins and Autonomous Agents. Explore 50 real-world applications with market value and deployment strategy.</p>
        <div class="app-hero-actions">
          <a href="${baseUrl}" class="btn-primary" data-action="get-started">Get Started</a>
          <a href="#top5" class="btn-secondary" data-action="learn-more">Learn More</a>
        </div>
        <a class="nav-link" href="/">← Back to Digital Twin</a>
      </div>
    </header>
  `;
}

function renderFeatures() {
  return `
    <section class="app-features" id="platform">
      ${FEATURES.map(
        (f) => `
        <div class="app-features-card">
          <div class="app-features-icon"></div>
          <h3>${escapeHtml(f.title)}</h3>
          <p>${escapeHtml(f.desc)}</p>
        </div>
      `
      ).join('')}
    </section>
  `;
}

function renderFilter(activeCategory) {
  const allClass = !activeCategory ? ' active' : '';
  const buttons = CATEGORIES.map(
    (c) => `<button type="button" data-category="${c.id}" class="${activeCategory === c.id ? 'active' : ''}">${escapeHtml(c.title)} (${escapeHtml(c.range)})</button>`
  ).join('');
  return `
    <div class="app-filter" id="app-filter">
      <span class="app-filter-label">Use cases</span>
      <button type="button" data-category="" class="${allClass}">All</button>
      ${buttons}
    </div>
  `;
}

function renderCard(app, index) {
  const deployList = app.deploy.map((d) => `<li>${escapeHtml(d)}</li>`).join('');
  const delay = (index % 10) * 0.04;
  return `
    <article class="app-card" data-id="${app.id}" data-category="${escapeHtml(app.category)}" style="animation-delay: ${delay}s">
      <div class="app-card-header">
        <span class="app-card-num">#${app.id}</span>
        <h3 class="app-card-title">${escapeHtml(app.title)}</h3>
        <span class="app-card-value">${escapeHtml(app.value)}</span>
      </div>
      <ul class="app-card-deploy">${deployList}</ul>
    </article>
  `;
}

function renderCategory(category, apps, activeCategory) {
  const categoryApps = apps.filter((a) => a.category === category.id);
  if (activeCategory && activeCategory !== category.id) return '';
  const cards = categoryApps.map((app, i) => renderCard(app, i)).join('');
  return `
    <section class="app-category" data-category="${category.id}">
      <h2 class="app-section-title">${escapeHtml(category.title)} <span class="range">${escapeHtml(category.range)}</span></h2>
      <div class="app-cards">${cards}</div>
    </section>
  `;
}

function renderTam() {
  const html = TAM_DESCRIPTION.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  return `
    <section class="app-tam">
      <h2>Total Addressable Opportunity</h2>
      <p class="tam-figure">$2T – $10T+</p>
      <p>${html}</p>
    </section>
  `;
}

function renderTop5() {
  const list = TOP_FIVE.map(
    (t) =>
      `<li><span class="rank">${t.rank}</span><span class="title">${escapeHtml(t.title)}</span><span class="note">${escapeHtml(t.note)}</span></li>`
  ).join('');
  return `
    <section class="app-top5" id="top5">
      <h2>The Most Powerful 5 Deployments</h2>
      <ul class="app-top5-list">${list}</ul>
      <p class="together">Together these represent <strong>$500B+</strong> markets.</p>
    </section>
  `;
}

function renderWins() {
  const pillars = BRIDGE_WINS_PILLARS.map((p) => `<li>${escapeHtml(p)}</li>`).join('');
  return `
    <section class="app-wins" id="wins">
      <div class="app-wins-inner">
        <h2>How Bridge AI OS Actually Wins</h2>
        <p class="tagline">Your architecture combines:</p>
        <ul class="app-wins-pillars">${pillars}</ul>
        <p class="one-line">Most AI systems do one of these. Bridge AI OS does all of them simultaneously.</p>
      </div>
    </section>
  `;
}

function renderCtas() {
  const baseUrl = typeof window !== 'undefined' && window.__API_BASE != null ? window.__API_BASE : '';
  const base = baseUrl ? baseUrl.replace(/\/$/, '') + '/' : '/';
  const sourceLinks = SOURCES.map(
    (s) => `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.label)}</a>`
  ).join(' · ');
  return `
    <section class="app-ctas" id="ctas">
      <h3>Unlock the Power of AI Orchestration</h3>
      <p>Connect with us to discover how Bridge AI OS can benefit your sector.</p>
      <div class="app-ctas-actions">
        <a href="${base}" class="btn-primary">Get Started</a>
        <a href="/executive-dashboard.html" class="btn-secondary">Executive Dashboard</a>
        <a href="#top5" class="btn-secondary">Learn More</a>
      </div>
      <p style="margin-top:1.5rem">Explore scaling and value strategies:</p>
      <div class="links">
        <a href="#top5">10 fastest ways to $1B–$10B platform</a>
        <a href="#wins">3 deployment strategies to 1M agents</a>
      </div>
      <p class="sources-label">Sources</p>
      <div class="links">${sourceLinks}</div>
    </section>
  `;
}

function getBaseUrl() {
  const base = typeof window !== 'undefined' && window.__API_BASE != null ? window.__API_BASE : '';
  return base ? base.replace(/\/$/, '') + '/' : '/';
}

let activeCategory = '';

function updateCategoryVisibility() {
  appEl.querySelectorAll('.app-category').forEach((section) => {
    section.style.display = activeCategory && section.dataset.category !== activeCategory ? 'none' : '';
  });
}

function render() {
  const baseUrl = getBaseUrl();
  appEl.innerHTML = `
    ${renderNav(baseUrl)}
    ${renderHero(baseUrl)}
    ${renderFeatures()}
    ${renderFilter(activeCategory)}
    <div id="app-content">
      ${CATEGORIES.map((c) => renderCategory(c, APPLICATIONS, activeCategory)).join('')}
    </div>
    ${renderTam()}
    ${renderTop5()}
    ${renderWins()}
    ${renderCtas()}
  `;

  const filterEl = document.getElementById('app-filter');
  if (filterEl) {
    filterEl.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-category]');
      if (!btn) return;
      activeCategory = btn.getAttribute('data-category') || '';
      filterEl.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      updateCategoryVisibility();
    });
  }
}

render();
