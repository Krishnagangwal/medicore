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
        // Warm neutrals for the landing page's framed-hero redesign — kept
        // separate from `surface` (the app's cool mint gray) since the two
        // are used in very different contexts.
        cream: '#f7f5ef',
        'cream-dark': '#eeebe1',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['"Playfair Display"', 'ui-serif', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
