import type { Ref } from "vue"
import type { VulnerabilityState } from "./exposure"
import type { ApiError } from "@/types/common"
import type { ExposureCompliance, ExposureVulnerabilities } from "@/types/exposure"
import { ref, watch } from "vue"
import Api from "@/api"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { i18nGlobal } from "@/lang"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"
import { PAGE_SIZE } from "./exposure"

/**
 * The Exposure page's data (#1289), one composable per tab: a load per filter or customer
 * filter change, only the latest one counting (`useLatestRequest`), the previous figures kept
 * on screen while the next ones load.
 */

export function useExposureVulnerabilities(state: Ref<VulnerabilityState>) {
	const customerFilterStore = useCustomerFilterStore()
	const data = ref<ExposureVulnerabilities | null>(null)
	const error = ref<string | null>(null)
	const { loading, run } = useLatestRequest()

	function load() {
		const { severity, search, page } = state.value
		return run(
			async signal => {
				const response = await Api.exposure.getVulnerabilities(
					{ severity, search, page, pageSize: PAGE_SIZE },
					customerFilterStore.queryCustomerCodes,
					signal
				)
				if (signal.aborted) return
				data.value = response.data
				error.value = null
			},
			err => {
				error.value = getApiErrorMessage(err as ApiError) || i18nGlobal.t("exposure.vulnerabilities.loadFailed")
			}
		)
	}

	// The store replaces the selection array on every change: no deep watch needed.
	watch(
		[
			() => state.value.severity,
			() => state.value.search,
			() => state.value.page,
			() => customerFilterStore.queryCustomerCodes
		],
		load,
		{ immediate: true }
	)

	return { data, error, loading, reload: load }
}

export function useExposureCompliance() {
	const customerFilterStore = useCustomerFilterStore()
	const data = ref<ExposureCompliance | null>(null)
	const error = ref<string | null>(null)
	const { loading, run } = useLatestRequest()

	function load() {
		return run(
			async signal => {
				const response = await Api.exposure.getCompliance(customerFilterStore.queryCustomerCodes, signal)
				if (signal.aborted) return
				data.value = response.data
				error.value = null
			},
			err => {
				error.value = getApiErrorMessage(err as ApiError) || i18nGlobal.t("exposure.compliance.loadFailed")
			}
		)
	}

	watch(() => customerFilterStore.queryCustomerCodes, load, { immediate: true })

	return { data, error, loading, reload: load }
}
