/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          bg: '#0a0b0e',
          panel: 'rgba(17, 19, 25, 0.75)',
          border: 'rgba(255, 255, 255, 0.08)',
          card: '#161920',
          hover: '#1e222c',
          text: '#94a3b8',
          textBright: '#f8fafc'
        },
        rosegold: {
          light: '#f5d6b3',
          DEFAULT: '#e0a96d',
          dark: '#c58c50',
          glow: 'rgba(224, 169, 109, 0.25)'
        },
        cyber: {
          cyan: '#00f2fe',
          cyanGlow: 'rgba(0, 242, 254, 0.25)',
          green: '#00e676',
          red: '#ff4b4b'
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        'glow-rose': '0 0 15px rgba(224, 169, 109, 0.15)',
        'glow-cyan': '0 0 15px rgba(0, 242, 254, 0.2)',
      }
    },
  },
  plugins: [],
}
