import type { SelectOption } from "naive-ui"
import type { RuleCategory } from "@/types/copilot-searches"
import { computed, h, ref } from "vue"
import Api from "@/api"

/**
 * Detection categories — the `detections/<folder>` layout of the
 * CoPilot-Search-Queries repo, exposed as filter options.
 *
 * State is module-level on purpose: the list is derived from the backend rules
 * cache and only moves when the repo does, so the Grid and Matrix toolbars share
 * a single fetch instead of one each. Concurrent callers await the same promise.
 */
const categories = ref<RuleCategory[]>([])
const loading = ref(false)
let inflight: Promise<void> | null = null

function fetchCategories(): Promise<void> {
	if (inflight) return inflight

	loading.value = true
	inflight = Api.copilotSearches
		.getCategories()
		.then(res => {
			if (res.data.success) {
				categories.value = res.data.categories || []
			}
		})
		.catch(() => {
			// Silent — the filter simply has no options. Everything else on the
			// page keeps working, which beats an error toast on mount.
		})
		.finally(() => {
			loading.value = false
			inflight = null
		})

	return inflight
}

export function useDetectionCategories() {
	/**
	 * Naive UI select options, bucketed by the backend-provided `group`
	 * (Sysmon, Windows Event Logs, PowerShell, Linux, Microsoft 365, Other).
	 * Backend order is preserved — it already sorts group-first, count-desc.
	 */
	const options = computed<SelectOption[]>(() => {
		const groups: { label: string; children: SelectOption[] }[] = []

		for (const category of categories.value) {
			let group = groups.find(g => g.label === category.group)
			if (!group) {
				group = { label: category.group, children: [] }
				groups.push(group)
			}
			group.children.push({
				label: category.label,
				value: category.value,
				count: category.count
			})
		}

		return groups.map(group => ({
			type: "group",
			key: group.label,
			label: group.label,
			children: group.children
		}))
	})

	/** Renders the rule count alongside each option label. */
	function renderLabel(option: SelectOption) {
		if (option.type === "group") return String(option.label ?? "")

		return h("div", { class: "flex items-center justify-between gap-4" }, [
			h("span", String(option.label ?? "")),
			h("span", { class: "text-tertiary text-xs" }, String(option.count ?? ""))
		])
	}

	function load() {
		if (categories.value.length) return Promise.resolve()
		return fetchCategories()
	}

	/** Force a re-fetch — used after the rules cache is manually refreshed. */
	function reload() {
		return fetchCategories()
	}

	return {
		categories,
		loading,
		options,
		renderLabel,
		load,
		reload
	}
}
