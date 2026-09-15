/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Core investigation palette
        charcoal: '#14171f',
        'charcoal-light': '#1c2030',
        cream: '#f4f2ed',
        'cream-dark': '#e8e6e1',
        dossier: '#d4a853',
        'dossier-dim': '#b8933f',
        'dossier-glow': '#e8c06a',
        alert: '#c0392b',
        'alert-dim': '#962d22',
        field: '#27ae60',
        'field-dim': '#1e8c4c',
        crosscase: '#2c6fbb',
        'crosscase-dim': '#245a96',
        ink: '#1a1a2e',
        mist: '#e8e6e1',
        'mist-dark': '#d5d2cb',
        // Graph entity colors — muted, forensic
        node: {
          person: '#4a7fbf',
          phone: '#5a9e6f',
          email: '#8b6db5',
          ip: '#c0544f',
          upi: '#c49a3c',
          vehicle: '#c77840',
          device: '#3a9aa0',
          location: '#bf6b8a',
          org: '#6e7fbf',
          bank: '#4aaa6a',
          social: '#8b6db5',
          url: '#7a8a9a',
          case: '#6a7a8a',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Inter', 'sans-serif'],
      },
      fontSize: {
        'stat': ['1.75rem', { lineHeight: '2rem', fontWeight: '800', letterSpacing: '-0.02em' }],
        'label': ['0.6875rem', { lineHeight: '1rem', fontWeight: '600', letterSpacing: '0.05em' }],
      },
    },
  },
  plugins: [],
}
