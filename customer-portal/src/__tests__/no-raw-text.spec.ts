import { readdirSync, readFileSync, statSync } from "node:fs"
import { join, relative, resolve } from "node:path"
import process from "node:process"
import { describe, expect, it } from "vitest"
import { parse } from "vue/compiler-sfc"

/**
 * No user-facing text is written in a component or a UI helper (#1310): every word the portal shows
 * goes through vue-i18n, so it can be shown in the user's language.
 *
 * Checked: a template's text, its user-facing attributes (static or a bound string literal), string
 * literals in its interpolations, and, in scripts and UI helpers, the usual ways text reaches the
 * screen (naive's message and dialog calls, `label: "…"`-style option fields). Data that is not
 * prose (codes, units, brand names, examples) is listed in `ALLOWED` with the reason.
 *
 * `RAW_TEXT_DIRS=components/alerts,views/Alerts` limits the check to those folders under `src/`.
 */

const SRC = resolve(__dirname, "..")

/** Folders whose files show text: components and pages, layouts, and the helpers that build labels. */
const SCANNED = ["components", "views", "app-layouts", "composables", "utils"]
const SKIPPED_DIRS = new Set(["__tests__", "lang"])

/** Attributes a reader sees or a screen reader announces. */
const USER_ATTRIBUTES = new Set([
	"placeholder",
	"title",
	"label",
	"description",
	"aria-label",
	"alt",
	"content",
	"positive-text",
	"negative-text",
	"empty-description",
	"tooltip",
	"text",
	"header",
	"heading",
	"subtitle",
	"caption",
	"hint"
])

/** Text that is not prose to translate, by file (relative to `src/`) or `*` for any file, with why. */
const ALLOWED: Record<string, string[]> = {
	// Product names, units, formats and codes read the same in every language.
	"*": ["CoPilot", "CSV", "PDF", "JSON", "IP", "IoCs", "IoC", "CVE", "CVSS", "EPSS", "SCA", "SLA", "MITRE", "Wazuh", "UTC", "ID", "OK", "N/A", "—", "·"],
	// The agent card names each field by its API key, like the rest of its raw fields.
	"components/agents/AgentDetails/AgentOverview.vue": ["wazuh_agent_status", "critical_asset"],
	// CVSS, upper-cased by CSS.
	"components/agents/AgentDetails/AgentVulnerabilities.vue": ["cvss"],
	// Example values in the invitation form's placeholders.
	"components/users/InviteUserDialog.vue": ["jane.doe", "jane.doe@example.com"]
}

const scriptPatterns: [RegExp, string][] = [
	[/\b(?:message|notification|dialog)\.(?:success|error|warning|info|create)\(\s*(["'`])([A-Za-z][^"'`]*)\1/g, "a message"],
	[
		/\b(?:label|title|description|placeholder|content|positiveText|negativeText|emptyDescription|tooltip|text|meta)\s*:\s*(["'`])([A-Z][a-z][^"'`]*)\1/g,
		"an option's text"
	]
]

function files(dir: string): string[] {
	return readdirSync(dir).flatMap(name => {
		const path = join(dir, name)
		if (statSync(path).isDirectory()) return SKIPPED_DIRS.has(name) ? [] : files(path)
		return /\.(?:vue|ts)$/.test(name) && !/\.d\.ts$/.test(name) && !/\.spec\.ts$/.test(name) ? [path] : []
	})
}

function isProse(text: string): boolean {
	return /[A-Z][a-z]|[a-z]{2,}/.test(text)
}

function allowed(file: string, text: string): boolean {
	const value = text.trim()
	return [...(ALLOWED["*"] ?? []), ...(ALLOWED[file] ?? [])].includes(value) || !isProse(value)
}

/** A quoted string in an expression that reads like prose: `"Waiting on you"`, not `"OPEN"` or `"carbon:x"`. */
function proseLiterals(expression: string): string[] {
	return [...expression.matchAll(/(["'`])((?:(?!\1).)*)\1/g)]
		.map(m => m[2] ?? "")
		.filter(text => /[A-Z][a-z]+ [a-z]|^[A-Z][a-z]{2,}$/.test(text) && !/[:/]|^\w+\.\w+/.test(text))
}

interface Finding {
	file: string
	text: string
	where: string
}

interface Node {
	type: number
	content?: string | { content?: string }
	tag?: string
	props?: { type: number; name: string; value?: { content: string }; arg?: { content?: string }; exp?: { content?: string } }[]
	children?: Node[]
	loc: { start: { line: number } }
}

function walk(node: Node, file: string, out: Finding[]) {
	if (node.type === 1) {
		if (node.props?.some(prop => prop.name === "pre")) return
		for (const prop of node.props ?? []) {
			if (prop.type === 6 && USER_ATTRIBUTES.has(prop.name) && prop.value && !allowed(file, prop.value.content)) {
				out.push({ file, text: prop.value.content, where: `${prop.name}= on line ${node.loc.start.line}` })
			}
			if (prop.type === 7 && prop.name === "bind" && USER_ATTRIBUTES.has(prop.arg?.content ?? "") && prop.exp?.content) {
				for (const text of proseLiterals(prop.exp.content)) {
					if (!allowed(file, text)) out.push({ file, text, where: `:${prop.arg?.content} on line ${node.loc.start.line}` })
				}
			}
		}
		if (node.tag === "code" || node.tag === "pre") return
	}
	if (node.type === 2 && typeof node.content === "string" && !allowed(file, node.content)) {
		out.push({ file, text: node.content.trim(), where: `text on line ${node.loc.start.line}` })
	}
	if (node.type === 5 && typeof node.content === "object" && node.content?.content) {
		for (const text of proseLiterals(node.content.content)) {
			if (!allowed(file, text)) out.push({ file, text, where: `{{ }} on line ${node.loc.start.line}` })
		}
	}
	for (const child of node.children ?? []) walk(child, file, out)
}

function scanScript(source: string, file: string, out: Finding[]) {
	for (const [pattern, what] of scriptPatterns) {
		for (const match of source.matchAll(pattern)) {
			const text = match[2] ?? ""
			if (!allowed(file, text)) out.push({ file, text, where: what })
		}
	}
}

function findings(): Finding[] {
	const only = (process.env.RAW_TEXT_DIRS ?? "")
		.split(",")
		.map(dir => dir.trim())
		.filter(Boolean)
	const roots = only.length ? only : SCANNED
	const out: Finding[] = []
	for (const root of roots) {
		for (const path of files(join(SRC, root))) {
			const file = relative(SRC, path)
			const source = readFileSync(path, "utf8")
			if (path.endsWith(".vue")) {
				const { descriptor } = parse(source, { filename: path })
				if (descriptor.template?.ast) walk(descriptor.template.ast as unknown as Node, file, out)
				scanScript(`${descriptor.script?.content ?? ""}\n${descriptor.scriptSetup?.content ?? ""}`, file, out)
			} else {
				scanScript(source, file, out)
			}
		}
	}
	return out
}

describe("the portal's text", () => {
	it("is all translated: no user-facing text is written in a component", () => {
		const raw = findings().map(f => `${f.file} (${f.where}): ${JSON.stringify(f.text)}`)
		expect(raw).toEqual([])
	})
})
