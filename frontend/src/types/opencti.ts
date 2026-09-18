// Mirrors backend/app/connectors/opencti/schema/opencti.py. The backend already
// flattens OpenCTI's GraphQL shapes (edges/node, objectLabel, createdBy{name}),
// so these are plain records.

export interface OpenCTILabel {
	value: string
	color: string | null
}

export interface OpenCTIObjectMeta {
	id: string
	standard_id: string | null
	entity_type: string
	created_at: string | null
	updated_at: string | null
	created_by: string | null
	labels: OpenCTILabel[]
	/** Marking definitions, e.g. "TLP:CLEAR" */
	markings: string[]
}

export interface OpenCTIIndicator extends OpenCTIObjectMeta {
	name: string | null
	description: string | null
	pattern: string | null
	pattern_type: string | null
	main_observable_type: string | null
	score: number | null
	confidence: number | null
	valid_from: string | null
	valid_until: string | null
	revoked: boolean | null
}

export interface OpenCTIHash {
	algorithm: string
	hash: string
}

export interface OpenCTIReportRef {
	id: string
	name: string | null
	published: string | null
}

export interface OpenCTIObservable extends OpenCTIObjectMeta {
	value: string | null
	description: string | null
	score: number | null
	file_name: string | null
	hashes: OpenCTIHash[]
	indicators: OpenCTIIndicator[]
	indicators_count: number
	reports: OpenCTIReportRef[]
	reports_count: number
}

export interface OpenCTIExternalReference {
	source_name: string | null
	url: string | null
	external_id: string | null
	description: string | null
}

export interface OpenCTIEntity extends OpenCTIObjectMeta {
	parent_types: string[]
	name: string | null
	description: string | null
	confidence: number | null
	score: number | null
	external_references: OpenCTIExternalReference[]
}

export interface OpenCTIAbout {
	version: string | null
	dependencies: { name: string; version: string | null }[]
	user_name: string | null
	user_email: string | null
}

export interface OpenCTIPageInfo {
	global_count: number | null
	has_next_page: boolean
	end_cursor: string | null
}

export interface OpenCTIAvailability {
	configured: boolean
	verified: boolean
	/** OpenCTI's web address, only set once verified. Links use `${platform_url}/dashboard/id/${id}`. */
	platform_url: string | null
}

export interface OpenCTIObservableLookup {
	value: string
	found: boolean
	total: number
	observables: OpenCTIObservable[]
}

export interface OpenCTIValueLookup {
	value: string
	found: boolean
	observables: OpenCTIObservable[]
}

export interface OpenCTIBatchLookup {
	/** One entry per requested value, in request order. */
	results: OpenCTIValueLookup[]
	/** OpenCTI matched more than one query returns; a "not found" may be a false negative. */
	truncated: boolean
}

export interface OpenCTIIndicatorsQuery {
	search?: string
	first?: number
	after?: string
	min_score?: number
	main_observable_type?: string
}
