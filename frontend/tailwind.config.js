const v = (n) => `rgb(var(--c-${n}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        page: v('page'),
        card: v('card'),
        fg: v('fg'),
        muted: v('muted'),
        accent: v('accent'),
        accenth: v('accenth'),
        onaccent: v('onaccent'),
        deep: v('deep'),
        deeptext: v('deeptext'),
        nav: v('nav'),
        invfg: v('invfg'),
        ink: v('ink'),
        subtle: v('subtle'),
        panel: v('panel'),
        brand: {
          green: '#5DD62C',
          darkgreen: '#337418',
          black: '#0F0F0F',
          grey: '#F8F8F8',
          bg: '#F8F8F8',
          dark: '#0F0F0F',
          primary: '#5DD62C',
          secondary: '#337418',
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
