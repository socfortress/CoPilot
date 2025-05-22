import flourite from "flourite"
import { decode } from "html-entities"
import { codeThemes, getHighlighter } from "@/utils/highlighter"

const vShiki = {
	created: async (
		el: HTMLElement,
		binding: { value: { lang?: string; fallbackLang?: string; decode?: boolean } }
	) => {
		const code = binding?.value?.decode ? decode(el.children[0].innerHTML) : el.children[0].innerHTML

		let flouriteDetect = null
		if (!binding?.value?.lang) {
			const fl = flourite(code, { shiki: true }).language
			if (fl !== "unknown") {
				flouriteDetect = fl
			}
		}

		const language = binding?.value?.lang || flouriteDetect || binding?.value?.fallbackLang || "text"
		const html = (await getHighlighter()).codeToHtml(code, {
			lang: language,
			themes: codeThemes
		})
		el.innerHTML = html
	}
}

export default vShiki
