const THEMES = {
  green: {
    color: '#00b386',
    dim: 'rgba(0, 179, 134, 0.12)',
    hover: '#00c896',
  },
  blue: {
    color: '#4a7ef5',
    dim: 'rgba(74, 126, 245, 0.12)',
    hover: '#5a8ef5',
  },
  red: {
    color: '#e05050',
    dim: 'rgba(224, 80, 80, 0.12)',
    hover: '#f06060',
  },
};

export function applyAccentTheme(accent = 'green') {
  const theme = THEMES[accent] || THEMES.green;
  const root = document.documentElement;
  root.style.setProperty('--blue', theme.color);
  root.style.setProperty('--blue-dim', theme.dim);
  root.style.setProperty('--accent-hover', theme.hover);
  root.dataset.accentColor = THEMES[accent] ? accent : 'green';
}

export function loadSavedTheme() {
  const saved = localStorage.getItem('accent_color') || 'green';
  applyAccentTheme(saved);
  return saved;
}

export const ACCENT_OPTIONS = [
  { id: 'green', name: 'Emerald', color: THEMES.green.color },
  { id: 'blue', name: 'Cobalt', color: THEMES.blue.color },
  { id: 'red', name: 'Crimson', color: THEMES.red.color },
];
