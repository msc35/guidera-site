// Header scroll state
(function () {
  const header = document.querySelector('.header');
  if (!header) return;
  const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 8);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
})();

// Mobile menu toggle
(function () {
  const btn = document.querySelector('.menu-btn');
  const menu = document.querySelector('.mobile-menu');
  const iconOpen = document.querySelector('.menu-btn .icon-menu');
  const iconClose = document.querySelector('.menu-btn .icon-close');
  if (!btn || !menu) return;
  btn.addEventListener('click', () => {
    const open = menu.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (iconOpen && iconClose) {
      iconOpen.style.display = open ? 'none' : 'block';
      iconClose.style.display = open ? 'block' : 'none';
    }
  });
})();

// Active nav link
(function () {
  const path = location.pathname.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
  document.querySelectorAll('[data-nav]').forEach((a) => {
    const href = a.getAttribute('href') || '';
    const target = href.replace(/\.html$/, '').replace(/\/$/, '') || '/';
    const current = path.replace(/\/$/, '') || '/';
    if (target === current || (target === '/' && (current === '/' || current === '/index'))) {
      a.classList.add('active');
    }
  });
})();

// Reveal on scroll (IntersectionObserver)
(function () {
  const els = document.querySelectorAll('.reveal');
  if (!els.length || !('IntersectionObserver' in window)) {
    els.forEach((el) => el.classList.add('in'));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const delay = entry.target.getAttribute('data-delay') || '0';
          entry.target.style.transitionDelay = delay + 'ms';
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    },
    { rootMargin: '0px 0px -10% 0px', threshold: 0.1 }
  );
  els.forEach((el) => io.observe(el));
})();

// Footer year
(function () {
  const y = document.getElementById('year');
  if (y) y.textContent = new Date().getFullYear();
})();
