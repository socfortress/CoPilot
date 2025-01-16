import { readFileSync } from "node:fs"
import _ from "lodash"
import plugin from "tailwindcss/plugin.js"

const fileUrl = new URL("./src/design-tokens.json", import.meta.url)
const tokens = JSON.parse(readFileSync(fileUrl))

function getValue(origin, val) {
	if (val && val.indexOf("{") === 0) {
		const path = val.replace("{", "").replace("}", "")
		return _.get(origin, path)
	}

	return val
}

function remFromPX(px) {
	return {
		key: Number.parseFloat(_.toNumber(px / 4).toFixed(4)),
		rem: `${Number.parseFloat(_.toNumber(px / 16).toFixed(4))}rem`
	}
}

export default {
	content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
	darkMode: ["selector", `.theme-dark`],
	theme: {
		fontFamily: {
			sans: ["var(--font-family)", "sans-serif"],
			serif: ["var(--font-family-display)", "serif"],
			display: ["var(--font-family-display)", "serif"],
			mono: ["var(--font-family-mono)", "monospace"]
		},
		extend: {
			colors: {
				primary: "rgb(var(--primary-color-rgb))",
				success: "rgb(var(--success-color-rgb))",
				error: "rgb(var(--error-color-rgb))",
				warning: "rgb(var(--warning-color-rgb))",
				info: "rgb(var(--info-color-rgb))",
				border: "rgb(var(--border-color-rgb))",
				hover: "rgb(var(--hover-color-rgb))",
				extra: {
					1: "rgb(var(--extra1-color-rgb))",
					2: "rgb(var(--extra2-color-rgb))",
					3: "rgb(var(--extra3-color-rgb))",
					4: "rgb(var(--extra4-color-rgb))"
				}
			},
			backgroundColor: {
				default: "rgb(var(--bg-default-color-rgb))",
				secondary: "rgb(var(--bg-secondary-color-rgb))",
				body: "rgb(var(--bg-body-color-rgb))",
				sidebar: "rgb(var(--bg-sidebar-color-rgb))"
			},
			textColor: {
				default: "rgb(var(--fg-default-color-rgb))",
				secondary: "rgb(var(--fg-secondary-color-rgb))",
				tertiary: "rgb(var(--fg-tertiary-color-rgb))"
			},
			animation: {
				fade: "fade 0.3s forwards"
			},
			keyframes: {
				fade: {
					from: { opacity: 0 },
					to: { opacity: 1 }
				}
			},
			screens: {
				xs: "460px"
			},
			height: {
				[remFromPX(3).key]: remFromPX(3).rem, // 0.75
				[remFromPX(600).key]: remFromPX(600).rem, // 150
				"60vh": "60vh"
			},
			minHeight: {
				114: "28.5rem",
				120: "30rem",
				[remFromPX(548).key]: remFromPX(548).rem // 137
			},
			maxHeight: {
				"50vh": "50vh",
				106: "26.5rem",
				125: "31.25rem",
				[remFromPX(600).key]: remFromPX(600).rem // 150
			},
			width: {
				[remFromPX(22).key]: remFromPX(22).rem, // 5.5
				[remFromPX(600).key]: remFromPX(600).rem, // 150
				"90vw": "90vw"
			},
			maxWidth: {
				"90vw": "90vw"
			},
			spacing: {
				"20vh": "20vh",
				"50vw": "50vw"
			}
		}
	},
	safelist: [
		"p-4",
		"py-4",
		"!p-1",
		"flex",
		"flex-col",
		"!justify-start",
		"opacity-50",
		"hover:text-red-500",
		"hover:opacity-100",
		"items-center",
		"gap-5",
		"w-72",
		"max-h-50vh",
		"max-w-90vw",
		"!h-0.75",
		"text-primary",
		"mx-1",
		"basis-1/4",
		"basis-1/5"
	],
	plugins: [
		require("@tailwindcss/container-queries"),
		plugin(({ addBase, theme }) => {
			addBase({
				h1: {
					fontFamily: getValue(tokens, tokens?.typography?.h1?.fontFamily),
					fontWeight: getValue(tokens, tokens?.typography?.h1?.fontWeight) || theme("fontWeight.bold"),
					fontSize: getValue(tokens, tokens?.typography?.h1?.fontSize),
					letterSpacing:
						getValue(tokens, tokens?.typography?.h1?.letterSpacing) || theme("letterSpacing.tight")
				},
				h2: {
					fontFamily: getValue(tokens, tokens?.typography?.h2?.fontFamily),
					fontWeight: getValue(tokens, tokens?.typography?.h2?.fontWeight) || theme("fontWeight.bold"),
					fontSize: getValue(tokens, tokens?.typography?.h2?.fontSize),
					letterSpacing:
						getValue(tokens, tokens?.typography?.h2?.letterSpacing) || theme("letterSpacing.tight")
				},
				h3: {
					fontFamily: getValue(tokens, tokens?.typography?.h3?.fontFamily),
					fontWeight: getValue(tokens, tokens?.typography?.h3?.fontWeight) || theme("fontWeight.bold"),
					fontSize: getValue(tokens, tokens?.typography?.h3?.fontSize),
					letterSpacing:
						getValue(tokens, tokens?.typography?.h3?.letterSpacing) || theme("letterSpacing.tight")
				},
				h4: {
					fontFamily: getValue(tokens, tokens?.typography?.h4?.fontFamily),
					fontWeight: getValue(tokens, tokens?.typography?.h4?.fontWeight) || theme("fontWeight.medium"),
					fontSize: getValue(tokens, tokens?.typography?.h4?.fontSize),
					letterSpacing:
						getValue(tokens, tokens?.typography?.h4?.letterSpacing) || theme("letterSpacing.tight")
				},
				h5: {
					fontFamily: getValue(tokens, tokens?.typography?.h5?.fontFamily),
					fontWeight: getValue(tokens, tokens?.typography?.h5?.fontWeight) || theme("fontWeight.bold"),
					fontSize: getValue(tokens, tokens?.typography?.h5?.fontSize),
					letterSpacing:
						getValue(tokens, tokens?.typography?.h5?.letterSpacing) || theme("letterSpacing.tight")
				},
				h6: {
					fontFamily: getValue(tokens, tokens?.typography?.h6?.fontFamily),
					fontWeight: getValue(tokens, tokens?.typography?.h6?.fontWeight) || theme("fontWeight.bold"),
					fontSize: getValue(tokens, tokens?.typography?.h6?.fontSize),
					letterSpacing: getValue(tokens, tokens?.typography?.h6?.letterSpacing)
				}
			})
		})
	]
}
