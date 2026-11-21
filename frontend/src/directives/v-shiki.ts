import flourite from "flourite"
import { decode } from "html-entities"
import { detectionSample, highlightable, MAX_HIGHLIGHT_LINE } from "@/utils/code-highlight"
import { codeThemes, getHighlighter } from "@/utils/highlighter"

const vShiki = {
	created: async (
		el: HTMLElement,
		binding: { value: { lang?: string; fallbackLang?: string; decode?: boolean } }
	) => {
		const children = el.children[0]

		if (!children) return

		const code = binding?.value?.decode ? decode(children.innerHTML) : children.innerHTML

		// Too large to highlight without holding the page up: it stays as it was rendered (#1360).
		if (!highlightable(code)) return

		let flouriteDetect = null
		if (!binding?.value?.lang) {
			// Detection reads the start only: its cost grows with the square of a line's length.
			const fl = flourite(detectionSample(code), { shiki: true }).language
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
			themes: codeThemes,
			// A longer line is shown as it is: tokenizing slows down with the square of its length.
			tokenizeMaxLineLength: MAX_HIGHLIGHT_LINE
		})
		el.innerHTML = html
	}
}

export default vShiki
