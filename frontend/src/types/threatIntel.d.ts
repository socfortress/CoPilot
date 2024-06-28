export interface ThreatIntelResponse {
	comment: string | null
	ioc_source: string
	report_url: string | null
	score: string | null
	timestamp: string | null
	type: string | null
	value: string | null
	virustotal_url: string | null
}

export interface EpssScore {
	cve: string
	/** a float (0.000680000) */
	epss: string
	/** a float (0.299330000) */
	percentile: string
	/** a date (2024-06-27) */
	date: string | Date
}

export interface EvaluationData {
	rank: number
	host_prev: string
	eps: string
	paths: EvaluationDataPath[]
	parents: EvaluationDataParent[]
	hashes: EvaluationDataHash[]
	network: EvaluationDataNetwork[]
	description: string
	intel: string
	/** ignore */
	truncated: EvaluationDataTruncated
	/** ignore */
	tags: EvaluationDataTag[]
}

export interface EvaluationDataHash {
	hash: string
	percentage: number
}

export interface EvaluationDataNetwork {
	port: string
	/** percentage */
	usage: number
}

export interface EvaluationDataParent {
	name: string
	percentage: number
}

export interface EvaluationDataPath {
	directory: string
	percentage: number
}

export interface EvaluationDataTag {
	category: string
	type: string
	description: string
	field4: string
	field5: string
	color: string
}

export interface EvaluationDataTruncated {
	paths: number
	parents: number
	grandparents: number
	children: number
	network: number
	hashes: number
}
