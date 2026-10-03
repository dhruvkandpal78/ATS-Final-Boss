try {
  document.documentElement.dataset.theme = localStorage.getItem('atsfb-theme') ||
    'dark';
} catch {
  document.documentElement.dataset.theme = 'dark';
}
