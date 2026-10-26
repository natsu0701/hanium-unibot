/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '"Pretendard Variable"',
          'Pretendard',
          'ui-sans-serif',
          'system-ui',
          'sans-serif',
        ],
      },
      borderRadius: {
        'md-xs': '4px',
        'md-sm': '8px',
        'md-md': '12px',
        'md-lg': '16px',
        'md-xl': '28px',
      },
      boxShadow: {
        'md-1':
          '0 1px 2px 0 rgb(0 0 0 / 0.3), 0 1px 3px 1px rgb(0 0 0 / 0.15)',
        'md-2':
          '0 1px 2px 0 rgb(0 0 0 / 0.3), 0 2px 6px 2px rgb(0 0 0 / 0.15)',
      },
      transitionTimingFunction: {
        'md-standard': 'cubic-bezier(0.2, 0, 0, 1)',
        'md-emphasized': 'cubic-bezier(0.2, 0, 0, 1)',
      },
      transitionDuration: {
        'md-short': '200ms',
        'md-medium': '300ms',
      },
    },
  },
  plugins: [],
}
