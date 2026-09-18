import type { MaybeRefOrGetter } from "vue"
import type { OpenCTIObservableLookup } from "@/types/opencti"
import { computed, reactive, toValue, watch } from "vue"
import Api from "@/api"

/**
 * Per-IoC OpenCTI lookups, batched.
 *
 * An alert renders one IoC card per IoC and each asks for its own value. Asked
 * one by one, a 20-IoC alert would cost 20 OpenCTI queries. Instead, values
 * requested within `BATCH_DELAY_MS` of each other are collected and sent as a
 * single `POST /opencti/observables/lookup`, one GraphQL query server-side.
 *
 * Answers are cached per value (case-insensitively, as OpenCTI matches) for
 * `CACHE_TTL_MS`, so reopening an alert or showing the same IoC on two alerts
 * costs nothing. Failures are not cached: the next request retries.
 */

const BATCH_DELAY_MS = 50
/** Server-side caps: values per batch request, and characters per value. */
const MAX_BATCH = 100
const MAX_VALUE_LENGTH = 2048
const CACHE_TTL_MS = 10 * 60 * 1000

interface Entry {
	loading: boolean
	error: boolean
	result: OpenCTIObservableLookup | null
	/** 0 means "don't reuse", e.g. a "not found" from a truncated answer. */
	fetchedAt: number
}

const entries = reactive(new Map<string, Entry>())
const queue = new Map<string, string>()
let timer: ReturnType<typeof setTimeout> | null = null

function keyOf(value: string): string {
	return value.trim().toLowerCase()
}

function isFresh(entry: Entry | undefined): boolean {
	return !!entry && (entry.loading || (!entry.error && Date.now() - entry.fetchedAt < CACHE_TTL_MS))
}

function sendBatch(values: string[]) {
	Api.opencti
		.lookupObservables(values)
		.then(res => {
			const now = Date.now()
			for (const item of res.data.results) {
				entries.set(keyOf(item.value), {
					loading: false,
					error: false,
					result: {
						value: item.value,
						found: item.found,
						total: item.observables.length,
						observables: item.observables
					},
					// A "not found" from a truncated answer may be a false
					// negative, so it is shown but not reused.
					fetchedAt: res.data.truncated && !item.found ? 0 : now
				})
			}
			// Anything the server silently dropped (blank after trimming) settles
			// as not found rather than spinning forever.
			for (const value of values) {
				const entry = entries.get(keyOf(value))
				if (entry?.loading) {
					entries.set(keyOf(value), {
						loading: false,
						error: false,
						result: { value, found: false, total: 0, observables: [] },
						fetchedAt: 0
					})
				}
			}
		})
		.catch(() => {
			for (const value of values) {
				entries.set(keyOf(value), { loading: false, error: true, result: null, fetchedAt: 0 })
			}
		})
}

function flush() {
	timer = null
	const values = [...queue.values()]
	queue.clear()
	for (let i = 0; i < values.length; i += MAX_BATCH) {
		sendBatch(values.slice(i, i + MAX_BATCH))
	}
}

function request(value: string) {
	const key = keyOf(value)
	if (!key || isFresh(entries.get(key))) return

	// The server rejects a whole batch over one oversized value, which would
	// fail every other IoC on the alert with it. Settle it here instead.
	if (value.trim().length > MAX_VALUE_LENGTH) {
		entries.set(key, {
			loading: false,
			error: false,
			result: { value: value.trim(), found: false, total: 0, observables: [] },
			fetchedAt: Date.now()
		})
		return
	}

	entries.set(key, { loading: true, error: false, result: null, fetchedAt: 0 })
	queue.set(key, value.trim())
	timer ??= setTimeout(flush, BATCH_DELAY_MS)
}

/**
 * @param value The IoC value to look up.
 * @param enabled Only look up while this is true, e.g. while OpenCTI is available.
 */
export function useOpenCTIIocLookup(value: MaybeRefOrGetter<string>, enabled: MaybeRefOrGetter<boolean> = true) {
	watch(
		() => [toValue(value), toValue(enabled)] as const,
		([current, isEnabled]) => {
			if (isEnabled && current) request(current)
		},
		{ immediate: true }
	)

	const entry = computed(() => entries.get(keyOf(toValue(value))))

	return {
		loading: computed(() => entry.value?.loading ?? false),
		error: computed(() => entry.value?.error ?? false),
		result: computed(() => entry.value?.result ?? null),
		/** Retry after an error. */
		retry: () => request(toValue(value))
	}
}

/** Test hook: forget every cached answer and pending request. */
export function resetOpenCTIIocLookupCache() {
	entries.clear()
	queue.clear()
	if (timer) clearTimeout(timer)
	timer = null
}
