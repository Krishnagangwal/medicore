/** @type {import('tailwindcss').Config} */
export default {
  // No ./src subfolder in this portal — App.jsx/pages/components/etc. live
  // directly under this directory (same layout as the nurse portal).
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
