/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./project/templates/**/*.html", 
    "./project/static/js/**/*.js",
    "./project/static/css/src/**/*.css",   // CSS फाइलें भी यहाँ add की हैं
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-background)',
        surface: 'var(--color-surface)',
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        'on-primary': 'var(--color-on-primary)',
        'on-surface': 'var(--color-on-surface)',
        'on-surface-variant': 'var(--color-on-surface-variant)',
        outline: 'var(--color-outline)',
        error: 'var(--color-error)',
        // बाकी brand- colors को हटा सकते हो या रख सकते हो अगर ज़रूरत हो तो
      },
      fontFamily: {
        sans: ['var(--font-family-sans)'],
        digital: ['var(--font-family-digital)'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
