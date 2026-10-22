/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'], display: ['Manrope', 'Inter', 'sans-serif'] },
      colors: { ink: '#09111f', mint: '#5eead4', violet: '#8b5cf6' },
      boxShadow: { glow: '0 0 60px rgba(94,234,212,.13)' },
    },
  },
  plugins: [],
};
