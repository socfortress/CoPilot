import hljs from "highlight.js/lib/core"
import javascript from "highlight.js/lib/languages/javascript"
import typescript from "highlight.js/lib/languages/typescript"
import xml from "highlight.js/lib/languages/xml"
import scss from "highlight.js/lib/languages/scss"
import css from "highlight.js/lib/languages/css"
import powershell from "highlight.js/lib/languages/powershell"
import bash from "highlight.js/lib/languages/bash"
import json from "highlight.js/lib/languages/json"
import yaml from "highlight.js/lib/languages/yaml"
//import "highlight.js/styles/monokai.css"
import "highlight.js/styles/atom-one-dark.css"

hljs.registerLanguage("javascript", javascript)
hljs.registerLanguage("typescript", typescript)
hljs.registerLanguage("html", xml)
hljs.registerLanguage("scss", scss)
hljs.registerLanguage("css", css)
hljs.registerLanguage("powershell", powershell)
hljs.registerLanguage("bash", bash)
hljs.registerLanguage("json", json)
hljs.registerLanguage("xml", xml)
hljs.registerLanguage("yaml", yaml)

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
