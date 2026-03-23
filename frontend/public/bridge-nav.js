/* Bridge AI OS — Mobile nav hamburger. Run after DOM ready. */
(function () {
  'use strict';
  function init() {
    var nav = document.querySelector('.bridge-nav');
    if (!nav) return;
    var links = nav.querySelector('.bridge-nav-links');
    var toggle = nav.querySelector('.bridge-nav-toggle');
    if (!links || !toggle) return;
    function close() {
      nav.classList.remove('bridge-nav-open');
      document.body.style.overflow = '';
    }
    function open() {
      nav.classList.add('bridge-nav-open');
      document.body.style.overflow = 'hidden';
    }
    function toggleMenu() {
      if (nav.classList.contains('bridge-nav-open')) close(); else open();
    }
    toggle.addEventListener('click', toggleMenu);
    links.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', close);
    });
    window.addEventListener('resize', function () {
      if (window.innerWidth >= 769) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
