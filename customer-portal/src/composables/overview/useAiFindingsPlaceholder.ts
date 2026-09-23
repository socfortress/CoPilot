import type { Ref } from "vue"
import type { AiInsights } from "@/types/aiReports"
import { useSessionStorage } from "@vueuse/core"
import { computed, watch } from "vue"

/**
 * Decides whether the AI findings card is on the page, and how big its placeholder is.
 *
 * The card only exists when the SOC has published findings, which is unknown until
 * the first response. Rendering it only then pushes the whole activity area down;
 * always rendering a placeholder makes it collapse for customers without AI. So the
 * page remembers, per session, how many findings the card last showed and reserves
 * exactly that space while loading.
 */
export function useAiFindingsPlaceholder(options: {
	insights: Ref<AiInsights>
	/** `true` once the first load has settled. */
	loaded: Ref<boolean>
	failed: () => boolean
}) {
	const { insights, loaded, failed } = options
	const lastRowCount = useSessionStorage("overview.ai-findings-rows", 0)

	const visible = computed(() => {
		if (failed()) return false
		return loaded.value ? insights.value.total_reports > 0 : lastRowCount.value > 0
	})

	/** Refreshed on every completed load, including refreshes and filter changes. */
	watch([loaded, insights], ([isLoaded, current]) => {
		if (!isLoaded || failed()) return
		lastRowCount.value = current.total_reports > 0 ? current.recent.length : 0
	})

	return {
		visible,
		skeletonRows: computed(() => lastRowCount.value || undefined)
	}
}
