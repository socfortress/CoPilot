import path from "node:path"
import { fileURLToPath } from "node:url"
import globals from "globals"

import { FlatCompat } from "@eslint/eslintrc"
import js from "@eslint/js"
import pluginVue from "eslint-plugin-vue"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const compat = new FlatCompat({
	baseDirectory: __dirname
})

export default [
	{
		ignores: ["**/dist/*", "**/tests/*", "**/.gitignore", "**/vite-env.d.ts"]
	},
	...pluginVue.configs["flat/essential"],
	js.configs.recommended,
	...compat.extends("@vue/eslint-config-typescript/recommended"),
	...compat.extends("@vue/eslint-config-prettier/skip-formatting"),
	{
		files: [
			"**/*.vue",
			"**/*.js",
			"**/*.jsx",
			"**/*.cjs",
			"**/*.mjs",
			"**/*.ts",
			"**/*.tsx",
			"**/*.cts",
			"**/*.mts"
		],
		languageOptions: {
			ecmaVersion: "latest",
			globals: {
				...globals.browser,
				...globals.node,
				...globals.amd
			}
		},
		rules: {
			"vue/multi-word-component-names": "off",
			"vue/no-setup-props-destructure": "off"
		}
	}
]
