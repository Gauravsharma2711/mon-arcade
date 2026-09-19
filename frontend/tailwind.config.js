/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        arcade: {
          bg: '#07070b',
          'bg-raised': '#0b0b12',
          panel: '#11111a',
          'panel-raised': '#171722',
          border: '#292938',
          text: '#f3f3f3',
          muted: '#9b9ba8',
          subtle: '#666675',
          accent: '#8cff00',
          lime: '#8cff00',
          cyan: '#35e8ff',
          pink: '#ff3ea5',
          warning: '#ffd23f',
          danger: '#ff4d5a',
        },
      },
      fontFamily: {
        display: ['"Press Start 2P"', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        sm: '2px',
        DEFAULT: '4px',
        md: '6px',
        lg: '8px',
      },
      borderWidth: {
        DEFAULT: '1px',
        1: '1px',
        2: '2px',
      },
      boxShadow: {
        'arcade-lime': '0 0 16px -2px rgba(140, 255, 0, 0.25)',
        'arcade-pink': '0 0 16px -2px rgba(255, 62, 165, 0.25)',
        'arcade-cyan': '0 0 16px -2px rgba(53, 232, 255, 0.25)',
        'arcade-panel': '0 4px 24px -2px rgba(0, 0, 0, 0.6)',
      },
    },
  },
  plugins: [],
};
