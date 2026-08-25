<template>
	<div class="flex flex-col gap-4 text-sm">
		<p class="text-secondary">
			Graylog search is based on Apache Lucene. Full reference:
			<a
				href="https://go2docs.graylog.org/current/making_sense_of_your_log_data/search_syntax_reference.htm"
				target="_blank"
				rel="noopener noreferrer"
			>
				Graylog Search Syntax Reference ↗
			</a>
		</p>

		<n-input v-model:value="filter" size="small" clearable placeholder="Filter syntax…">
			<template #prefix><Icon :name="SearchIcon" :size="14" /></template>
		</n-input>

		<!-- gotchas (hidden while filtering to reduce noise) -->
		<div v-if="!filter" class="flex flex-col gap-2">
			<div v-for="note of notes" :key="note" class="flex items-start gap-2">
				<Icon :name="WarnIcon" :size="15" class="mt-0.5 shrink-0 text-amber-500" />
				<span v-html="note" />
			</div>
		</div>

		<!-- sections -->
		<div v-for="sec of filteredSections" :key="sec.title" class="flex flex-col gap-1.5">
			<div class="text-secondary text-xs font-semibold tracking-wide uppercase">{{ sec.title }}</div>
			<div
				v-for="(row, i) of sec.items"
				:key="i"
				class="grid grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] items-baseline gap-3 border-b border-[var(--n-border-color)] py-1 last:border-0"
			>
				<code
					class="text-primary hover:text-primary-hover cursor-pointer break-all"
					title="Click to copy"
					@click="copy(row.code)"
				>
					{{ row.code }}
				</code>
				<span class="text-secondary">{{ row.desc }}</span>
			</div>
		</div>

		<n-empty v-if="filter && !filteredSections.length" description="No syntax matches your filter." class="py-6" />

		<div class="text-secondary text-xs">
			Escape any of these to search them literally (with <code>\</code>):
			<code class="break-all">&amp; | : \ / + - ! ( ) {{ "{ } [ ] ^ \" ~ * ?" }}</code>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NEmpty, NInput, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"

const WarnIcon = "carbon:warning-alt"
const SearchIcon = "carbon:search"

const message = useMessage()
const filter = ref("")

async function copy(text: string) {
	try {
		await navigator.clipboard.writeText(text)
		message.success("Copied to clipboard")
	} catch {
		message.error("Couldn't copy to clipboard")
	}
}

const notes = [
	"<b>Case-sensitive</b> by default (WhitespaceAnalyzer) — <code>ERROR</code> ≠ <code>error</code>. Use wildcards or regex for case-insensitive matching.",
	"Boolean operators must be <b>UPPERCASE</b>: <code>AND OR NOT</code> (lowercase is treated as a term).",
	"<b>Leading wildcards</b> (<code>*.org</code>) are disabled by default — expensive. Trailing is fine (<code>example*</code>).",
	"<code>message</code>, <code>full_message</code> and <code>source</code> are <b>analyzed</b> — regex &amp; exact matches don't work on them; parse into dedicated fields instead."
]

const sections: { title: string; items: { code: string; desc: string }[] }[] = [
	{
		title: "Terms & phrases",
		items: [
			{ code: "ssh", desc: "single term, matches anywhere" },
			{ code: "ssh login", desc: "two terms — OR by default (either)" },
			{ code: '"ssh login"', desc: "exact phrase, in order (case-sensitive)" }
		]
	},
	{
		title: "Boolean operators",
		items: [
			{ code: "type:ssh AND level:error", desc: "both required" },
			{ code: "+type:ssh +level:error", desc: "+ = required (alt for AND)" },
			{ code: "type:ssh OR type:login", desc: "either (default when no operator)" },
			{ code: "NOT source:test", desc: "exclude" },
			{ code: "-source:test", desc: "- = exclude (alt for NOT)" }
		]
	},
	{
		title: "Fields",
		items: [
			{ code: "field:value", desc: "search one field, e.g. type:ssh" },
			{ code: "type:(ssh OR login)", desc: "one field, multiple values" },
			{ code: "message:(failed AND auth)", desc: "both terms in same field" },
			{ code: "_exists_:user_id", desc: "field is present" },
			{ code: "NOT _exists_:user_id", desc: "field is absent" }
		]
	},
	{
		title: "Grouping",
		items: [
			{ code: "(a:1 OR b:2) AND c:3", desc: "control precedence" },
			{ code: "((x AND y) OR (p AND q)) AND s:prod*", desc: "nested grouping" }
		]
	},
	{
		title: "Wildcards",
		items: [
			{ code: "source:exam?le.org", desc: "? = exactly one character" },
			{ code: "source:example*", desc: "* = zero or more (trailing only)" },
			{ code: "source:exam?le.*", desc: "combine both" }
		]
	},
	{
		title: "Fuzzy & proximity",
		items: [
			{ code: "roam~", desc: "fuzzy — similar terms (edit distance)" },
			{ code: "roam~1", desc: "fuzzy with max 1 edit" },
			{ code: '"ssh login"~5', desc: "proximity — within 5 words, any order" }
		]
	},
	{
		title: "Ranges (numeric & date)",
		items: [
			{ code: "code:[400 TO 500]", desc: "inclusive range" },
			{ code: "code:{400 TO 500}", desc: "exclusive range" },
			{ code: "code:[400 TO 500}", desc: "mixed (incl 400, excl 500)" },
			{ code: "code:>=400", desc: "unbounded: > >= < <=" },
			{ code: 'ts:["2019-07-23 09:53:08.175" TO ...]', desc: "date range (UTC unless tz given)" },
			{ code: "otherDate:[now-5d TO now-4d]", desc: "relative date range" }
		]
	},
	{
		title: "Regex (non-analyzed fields only)",
		items: [
			{ code: "field:/.*value.*/", desc: "wrap pattern in slashes" },
			{ code: "user_name:/.*\\$/", desc: "ends with $ (e.g. machine accts)" }
		]
	},
	{
		title: "Handy examples",
		items: [
			{ code: "http_response_code:[400 TO 599]", desc: "all client + server errors" },
			{ code: 'level:error AND ("timeout" OR "out of memory")', desc: "errors of a kind" },
			{ code: "source:(web01 OR web02) AND http_response_code:>399", desc: "errors on specific hosts" }
		]
	}
]

const filteredSections = computed(() => {
	const q = filter.value.trim().toLowerCase()
	if (!q) return sections
	return sections
		.map(sec => ({
			title: sec.title,
			items: sec.items.filter(
				row =>
					row.code.toLowerCase().includes(q) ||
					row.desc.toLowerCase().includes(q) ||
					sec.title.toLowerCase().includes(q)
			)
		}))
		.filter(sec => sec.items.length > 0)
})
</script>
