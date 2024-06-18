import { getHighlighterCore } from "shiki/core"
import getWasm from "shiki/wasm"

const THEME_LIGHT = "slack-ochin"
const THEME_DARK = "aurora-x"

export async function getHighlighter() {
	return await getHighlighterCore({
		themes: [import("shiki/themes/slack-ochin.mjs"), import("shiki/themes/aurora-x.mjs")],
		langs: [
			import("shiki/langs/javascript.mjs"),
			import("shiki/langs/typescript.mjs"),
			import("shiki/langs/powershell.mjs"),
			import("shiki/langs/shellscript.mjs"),
			import("shiki/langs/json.mjs"),
			import("shiki/langs/xml.mjs"),
			import("shiki/langs/yaml.mjs"),
			import("shiki/langs/html.mjs"),
			import("shiki/langs/scss.mjs"),
			import("shiki/langs/css.mjs"),
			import("shiki/langs/csharp.mjs"),
			import("shiki/langs/http.mjs")
		],
		loadWasm: getWasm
	})
}

export const codeThemes = {
	light: THEME_LIGHT,
	dark: THEME_DARK
}

export function resetIndent(el: HTMLElement) {
	if (el) {
		let lines: string[] = el.innerHTML?.split("\n")

		if (lines?.length) {
			if (lines[0] === "") {
				lines.shift()
			}

			const matches = /^[\s\t]+/.exec(lines[0])
			const indentation = matches !== null ? matches[0] : null
			if (indentation) {
				lines = lines.map(line => {
					line = line.replace(indentation, "")
					return line.replace(/\t/g, "    ")
				})

				el.innerHTML = lines.join("\n").trim()
			}
		}
	}
}
