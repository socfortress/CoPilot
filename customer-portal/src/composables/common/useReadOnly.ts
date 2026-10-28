import type { MaybeRefOrGetter } from "vue"
import { computed, toValue } from "vue"
import { useAuthStore } from "@/stores/auth"

/**
 * Whether the user may only read this customer's data (#1312): a control that would change it is
 * disabled or not offered. The server refuses the write anyway; this keeps the user from trying.
 */
export function useReadOnly(customerCode: MaybeRefOrGetter<string | null | undefined>) {
	const authStore = useAuthStore()
	return computed(() => authStore.isReadOnlyFor(toValue(customerCode)))
}
