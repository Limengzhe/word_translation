/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        source: {
          edited: '#fee2e2',
          editedBorder: '#f87171',
        },
        syncing: {
          bg: '#fff7ed',
          border: '#fb923c',
        },
      },
    },
  },
  plugins: [],
}
