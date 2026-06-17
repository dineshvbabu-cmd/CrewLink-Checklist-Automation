/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'crew-navy': '#1a2a4a',
        'crew-header': '#2c3e6b',
        'crew-section': '#e8eef5',
        'crew-orange': '#e67e22',
        'crew-blue': '#2980b9',
        'crew-red': '#e74c3c',
        'crew-green': '#27ae60',
        'crew-cta': '#c0392b',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
