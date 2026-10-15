import type { MaybeRefOrGetter, Ref } from "vue"
import type { EventSearchMemory, QueryState } from "./eventSearchMemory"
import type { DisplayColumn } from "@/types/siem"
import { computed, ref, toValue } from "vue"
import { useAuthStore } from "@/stores/auth"
import { secureLocalStorage } from "@/utils/secure-storage"
import {
	clearRecent,
	deleteQuery,
	emptyMemory,
	memoryKey,
	normalizeMemory,
	rememberRecent,
	saveQuery,
	setColumns
} from "./eventSearchMemory"

export interface MemoryStorage {
	getItem: (key: string) => unknown
	setItem: (key: string, value: string) => void
}

// One state per storage key, shared by every component that asks for it: the search form
// (saved and recent queries) and the results (columns) always see the same memory.
const states = new Map<string, Ref<EventSearchMemory>>()

/** Forgets the in-memory copies (tests; the stored data is untouched). */
export function resetEventSearchMemoryCache() {
	states.clear()
}

/**
 * Event search's memory for the signed-in user and `customerCode` (#1258), kept in this
 * browser, encrypted (queries can name hosts, users and addresses) and keyed per user and
 * customer, so another user of the same browser never sees it.
 */
export function useEventSearchMemory(
	customerCode: MaybeRefOrGetter<string | null | undefined>,
	storage: MemoryStorage = secureLocalStorage()
) {
	const authStore = useAuthStore()
	const key = computed(() => {
		const code = toValue(customerCode)
		return authStore.userName && code ? memoryKey(authStore.userName, code) : null
	})
	const fallback = ref(emptyMemory())

	function stateFor(storageKey: string | null): Ref<EventSearchMemory> {
		if (!storageKey) return fallback
		let state = states.get(storageKey)
		if (!state) {
			state = ref(normalizeMemory(storage.getItem(storageKey)))
			states.set(storageKey, state)
		}
		return state
	}

	const memory = computed(() => stateFor(key.value).value)

	function commit(next: EventSearchMemory) {
		if (!key.value) return
		stateFor(key.value).value = next
		storage.setItem(key.value, JSON.stringify(next))
	}

	return {
		memory,
		/** Whether anything can be remembered: a signed-in user and a customer. */
		available: computed(() => !!key.value),
		save(name: string, state: QueryState) {
			const result = saveQuery(memory.value, name, state, Date.now())
			commit(result.memory)
			return result.replaced
		},
		remove(id: string) {
			commit(deleteQuery(memory.value, id))
		},
		remember(state: QueryState) {
			commit(rememberRecent(memory.value, state, Date.now()))
		},
		clearRecent() {
			commit(clearRecent(memory.value))
		},
		columnsFor(sourceName: string | null | undefined): DisplayColumn[] | null {
			return (sourceName && memory.value.columns[sourceName]) || null
		},
		setColumns(sourceName: string, columns: DisplayColumn[] | null) {
			commit(setColumns(memory.value, sourceName, columns))
		}
	}
}
