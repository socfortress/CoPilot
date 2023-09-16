/** @type {import('tailwindcss').Config} */
const plugin = require("tailwindcss/plugin")

module.exports = {
	content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
	darkMode: ["class"],
	theme: {
		extend: {
			screens: {
				xs: "460px"
			}
		}
	},
	plugins: [
		plugin(function ({ addBase, theme }) {
			addBase({
				h1: {
					fontWeight: theme("fontWeight.bold"),
					letterSpacing: theme("letterSpacing.tight")
				},
				h2: {
					fontWeight: theme("fontWeight.bold"),
					letterSpacing: theme("letterSpacing.tight")
				},
				h3: {
					fontWeight: theme("fontWeight.bold"),
					letterSpacing: theme("letterSpacing.tight")
				},
				h4: {
					fontWeight: theme("fontWeight.medium"),
					letterSpacing: theme("letterSpacing.tight")
				},
				h5: {
					fontWeight: theme("fontWeight.bold"),
					letterSpacing: theme("letterSpacing.tight")
				},
				h6: {
					fontWeight: theme("fontWeight.medium")
				}
			})
		})
	]
}
