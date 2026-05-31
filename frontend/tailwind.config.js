/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eff5ff',
          100: '#dbe7fe',
          200: '#bfd3fe',
          300: '#94b6fd',
          400: '#638dfa',
          500: '#4a72f5',
          600: '#3b56ea',
          700: '#3243d2',
          800: '#2e3aa9',
          900: '#2b3786',
        },
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Microsoft YaHei', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
