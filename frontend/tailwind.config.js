/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'deep-navy': '#122056',
        'slate-indigo': '#5b65dc',
        'lavender-mist': '#eeeffd',
        'bright-snow': '#fafafd',
        accent: '#5b65dc',
        surface: '#ffffff',
        'surface-soft': '#f4f5ff',
      },
      boxShadow: {
        soft: '0 24px 60px rgba(18, 32, 86, 0.08)',
      },
      borderRadius: {
        xl: '1.125rem',
      },
    },
  },
}
