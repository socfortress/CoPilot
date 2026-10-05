import type { LocationQueryRaw } from "vue-router"
import type { PeriodPreset, PeriodRange } from "../utils"
import type { SocDashboardQuery } from "@/api/endpoints/soc-management"
import type { Severity } from "@/types/soc-management"
import { computed, shallowRef } from "vue"
import { useRoute, useRouter } from "vue-router"
import { isValidRange, PERIOD_PRESETS, presetRange, SEVERITIES } from "../utils"

export const SOC_TABS = ["overview", "sla", "analysts", "rules", "customers", "workload", "policies"] as const
export type SocTab = (typeof SOC_TABS)[number]

const DEFAULT_PRESET = "30d" as const

function list(raw: unknown): string[] {
	const values = Array.isArray(raw) ? raw : raw == null ? [] : [raw]
	return values.filter((value): value is string => typeof value === "string" && value.length > 0)
}

function parseDate(raw: unknown): Date | null {
	const value = list(raw)[0]
	if (!value) return null
	const date = new Date(value)
	return Number.isNaN(date.getTime()) ? null : date
}

/**
 * The SOC Management page's filters, kept in the URL so a view can be linked and
 * survives a reload. Every change *refines* the page, so it is a `replace`, never a
 * new history entry.
 *
 * `?period=7d` for a rolling window, `?period=custom&from=…&to=…` for a fixed one.
 */
export function useSocFilters() {
	const route = useRoute()
	const router = useRouter()

	/** Bumped by `refresh()`: a rolling window ends "now", and now moves. */
	const tick = shallowRef(0)

	/**
	 * The query of a navigation still in flight. `route.query` only moves once the
	 * navigation settles, so two changes made in one go (a customer, then the tab) would
	 * each start from the old query and the second would drop the first.
	 */
	let pending: LocationQueryRaw | null = null

	function patch(query: Record<string, string | string[] | undefined>) {
		const next = { ...(pending ?? route.query), ...query }
		pending = next
		router.replace({ query: next }).finally(() => {
			if (pending === next) pending = null
		})
	}

	const tab = computed<SocTab>({
		get: () => {
			const value = list(route.query.tab)[0]
			return (SOC_TABS as readonly string[]).includes(value ?? "") ? (value as SocTab) : "overview"
		},
		set: value => patch({ tab: value })
	})

	const customRange = computed<PeriodRange | null>(() => {
		const range = { from: parseDate(route.query.from), to: parseDate(route.query.to) }
		return range.from && range.to && isValidRange(range as PeriodRange) ? (range as PeriodRange) : null
	})

	const preset = computed<PeriodPreset>({
		get: () => {
			const value = list(route.query.period)[0]
			if (value === "custom" && customRange.value) return "custom"
			return PERIOD_PRESETS.some(p => p.key === value) ? (value as PeriodPreset) : DEFAULT_PRESET
		},
		set: value => patch({ period: value, ...(value === "custom" ? {} : { from: undefined, to: undefined }) })
	})

	function setCustomRange(range: PeriodRange) {
		if (!isValidRange(range)) return
		patch({ period: "custom", from: range.from.toISOString(), to: range.to.toISOString() })
	}

	const range = computed<PeriodRange>(() => {
		void tick.value
		const current = preset.value
		if (current === "custom") return customRange.value ?? presetRange(DEFAULT_PRESET)
		return presetRange(current)
	})

	const severities = computed<Severity[]>({
		get: () =>
			list(route.query.severity).filter((value): value is Severity => (SEVERITIES as string[]).includes(value)),
		set: value => patch({ severity: value.length ? value : undefined })
	})

	const sources = computed<string[]>({
		get: () => list(route.query.source),
		set: value => patch({ source: value.length ? value : undefined })
	})

	const customerCodes = computed<string[]>({
		get: () => list(route.query.customer),
		set: value => patch({ customer: value.length ? value : undefined })
	})

	const hasCustomerInUrl = computed(() => list(route.query.customer).length > 0)

	const query = computed<SocDashboardQuery>(() => ({
		dateFrom: range.value.from,
		dateTo: range.value.to,
		customerCodes: customerCodes.value,
		severities: severities.value,
		sources: sources.value
	}))

	function refresh() {
		tick.value++
	}

	return {
		tab,
		preset,
		customRange,
		setCustomRange,
		range,
		severities,
		sources,
		customerCodes,
		hasCustomerInUrl,
		query,
		refresh
	}
}

export type SocFilters = ReturnType<typeof useSocFilters>
