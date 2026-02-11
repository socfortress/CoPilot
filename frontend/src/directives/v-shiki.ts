import flourite from "flourite"
import { decode } from "html-entities"
import { codeThemes, getHighlighter } from "@/utils/highlighter"

const vShiki = {
	created: async (
		el: HTMLElement,
		binding: { value: { lang?: string; fallbackLang?: string; decode?: boolean } }
	) => {
		const children = el.children[0]

		if (!children) return

		const code = binding?.value?.decode ? decode(children.innerHTML) : children.innerHTML

		let flouriteDetect = null
		if (!binding?.value?.lang) {
			const fl = flourite(code, { shiki: true }).language
			if (fl !== "unknown") {
				flouriteDetect = fl
			}
		}

		const language = binding?.value?.lang || flouriteDetect || binding?.value?.fallbackLang || "text"

		const formattedCode = (val: string) => {
			try {
				return JSON.stringify(JSON.parse(val), null, 4)
			} catch {
				return val
			}
		}

		const html = (await getHighlighter()).codeToHtml(formattedCode(code), {
			lang: language,
			themes: codeThemes
		})
		el.innerHTML = html
	}
}

export default vShiki
