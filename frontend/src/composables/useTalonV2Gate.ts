import type { MaybeRefOrGetter } from "vue"
import { computed, toValue, watch } from "vue"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { ensureTalonV2Availability, talonV2AvailabilityState } from "./useTalonV2Availability"

/** The roles talon-analyst's v2 serves (CoPilot's v2 routes are admin/analyst; a responder's token carries analyst). */
const TALON_V2_ROLES: ReadonlySet<AuthUserRole> = new Set([
	AuthUserRole.Admin,
	AuthUserRole.Analyst,
	AuthUserRole.Responder
])

export function talonV2RoleAllowed(): boolean {
	return TALON_V2_ROLES.has(useAuthStore().userRole)
}

/**
 * The "Talon v2" availability for a surface that only sometimes shows a v2 view (the alert's AI
 * panel with a report, the job page but not its embedded rows): `GET /talon/v2/availability` is
 * asked for only once `when` holds *and* the user's role could use v2, so a scheduler, a portal
 * user or a list of embedded rows never asks. Otherwise the shared, session-cached answer.
 */
export function useTalonV2AvailabilityWhen(when: MaybeRefOrGetter<boolean>) {
	const wanted = computed(() => toValue(when) && talonV2RoleAllowed())
	const state = talonV2AvailabilityState()
	watch(
		wanted,
		on => {
			if (on) ensureTalonV2Availability()
		},
		{ immediate: true }
	)
	return {
		available: computed(() => wanted.value && state.available.value),
		runView: computed(() => wanted.value && state.runView.value)
	}
}
