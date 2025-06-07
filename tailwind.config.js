/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./project/templates/**/*.html", 
    "./project/static/js/**/*.js",    
  ],
  theme: {
    extend: {
      colors: {
        'brand-dark': '#1A202C',      
        'brand-panel': '#2D3748',     
        'brand-box': '#4A5568',       
        'brand-red': '#E53E3E',       
        'brand-green': '#48BB78',     
        'brand-blue': '#4299E1',      
        'brand-yellow': '#F6E05E',    
        'brand-orange': '#ED8936',    
        'brand-purple': '#9F7AEA',    
        'brand-light-gray': '#F7FAFC',
        'brand-medium-gray': '#A0AEC0',
        'brand-border': '#4A5568',    
      },
      fontFamily: {
        sans: ['Inter', 'Roboto', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Helvetica', 'Arial', 'sans-serif'],
        digital: ['Orbitron', 'Share Tech Mono', '"DS-Digital"', 'monospace'], 
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
