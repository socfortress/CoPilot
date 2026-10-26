import type { AxiosResponse } from "axios"
import type { MaybeRefOrGetter, Ref } from "vue"
import type { ApiError, CommonResponse } from "@/types/common"
import type { DisplayColumn, EventSearchColumnTemplate, EventSearchMemory, EventSearchState } from "@/types/siem"
import { computed, ref, toValue, watch } from "vue"
import Api from "@/api"
import { i18nGlobal } from "@/lang"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"
import { emptyMemory } from "./eventSearchMemory"

interface Entry {
	memory: Ref<EventSearchMemory>
	status: Ref<"idle" | "loading" | "ready" | "error">
	error: Ref<string | null>
	pending?: Promise<void>
	/** The last request whose answer was taken: an older answer arriving late is dropped. */
	applied: number
}

function newEntry(): Entry {
	return { memory: ref(emptyMemory()), status: ref("idle"), error: ref(null), applied: 0 }
}

// One entry per user and customer, shared by every component that asks: the search form
// (saved and recent searches) and the results (columns) always show the same memory.
const entries = new Map<string, Entry>()
let sequence = 0

/** Forgets every copy: called on logout, so the next user of the browser starts clean. */
export function resetEventSearchMemory() {
	entries.clear()
}

function memoryOf(data: EventSearchMemory): EventSearchMemory {
	return { saved: data.saved, recent: data.recent, columns: data.columns, templates: data.templates ?? [] }
}

/**
 * Event search's memory for the signed-in user and `customerCode` (#1258), kept on the
 * server so the user finds it on any device. Loaded once per user and customer; every
 * write answers with the whole memory, which replaces the copy.
 */
export function useEventSearchMemory(customerCode: MaybeRefOrGetter<string | null | undefined>) {
	const authStore = useAuthStore()
	const code = computed(() => toValue(customerCode) || null)
	const key = computed(() => (authStore.userName && code.value ? `${authStore.userName}:${code.value}` : null))
	const fallback = newEntry()

	function entryFor(storageKey: string | null): Entry {
		if (!storageKey) return fallback
		let entry = entries.get(storageKey)
		if (!entry) {
			entry = newEntry()
			entries.set(storageKey, entry)
		}
		return entry
	}

	const entry = computed(() => entryFor(key.value))

	function load(force = false): Promise<void> {
		const customer = code.value
		const target = entryFor(key.value)
		if (!customer || target === fallback) return Promise.resolve()
		if (target.pending) return target.pending
		if (!force && target.status.value === "ready") return Promise.resolve()

		const ticket = ++sequence
		target.status.value = "loading"
		target.error.value = null
		target.pending = (async () => {
			try {
				const response = await Api.siem.getEventSearchMemory(customer)
				if (ticket > target.applied) {
					target.applied = ticket
					target.memory.value = memoryOf(response.data)
				}
				target.status.value = "ready"
			} catch (err) {
				target.error.value = getApiErrorMessage(err as ApiError) || i18nGlobal.t("eventSearch.queries.loadFailed")
				target.status.value = "error"
			} finally {
				target.pending = undefined
			}
		})()
		return target.pending
	}

	watch(key, () => load(), { immediate: true })

	async function write<T extends EventSearchMemory>(
		request: (customer: string) => Promise<AxiosResponse<CommonResponse<T>>>
	): Promise<T> {
		const customer = code.value
		const target = entryFor(key.value)
		if (!customer || target === fallback) throw new Error("Select a customer first")
		const ticket = ++sequence
		const response = await request(customer)
		if (ticket > target.applied) {
			target.applied = ticket
			target.memory.value = memoryOf(response.data)
			target.status.value = "ready"
		}
		return response.data
	}

	const memory = computed(() => entry.value.memory.value)

	return {
		memory,
		loading: computed(() => entry.value.status.value === "loading"),
		/** Why the memory could not be read, if it could not. */
		error: computed(() => entry.value.error.value),
		/** Whether anything can be remembered: a signed-in user and a customer. */
		available: computed(() => !!key.value),
		reload: () => load(true),
		/** Saves the search under `name`; true when a query of that name was updated. */
		async save(name: string, state: EventSearchState): Promise<boolean> {
			const data = await write(customer => Api.siem.saveEventSearchQuery(customer, name, state))
			return !!data.replaced
		},
		async remove(id: number) {
			await write(customer => Api.siem.deleteEventSearchQuery(customer, id))
		},
		/** Records a search just run. Never in the user's way: a failure is only logged. */
		async remember(state: EventSearchState) {
			try {
				await write(customer => Api.siem.rememberEventSearch(customer, state))
			} catch (err) {
				console.warn("[event search] could not record the search", err)
			}
		},
		async clearRecent() {
			await write(customer => Api.siem.clearEventSearchRecent(customer))
		},
		columnsFor(sourceName: string | null | undefined): DisplayColumn[] | null {
			return (sourceName && memory.value.columns[sourceName]) || null
		},
		async setColumns(sourceName: string, columns: DisplayColumn[] | null) {
			await write(customer => Api.siem.setEventSearchColumns(customer, sourceName, columns))
		},
		templatesFor(sourceName: string | null | undefined): EventSearchColumnTemplate[] {
			return sourceName ? memory.value.templates.filter(template => template.source_name === sourceName) : []
		},
		/** Saves a named column set for a source; true when a template of that name was updated. */
		async saveTemplate(sourceName: string, name: string, columns: DisplayColumn[]): Promise<boolean> {
			const data = await write(customer => Api.siem.saveEventSearchTemplate(customer, sourceName, name, columns))
			return !!data.replaced
		},
		async removeTemplate(id: number) {
			await write(customer => Api.siem.deleteEventSearchTemplate(customer, id))
		}
	}
}
