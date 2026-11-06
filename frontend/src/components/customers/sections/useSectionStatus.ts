/**
 * What each section of a customer's page holds, for the navigation's lights (#1325).
 *
 * One request (`GET /customers/{code}/sections/status`), read again when the customer changes, when
 * the viewer leaves a section (a switch may have moved there), and through `refresh` when a section
 * changes its own count while it stays open. A newer read aborts the one in flight; a failure leaves
 * the lights off rather than wrong, and tells no one: the sections work without them.
 */
import type { MaybeRefOrGetter } from "vue"
import type { CustomerSectionStatus } from "@/types/customers"
import axios from "axios"
import { onScopeDispose, ref, toValue, watch } from "vue"
import Api from "@/api"

export function useSectionStatus(customerCode: MaybeRefOrGetter<string>) {
	const status = ref<CustomerSectionStatus | null>(null)
	let controller: AbortController | null = null

	async function refresh() {
		const code = toValue(customerCode)
		controller?.abort()
		if (!code) {
			status.value = null
			return
		}
		const current = new AbortController()
		controller = current
		try {
			const res = await Api.customers.getCustomerSectionStatus(code, current.signal)
			if (controller !== current) return
			status.value = res.data.success && res.data.customer_code === code ? res.data.sections : null
		} catch (err) {
			if (axios.isCancel(err) || controller !== current) return
			status.value = null
		}
	}

	watch(
		() => toValue(customerCode),
		() => {
			status.value = null
			void refresh()
		},
		{ immediate: true }
	)

	onScopeDispose(() => controller?.abort())

	return { status, refresh }
}
