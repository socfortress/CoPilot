import type { QuestionEntity } from "@/components/incidentManagement/customerQuestions/customerQuestions"
import type { SocRequest } from "@/types/soc-requests"
import { readonly, ref } from "vue"
import Api from "@/api"
import { openCount } from "@/components/incidentManagement/customerQuestions/customerQuestions"

/**
 * The open customer questions (#1305) of the caller's customers, shared by every case and alert row
 * that shows a "Customer question" badge: one request for a whole list, read again after
 * `STALE_MS` or when a question is answered (`invalidate`). A failure shows no badge and is retried
 * on the next read. Reset at logout: the next analyst may see other customers.
 */
const STALE_MS = 60_000

const open = ref<SocRequest[]>([])
let loadedAt = 0
let inflight: Promise<void> | null = null

async function load(): Promise<void> {
	try {
		const res = await Api.socRequests.list({ status: "open" })
		open.value = res.data.requests ?? []
		loadedAt = Date.now()
	} catch {
		// No badge rather than an error on every row; the next read tries again.
		loadedAt = 0
	} finally {
		inflight = null
	}
}

export function useOpenCustomerQuestions() {
	function ensure(): Promise<void> {
		if (inflight) return inflight
		if (loadedAt && Date.now() - loadedAt < STALE_MS) return Promise.resolve()
		inflight = load()
		return inflight
	}

	function countFor(entity: QuestionEntity, id: number): number {
		return openCount(open.value, entity, id)
	}

	function invalidate() {
		loadedAt = 0
		return ensure()
	}

	return { open: readonly(open), ensure, countFor, invalidate }
}

export function resetOpenCustomerQuestions() {
	open.value = []
	loadedAt = 0
	inflight = null
}
