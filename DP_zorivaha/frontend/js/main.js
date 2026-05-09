/**
 * main.js — Global JavaScript for Зори Ваха
 * Loaded on every page via base.html
 */

'use strict';

/* =========================================================
   Auto-dismiss alerts after 5 seconds
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });
});

/* =========================================================
   Form loading state
   Any form with data-loading attribute shows spinner on submit
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-loading]').forEach(form => {
    form.addEventListener('submit', () => {
      const btn = form.querySelector('[type="submit"]');
      if (!btn || btn.disabled) return;
      btn.disabled = true;
      const original = btn.innerHTML;
      btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>Подождите…`;
      // Re-enable after 15s as safety fallback
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = original;
      }, 15000);
    });
  });
});

/* =========================================================
   Confirm dialogs via data-confirm attribute
   <button data-confirm="Вы уверены?">Удалить</button>
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      const msg = el.dataset.confirm || 'Вы уверены?';
      if (!confirm(msg)) e.preventDefault();
    });
  });
});

/* =========================================================
   Password visibility toggle
   Usage: <button data-toggle-pwd="input_id">
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-toggle-pwd]').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.togglePwd);
      if (!input) return;
      const icon = btn.querySelector('i');
      if (input.type === 'password') {
        input.type = 'text';
        if (icon) icon.className = 'bi bi-eye-slash';
      } else {
        input.type = 'password';
        if (icon) icon.className = 'bi bi-eye';
      }
    });
  });
});

/* =========================================================
   Smooth scroll to anchor
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
});

/* =========================================================
   Tooltip initialization (Bootstrap)
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });
});

/* =========================================================
   Active nav link highlight
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
    if (link.getAttribute('href') === path) {
      link.style.color = 'var(--gold)';
    }
  });
});
