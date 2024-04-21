import { codeToHtml } from "shiki"
import flourite from "flourite"

const vShiki = {
	created: async (el: HTMLElement, binding: { value: { theme: string; lang?: string } }) => {
		const html = await codeToHtml(el.children[0].innerHTML, {
			lang: binding?.value?.lang || flourite(el.children[0].innerHTML, { shiki: true }).language || "text",
			theme: binding?.value?.theme || ""
		})
		el.innerHTML = html
	}
}

export { codeToHtml }

export default vShiki
