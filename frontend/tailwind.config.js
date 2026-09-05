/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        page: "#f5f5f5",
        panel: "#ffffff",
        panelAlt: "#f9f9fa",
        borderRef: "#d9d9da",
        borderStrong: "#bfbfc0",
        textPrimary: "#1f1f21",
        textSecondary: "#6c6c73",
        textTertiary: "#9d9da5",
        critical: "#942222",
        criticalBg: "#f7e6e6",
        elevated: "#997107",
        elevatedBg: "#f8ecd6",
        low: "#666668",
        lowBg: "#e8e8ea",
        success: "#155724",
        successBg: "#d4edda",
        navBg: "#1c1c1f",
        navActive: "#333336",
        navText: "#9d9da5",
        navTextActive: "#ffffff",
        dark: "#1c1c1f",
        accent: "#3b82f6",
      },
      fontSize: {
        'xxs': '0.625rem', // 10px
        'xs-plus': '0.8125rem', // 13px
      },
      spacing: {
        '18': '4.5rem',
      }
    },
  },
  plugins: [],
}
