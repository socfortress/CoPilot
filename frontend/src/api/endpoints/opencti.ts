import type { FlaskBaseResponse } from "@/types/flask"
import type {
	OpenCTIAbout,
	OpenCTIAvailability,
	OpenCTIBatchLookup,
	OpenCTIEntity,
	OpenCTIIndicator,
	OpenCTIIndicatorsQuery,
	OpenCTIObservableLookup,
	OpenCTIPageInfo
} from "@/types/opencti"
import { HttpClient } from "../http-client"

export default {
	/**
	 * Whether the OpenCTI connector is configured and verified. Reads the connector row only.
	 *
	 * Session-scoped gating, like the licence lookup: an abort on navigation would
	 * be read as "unavailable" and hide OpenCTI (the navbar drawer never asks again).
	 */
	getAvailability() {
		return HttpClient.get<FlaskBaseResponse & OpenCTIAvailability>(`/opencti/availability`, {
			keepOnNavigation: true
		})
	},
	getAbout(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { about: OpenCTIAbout }>(`/opencti/about`, { signal })
	},
	/** Exact-value IOC lookup: IP, domain, hostname, URL, email or file hash. */
	lookupObservable(value: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & OpenCTIObservableLookup>(`/opencti/observables/search`, {
			params: { value },
			signal
		})
	},
	/** Many exact-value IOC lookups in one OpenCTI query (max 100 values). */
	lookupObservables(values: string[]) {
		return HttpClient.post<FlaskBaseResponse & OpenCTIBatchLookup>(`/opencti/observables/lookup`, { values })
	},
	getIndicators(query: OpenCTIIndicatorsQuery = {}, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { indicators: OpenCTIIndicator[]; page_info: OpenCTIPageInfo }>(
			`/opencti/indicators`,
			{ params: query, signal }
		)
	},
	/** Any STIX core object, by OpenCTI internal id or STIX standard_id. */
	getEntity(entityId: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { entity: OpenCTIEntity }>(
			`/opencti/entities/${encodeURIComponent(entityId)}`,
			{ signal }
		)
	}
}
