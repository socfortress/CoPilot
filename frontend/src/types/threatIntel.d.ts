import type { SafeAny } from "./common"

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

export interface StructuredAgentResponse {
	response: string
	thinking_process: string | null
}

export interface MCPQueryResponse {
	message: string
	success: boolean
	result?: SafeAny
	structured_result?: StructuredAgentResponse
	execution_time?: number
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

export interface AiAnalysisResponse {
	analysis: string
	base64_decoded: string
	confidence_score: number
	threat_indicators: string
	risk_evaluation: "low" | "medium" | "high"
}

export interface AiWazuhExclusionRuleResponse {
	wazuh_exclusion_rule: string
	wazuh_exclusion_rule_justification: string
}

export interface AiVelociraptorArtifactRecommendationResponse {
	artifact_recommendations: {
		name: string
		description: string
		explanation: string
	}[]
	general_thoughts: string
}

export interface VirusTotalResponse {
	data: VirusTotal
}

export interface VirusTotal {
	data: VirusTotalData
}

export interface VirusTotalData {
	id: string
	type: string
	links: { [key: string]: string }
	attributes: VirusTotalAttributes
}

export interface VirusTotalAttributes {
	total_votes: { [key in VirusTotalLastAnalysisResultCategory]: number }
	last_analysis_results: { [key: string]: VirusTotalLastAnalysisResult }
	regional_internet_registry: string | null
	continent: string | null
	last_modification_date: number
	crowdsourced_context: string | null
	tags: string[]
	asn: number
	whois: string
	whois_date: number
	reputation: number
	last_analysis_date: number
	jarm: string
	country: string | null
	as_owner: string
	last_analysis_stats: VirusTotalLastAnalysisStats
	last_https_certificate_date: number
	network: string
	last_https_certificate: VirusTotalLastHTTPSCertificate
}

export interface VirusTotalLastAnalysisResult {
	method: string
	engine_name: string
	category: VirusTotalLastAnalysisResultCategory
	result: VirusTotalLastAnalysisResultResult
}

export enum VirusTotalLastAnalysisResultCategory {
	Harmless = "harmless",
	Malicious = "malicious",
	Suspicious = "suspicious",
	Undetected = "undetected",
	Timeout = "timeout"
}

export enum VirusTotalLastAnalysisResultResult {
	Clean = "clean",
	Malicious = "malicious",
	Suspicious = "suspicious",
	Unrated = "unrated"
}

export interface VirusTotalLastAnalysisStats {
	malicious: number
	suspicious: number
	undetected: number
	harmless: number
	timeout: number
}

export interface VirusTotalLastHTTPSCertificate {
	cert_signature: {
		signature_algorithm: string
		signature: string
	}
	extensions: VirusTotalLastHTTPSCertificateExtensions
	validity: {
		not_after: Date
		not_before: Date
	}
	size: number
	version: string
	public_key: {
		algorithm: string
		ec: {
			oid: string
			pub: string
		}
	}
	thumbprint_sha256: string
	thumbprint: string
	serial_number: string
	issuer: { [key: string]: string }
	subject: { [key: string]: string }
}

export interface VirusTotalLastHTTPSCertificateExtensions {
	authority_key_identifier: { [key: string]: string }
	subject_key_identifier: string
	subject_alternative_name: string[]
	certificate_policies: string[]
	key_usage: string[]
	extended_key_usage: string[]
	crl_distribution_points: string[]
	ca_information_access: { [key: string]: string }
	CA: boolean
	"1.3.6.1.4.1.11129.2.4.2": string
}

export interface VirusTotalAnalysis {
	type: string
	id: string
	attributes: VirusTotalAnalysisAttributes
	links: Record<string, string>
}

export interface VirusTotalAnalysisAttributes {
	date: number
	status: "queued" | "completed"
	stats: VirusTotalAnalysisStats
	results: { [key: string]: VirusTotalAnalysisResult }
}

export interface VirusTotalAnalysisResult {
	method: string
	engine_name: string
	engine_version: null | string
	engine_update: string
	category: string
	result: null | string
}

export interface VirusTotalAnalysisStats {
	harmless: number
	malicious: number
	suspicious: number
	undetected: number
	timeout: number
	confirmed_timeout: number
	failure: number
	type_unsupported: number
	"confirmed-timeout": number
	"type-unsupported": number
}

export interface VirusTotalFileCheckResponse {
	type: string
	id: string
	links: {
		self: string
	}
}
