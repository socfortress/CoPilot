/** @type {import('tailwindcss').Config} */
const plugin = require("tailwindcss/plugin")
const tokens = require("./src/design-tokens.json")
const _ = require("lodash")

function getValue(origin, val) {
	if (val && val.indexOf("{") === 0) {
		const path = val.replace("{", "").replace("}", "")
		return _.get(origin, path)
	}

	return val
}

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
