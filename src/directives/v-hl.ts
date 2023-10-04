import hljs from "highlight.js/lib/core"
import javascript from "highlight.js/lib/languages/javascript"
import typescript from "highlight.js/lib/languages/typescript"
import html from "highlight.js/lib/languages/xml"
import scss from "highlight.js/lib/languages/scss"
import css from "highlight.js/lib/languages/css"
//import "highlight.js/styles/monokai.css"
import "highlight.js/styles/atom-one-dark.css"

hljs.registerLanguage("javascript", javascript)
hljs.registerLanguage("typescript", typescript)
hljs.registerLanguage("html", html)
hljs.registerLanguage("scss", scss)
hljs.registerLanguage("css", css)

const vHl = {
	created: (el: HTMLElement, binding: { arg: string }) => {
		if (binding.arg) {
			el.innerHTML = hljs.highlight(el.children[0].innerHTML, { language: binding.arg }).value
		} else {
			el.innerHTML = hljs.highlightAuto(el.children[0].innerHTML).value
		}
		resetIndent(el)
	}
}

function resetIndent(el: HTMLElement) {
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

export { hljs, resetIndent }

export default vHl
