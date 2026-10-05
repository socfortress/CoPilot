import type { Ref } from "vue"
import type { EditableCalendar } from "../policies/calendar"
import type { CalendarResponse, CalendarSource } from "@/types/soc-management"
import { computed, ref, shallowRef, watch } from "vue"
import Api from "@/api"
import { buildCalendarPayload, calendarError, isCalendarDirty, toEditableCalendar } from "../policies/calendar"

function errorText(err: unknown) {
	const e = err as { response?: { data?: { detail?: string; message?: string } }; message?: string }
	return e?.response?.data?.detail ?? e?.response?.data?.message ?? e?.message ?? "unknown error"
}

/**
 * The business-hours calendar of one scope (global when `scope` is null), as the
 * editor holds it: what is stored, the working copy, and the three writes.
 *
 * Reloads whenever the scope changes; a load that a newer one superseded is ignored.
 * Writes report through the returned message rather than a toast so the caller
 * decides how to say it.
 */
export function useBusinessCalendar(scope: Ref<string | null>) {
	const original = shallowRef<EditableCalendar | null>(null)
	// Deep, unlike the rest: the editor binds straight into its days and holidays.
	const draft = ref<EditableCalendar | null>(null)
	const source = shallowRef<CalendarSource>("default")
	const customersWithCalendar = shallowRef<string[]>([])
	const loading = shallowRef(false)
	const saving = shallowRef(false)
	const loadError = shallowRef<string | null>(null)
	let generation = 0

	const dirty = computed(() => !!draft.value && !!original.value && isCalendarDirty(draft.value, original.value))
	const error = computed(() => (draft.value ? calendarError(draft.value) : null))
	/** A customer scope has a calendar of its own (rather than following the global one). */
	const hasOwn = computed(() => !!scope.value && source.value === "customer")

	function accept(response: CalendarResponse) {
		original.value = toEditableCalendar(response.calendar)
		draft.value = toEditableCalendar(response.calendar)
		source.value = response.calendar.source
		customersWithCalendar.value = response.customers_with_calendar
	}

	async function load() {
		const mine = ++generation
		loading.value = true
		loadError.value = null
		try {
			const response = await Api.socManagement.getCalendar(scope.value)
			if (mine === generation) accept(response.data)
		} catch (err) {
			if (mine === generation) loadError.value = errorText(err)
		} finally {
			if (mine === generation) loading.value = false
		}
	}

	async function save(applyToOpen: boolean): Promise<{ ok: boolean; message: string }> {
		if (!draft.value) return { ok: false, message: "Nothing to save" }
		saving.value = true
		try {
			const response = await Api.socManagement.saveCalendar(
				buildCalendarPayload(draft.value, scope.value, applyToOpen)
			)
			accept(response.data)
			return { ok: true, message: response.data.message || "Calendar saved" }
		} catch (err) {
			return { ok: false, message: `Could not save the calendar: ${errorText(err)}` }
		} finally {
			saving.value = false
		}
	}

	async function remove(applyToOpen: boolean): Promise<{ ok: boolean; message: string }> {
		if (!scope.value) return { ok: false, message: "The global calendar cannot be removed" }
		saving.value = true
		try {
			const response = await Api.socManagement.deleteCalendar(scope.value, applyToOpen)
			accept(response.data)
			return { ok: true, message: response.data.message || "Calendar removed" }
		} catch (err) {
			return { ok: false, message: `Could not remove the calendar: ${errorText(err)}` }
		} finally {
			saving.value = false
		}
	}

	function discard() {
		if (original.value) draft.value = toEditableCalendar(original.value)
	}

	watch(scope, load, { immediate: true })

	return {
		original,
		draft,
		source,
		customersWithCalendar,
		loading,
		saving,
		loadError,
		dirty,
		error,
		hasOwn,
		load,
		save,
		remove,
		discard
	}
}
