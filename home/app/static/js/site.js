(() => {
  const root = document.documentElement;
  const menuButton = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.main-nav');
  const themeButton = document.querySelector('.theme-toggle');
  const preferred = localStorage.getItem('reaver-theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  root.dataset.theme = preferred;
  themeButton?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('reaver-theme', next);
  });
  menuButton?.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!open));
    nav?.classList.toggle('open', !open);
  });
  nav?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
    menuButton?.setAttribute('aria-expanded', 'false');
    nav.classList.remove('open');
  }));
})();
