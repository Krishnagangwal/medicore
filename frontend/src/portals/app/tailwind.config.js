/** @type {import('tailwindcss').Config} */
export default {
  // Unlike the nurse/doctor portals (which have no ./src subfolder), this
  // merged app nests everything under ./src — see the file tree in the task
  // brief.
  content: ['./index.html', './src/**/*.{js,jsx}'],
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
