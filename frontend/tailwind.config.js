import { readFileSync } from "fs"
import plugin from "tailwindcss/plugin.js"
import _ from "lodash"
const fileUrl = new URL("./src/design-tokens.json", import.meta.url)
const tokens = JSON.parse(readFileSync(fileUrl))

function getValue(origin, val) {
	if (val && val.indexOf("{") === 0) {
		const path = val.replace("{", "").replace("}", "")
		return _.get(origin, path)
	}

	return val
}

export default {
	content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
	darkMode: ["class"],
	theme: {
		extend: {
			screens: {
				xs: "460px"
			},
			height: {
				0.75: "0.1875rem",
				150: "37.5rem",
				"60vh": "60vh"
			},
			width: {
				5.5: "1.375rem",
				150: "37.5rem"
			},
			spacing: {
				"20vh": "20vh",
				"50vw": "50vw"
			},
			maxHeight: {
				"50vh": "50vh"
			},
			maxWidth: {
				"90vw": "90vw"
			}
		}
	},
	safelist: [
		"p-4",
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
		"max-w-90vw"
	],
	plugins: [
		plugin(function ({ addBase, theme }) {
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
