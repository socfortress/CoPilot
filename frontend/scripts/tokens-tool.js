import os from "node:os"
import path from "node:path"
import process from "node:process"
import { cancel, intro, isCancel, outro, select, spinner, text } from "@clack/prompts"
import { colord } from "colord"
import fs from "fs-extra"
import _ from "lodash"

const GLOBAL_KEYS = ["border-radius", "line-heights", "font-sizes", "font-families", "font-weights"]
const TYPO_KEYS = ["typo"]
const COLOR_KEYS = ["color"]
const COLOR_OPACITY_LIST = [] // [5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90]
const TOKENS_MAP = [
	{
		token: "colors",
		type: "color"
	},
	{
		token: "fontFamily",
		type: "fontFamilies"
	},
	{
		token: "fontWeight",
		type: "fontWeights"
	},
	{
		token: "fontSize",
		type: "fontSizes"
	},
	{
		token: "lineHeight",
		type: "lineHeights"
	},
	{
		token: "typography",
		type: "typo"
	}
]

const DESIGN_TOKEN_PATH = fs.pathExistsSync(path.join(process.cwd(), "src"))
	? path.join(process.cwd(), "src", "design-tokens.json")
	: path.join(process.cwd(), "design-tokens.json")
const FIGMA_TOKEN_PATH = path.join(process.cwd(), "figma-tokens.json")

function getValue(origin, val) {
	if (val && val.indexOf("{") === 0) {
		const path = val.replace("{", "").replace("}", "")
		return _.get(origin, path)
	}

	return val
}

/**
 * Sanitizes a token or type name based on the provided mapping.
 *
 * This function converts a token name to a type name or vice versa based on the direction specified. It uses a predefined map to find the corresponding sanitized name.
 *
 * @param {string} name - The name of the token or type to be sanitized.
 * @param {"token" | "type"} from - Indicates the current type of the name (`"token"` or `"type"`) to determine the direction of the conversion.
 * @returns {string} The sanitized name, converted to the opposite type. If no mapping is found, returns the original name.
 */
function tokenNameSanitize(name, from) {
	const to = from === "token" ? "type" : "token"

	const pair = TOKENS_MAP.find(o => o[from] === name)

	if (!pair) return name

	return pair[to]
}

/**
 * Imports tokens from a JSON file and processes them into a project file format.
 *
 * This function reads a JSON file containing token definitions, normalizes paths, and organizes tokens into a project file structure. It handles global tokens, typography tokens, and set tokens, and writes the processed data to a specified design token path.
 *
 * @param {string} tokensPath - The path to the JSON file containing the tokens to be imported. The path can be relative or use `~` to refer to the home directory.
 * @returns {string} The path to the design token file where the processed tokens have been written.
 */
async function importTokens(tokensPath) {
	const filePath = path.normalize(tokensPath.trim().replace("~/", `${os.homedir()}/`))
	const tokens = await fs.readJSON(filePath)

	const projectFile = {}

	const globalTokens = tokens.global
	const colorTokens = [
		{ key: "light", value: tokens.light },
		{ key: "dark", value: tokens.dark }
	]

	for (const k in globalTokens) {
		for (const gk of GLOBAL_KEYS) {
			const kIndex = k.indexOf(gk)
			if (kIndex !== -1) {
				const gkParsed = tokenNameSanitize(_.camelCase(gk), "type")
				const name = _.camelCase(k.replace(`${gk}-`, ""))

				_.set(projectFile, `${gkParsed}.${name}`, globalTokens[k].value)
			}
		}
	}

	for (const k in globalTokens) {
		for (const tk of TYPO_KEYS) {
			const kIndex = k.indexOf(tk)
			if (kIndex !== -1) {
				const value = globalTokens[k].value
				const element = _.split(k, "-")[1]
				const tkParsed = tokenNameSanitize(_.camelCase(tk), "type")

				for (const k in value) {
					const prop = value[k]
					if (prop.indexOf("{") === 0) {
						const prefix = tokenNameSanitize(k, "token")
						const ref = prop
							.replace(`${_.kebabCase(prefix)}-`, "")
							.replace("{", "")
							.replace("}", "")
						value[k] = `{${k}.${_.camelCase(ref)}}`
					}
				}

				_.set(projectFile, `${tkParsed}.${element}`, value)
			}
		}
	}

	for (const set of colorTokens) {
		const setName = set.key
		const group = set.value

		for (const k in group) {
			for (const sk of COLOR_KEYS) {
				const regex = /-\d{3}$/
				// exclude opacity variants
				if (k.includes(sk) && !regex.test(k)) {
					const skParsed = tokenNameSanitize(_.camelCase(sk), "type")
					const name = _.camelCase(k.replace(`${sk}-`, ""))
					let value = group[k].value

					if (value.indexOf("{") === 0) {
						const ref = value.replace("{", "").replace("}", "")
						const token = globalTokens[ref]
						if (token?.value) {
							value = token?.value
						}
					}

					value = colord(value).toRgbString()

					_.set(projectFile, `${skParsed}.${setName}.${name}`, value)
				}
			}
		}
	}

	await fs.writeJSON(DESIGN_TOKEN_PATH, projectFile, { spaces: "\t" })

	return DESIGN_TOKEN_PATH
}

/**
 * Exports tokens from the design system and writes them to a JSON file.
 *
 * @returns {string} The path to the exported JSON file.
 */
async function exportTokens() {
	const tokens = await fs.readJSON(DESIGN_TOKEN_PATH)

	const groups = _.chain(tokens)
		.toPairs()
		.map(([k, v]) => ({ key: k, value: v }))
		.value()

	const exportFile = {
		global: {},
		light: {},
		dark: {}
	}

	const globalTokens = groups.filter(o => !["colors", "typography"].includes(o.key))
	const colorTokens = groups.filter(o => ["colors"].includes(o.key))
	const typoTokens = groups.filter(o => ["typography"].includes(o.key))

	for (const group of globalTokens) {
		const type = tokenNameSanitize(group.key, "token")

		for (const name in group.value) {
			const tokenName = _.kebabCase(`${type}-${name}`)

			exportFile.global[tokenName] = {
				value: group.value[name],
				type
			}
		}
	}

	for (const group of colorTokens) {
		const type = tokenNameSanitize(group.key, "token")
		const set = group.value

		for (const setName in set) {
			for (const name in set[setName]) {
				const globalName = _.kebabCase(`${type}-${setName}-${name}`)
				const tokenName = _.kebabCase(`${type}-${name}`)

				const value = colord(set[setName][name]).toRgbString()

				exportFile.global[globalName] = {
					value,
					type
				}

				exportFile[setName][tokenName] = {
					value: `{${globalName}}`,
					type
				}

				for (const opacity of COLOR_OPACITY_LIST) {
					const opacityName = opacity.toString().padStart(3, "0")
					const globalNameOpacity = _.kebabCase(`${type}-${setName}-${name}-${opacityName}`)
					const tokenNameOpacity = _.kebabCase(`${type}-${name}-${opacityName}`)
					const valueOpacity = colord(value)
						.alpha(opacity / 100)
						.toRgbString()

					exportFile.global[globalNameOpacity] = {
						value: valueOpacity,
						type
					}

					exportFile[setName][tokenNameOpacity] = {
						value: `{${globalNameOpacity}}`,
						type
					}
				}
			}
		}
	}

	for (const group of typoTokens) {
		const type = group.key
		const set = group.value

		for (const setName in set) {
			const globalName = `typo-${setName}`
			const value = set[setName]
			const newValue = {}

			for (const k in value) {
				const prop = value[k]
				if (prop.indexOf("{") === 0) {
					const ref = prop.replace("{", "").replace("}", "")
					const path = _.split(ref, ".")[1]
					const prefix = tokenNameSanitize(k, "token")
					newValue[k] = `{${_.kebabCase(`${prefix}-${_.kebabCase(path)}`)}}`
				} else {
					newValue[k] = prop
				}
			}

			// sanitize lineHeight for figma
			if (value.fontSize && tokens?.lineHeight?.default) {
				newValue.lineHeight = Math.round(
					Number.parseInt(getValue(tokens, value.fontSize)) * Number.parseFloat(tokens.lineHeight.default)
				).toString()
			}

			exportFile.global[globalName] = {
				value: newValue,
				type
			}
		}
	}

	await fs.writeJSON(FIGMA_TOKEN_PATH, exportFile, { spaces: "\t" })

	return FIGMA_TOKEN_PATH
}

async function main() {
	console.log()
	intro("Design tokens import/export tool")

	const flowType = await select({
		message: "Choose an action.",
		options: [
			{ value: "import", label: "Import figma tokens" },
			{ value: "export", label: "Export figma json" }
		]
	})

	if (isCancel(flowType)) {
		cancel("Operation cancelled")
		return process.exit(0)
	}

	if (flowType === "import") {
		const tokensPath = await text({
			message: "Tokens json file path...",
			placeholder: "~/Downloads/tokens.json"
		})

		if (isCancel(tokensPath)) {
			cancel("Operation cancelled")
			return process.exit(0)
		}

		const s = spinner()
		s.start("Importing figma token file")

		await importTokens(tokensPath)

		s.stop("Figma token file imported")

		outro(`Template tokens updated`)
	} else {
		const s = spinner()
		s.start("Creating figma token file")

		const filePath = await exportTokens()

		s.stop("Figma token file created")

		outro(`You can find it here: ${filePath}`)
	}
}

main().catch(console.error)
