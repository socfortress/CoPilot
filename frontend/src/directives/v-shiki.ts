import { codeToHtml } from "shiki"
import flourite from "flourite"
import { decode } from "html-entities"

const vShiki = {
	created: async (
		el: HTMLElement,
		binding: { value: { theme?: "dark" | "light"; lang?: string; decode?: boolean } }
	) => {
		const code = binding?.value?.decode ? decode(el.children[0].innerHTML) : el.children[0].innerHTML

		let flouriteDetect = null
		if (!binding?.value?.lang) {
			const fl = flourite(code, { shiki: true }).language
			if (fl !== "unknown") {
				flouriteDetect = fl
			}
		}

		const language = binding?.value?.lang || flouriteDetect || "text"
		const html = await codeToHtml(code, {
			lang: language,
			theme: binding?.value?.theme === "light" ? "slack-ochin" : "aurora-x"
		})
		el.innerHTML = html
	}
}

export { codeToHtml }

export default vShiki
