/**
 * Per-viewer conveniences of a customer's page (#1325): the pinned sections, per username, and
 * whether the section rail is hidden, for this browser. localStorage only: a private window or
 * blocked storage just starts from nothing pinned and the rail shown.
 */
import type { SectionId } from "./sections"
import { computed, ref, watch } from "vue"
import { useAuthStore } from "@/stores/auth"
import { isSectionId } from "./sections"

export const PINNED_KEY_PREFIX = "copilot.customer.sections.pinned."
export const RAIL_HIDDEN_KEY = "copilot.customer.sections.railHidden"
export const MAX_PINNED = 12

function readPinned(username: string): SectionId[] {
	try {
		const parsed: unknown = JSON.parse(localStorage.getItem(PINNED_KEY_PREFIX + username) || "[]")
		if (!Array.isArray(parsed)) return []
		const ids = parsed.filter((id): id is SectionId => typeof id === "string" && isSectionId(id))
		return [...new Set(ids)].slice(0, MAX_PINNED)
	} catch {
		return []
	}
}

function writePinned(username: string, ids: SectionId[]) {
	try {
		localStorage.setItem(PINNED_KEY_PREFIX + username, JSON.stringify(ids))
	} catch {
		// Storage refused: the pin lasts for this page only.
	}
}

function readRailHidden(): boolean {
	try {
		return localStorage.getItem(RAIL_HIDDEN_KEY) === "true"
	} catch {
		return false
	}
}

export function useSectionPreferences() {
	const authStore = useAuthStore()
	const username = computed(() => authStore.userName || "")

	const pinned = ref<SectionId[]>(readPinned(username.value))
	watch(username, name => {
		pinned.value = readPinned(name)
	})

	function isPinned(id: SectionId): boolean {
		return pinned.value.includes(id)
	}

	function togglePin(id: SectionId) {
		pinned.value = isPinned(id)
			? pinned.value.filter(item => item !== id)
			: [...pinned.value, id].slice(-MAX_PINNED)
		writePinned(username.value, pinned.value)
	}

	const railHidden = ref(readRailHidden())

	function setRailHidden(hidden: boolean) {
		railHidden.value = hidden
		try {
			localStorage.setItem(RAIL_HIDDEN_KEY, String(hidden))
		} catch {
			// Storage refused: the choice lasts for this page only.
		}
	}

	return { pinned, isPinned, togglePin, railHidden, setRailHidden }
}
