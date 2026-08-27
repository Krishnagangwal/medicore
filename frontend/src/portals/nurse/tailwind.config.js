/** @type {import('tailwindcss').Config} */
export default {
  // No ./src subfolder in this portal (see file tree in the task brief) —
  // App.jsx/pages/components/etc. live directly under this directory.
  content: [
    './index.html',
    './App.jsx',
    './main.jsx',
    './pages/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
    './context/**/*.{js,jsx}',
    './services/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3d6b35',
        accent: '#5a9e4e',
        surface: '#f0f4f0',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
