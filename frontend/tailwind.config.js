/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#e0eaff',
          200: '#c7d7fe',
          300: '#a5bbfc',
          400: '#8098f9',
          500: '#6172f3',
          600: '#4f53e8',
          700: '#3f40cc',
          800: '#3337a4',
          900: '#2e3282',
        },
        dark: {
          900: '#0a0d1a',
          800: '#0f1629',
          700: '#151d38',
          600: '#1c2647',
          500: '#243058',
          400: '#2d3b6b',
        },
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#3b82f6',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #4f53e8 0%, #6172f3 50%, #8098f9 100%)',
        'gradient-dark': 'linear-gradient(135deg, #0f1629 0%, #151d38 100%)',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(97, 114, 243, 0.3)',
        'glow-lg': '0 0 40px rgba(97, 114, 243, 0.4)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
