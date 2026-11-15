/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          green: '#08CB00',
          darkgreen: '#253900',
          black: '#000000',
          grey: '#EEEEEE',
          bg: '#EEEEEE',
          dark: '#000000',
          primary: '#08CB00',
          secondary: '#253900',
          muted: '#555555',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
