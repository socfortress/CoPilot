/* eslint-env node */
require("@rushstack/eslint-patch/modern-module-resolution")

module.exports = {
	root: true,
	env: {
		browser: true,
		amd: true,
		node: true
	},
	globals: {
		NodeJS: true
	},
	extends: ["plugin:vue/vue3-essential", "eslint:recommended", "@vue/eslint-config-typescript"],
	overrides: [
		{
			files: ["cypress/e2e/**.{cy,spec}.{js,ts,jsx,tsx}"],
			extends: ["plugin:cypress/recommended"]
		}
	],
	parserOptions: {
		ecmaVersion: "latest"
	},
	rules: {
		"vue/multi-word-component-names": "off"
	}
}
