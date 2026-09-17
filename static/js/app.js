(() => {
  const root = document.documentElement;
  const storedTheme = localStorage.getItem('nse-theme');
  if (storedTheme) root.dataset.theme = storedTheme;

  const themeToggle = document.getElementById('themeToggle');
  themeToggle?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('nse-theme', next);
  });

  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  const openSidebar = () => { sidebar?.classList.add('open'); backdrop?.classList.add('show'); };
  const closeSidebar = () => { sidebar?.classList.remove('open'); backdrop?.classList.remove('show'); };
  document.getElementById('openSidebar')?.addEventListener('click', openSidebar);
  document.getElementById('closeSidebar')?.addEventListener('click', closeSidebar);
  backdrop?.addEventListener('click', closeSidebar);

  document.querySelectorAll('.refresh-form').forEach(form => {
    form.addEventListener('submit', () => form.querySelector('.refresh-button')?.classList.add('loading'));
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

  const animateNumber = (el) => {
    const target = parseFloat(el.dataset.count || el.textContent || '0');
    if (!Number.isFinite(target)) return;
    const duration = 700;
    const start = performance.now();
    const decimals = String(target).includes('.') ? 1 : 0;
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = (target * eased).toFixed(decimals);
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  document.querySelectorAll('[data-count]').forEach(animateNumber);

  document.querySelectorAll('.premium-card').forEach(card => {
    card.addEventListener('pointermove', (e) => {
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', `${e.clientX - r.left}px`);
      card.style.setProperty('--my', `${e.clientY - r.top}px`);
    });
  });

  const liveSearch = document.querySelector('[data-live-search]');
  if (liveSearch) {
    liveSearch.addEventListener('input', () => {
      const q = liveSearch.value.toLowerCase().trim();
      document.querySelectorAll('[data-stock-row]').forEach(row => {
        row.hidden = q && !(row.dataset.name || '').includes(q);
      });
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault(); liveSearch.focus();
      }
    });
  }

  const table = document.getElementById('stockTable');
  if (table) {
    table.querySelectorAll('th[data-sort]').forEach((th, index) => {
      th.classList.add('sortable');
      th.addEventListener('click', () => {
        const tbody = table.tBodies[0];
        const rows = Array.from(tbody.querySelectorAll('tr[data-stock-row]'));
        const direction = th.dataset.direction === 'asc' ? 'desc' : 'asc';
        table.querySelectorAll('th[data-sort]').forEach(h => delete h.dataset.direction);
        th.dataset.direction = direction;
        rows.sort((a, b) => {
          const ac = a.cells[index], bc = b.cells[index];
          let av = ac.dataset.value ?? ac.innerText.trim();
          let bv = bc.dataset.value ?? bc.innerText.trim();
          if (th.dataset.sort === 'number') { av = parseFloat(av) || 0; bv = parseFloat(bv) || 0; }
          const result = av < bv ? -1 : av > bv ? 1 : 0;
          return direction === 'asc' ? result : -result;
        });
        rows.forEach(row => tbody.appendChild(row));
      });
    });
  }

  document.querySelector('.density-toggle')?.addEventListener('click', () => {
    document.querySelector('.table-panel')?.classList.toggle('compact-table');
  });
})();
