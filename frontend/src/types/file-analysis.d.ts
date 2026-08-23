// Types for the File Analysis module (issue #974). Mirrors the backend inspector
// JSON contract (design/file-analysis/docs/01 section 2) and the router response
// shapes (docs/03 section 3).

export type FileAnalysisVerdict = "clean" | "suspicious" | "malicious"
export type FileAnalysisTier = "static" | "dynamic"
export type FileAnalysisStatus = "pending" | "queued" | "running" | "done" | "failed"

export interface FileAnalysisJob {
	job_id: string
	sha256: string
	filename: string
	customer_code: string
	status: FileAnalysisStatus
	static_status: FileAnalysisStatus
	dynamic_status?: FileAnalysisStatus
	/** True only when SANDBOX_BACKEND != none AND the backend is available. Drives detonation-tab visibility. */
	sandbox_enabled: boolean
	/** False when the result came from the dev-only in-process inspector (no container isolation). */
	hardened: boolean
	verdict?: FileAnalysisVerdict
	created_at?: string
}

export interface InspectorHashes {
	md5?: string
	sha1?: string
	sha256?: string
	imphash?: string | null
}

export interface InspectorIocs {
	urls: string[]
	ips: string[]
	domains: string[]
}

export interface InspectorSection {
	name: string
	vsize: number
	rawsize: number
	entropy: number
}

export interface InspectorContent {
	raw?: string
	deobfuscated?: string
	deobfuscated_layers?: string[]
	macros?: string
	autoexec_keywords?: string[]
	suspicious_keywords?: string[]
	dde?: string
	javascript?: string
	text?: string
	structure?: Record<string, number>
	pdf_metadata?: Record<string, string>
	target?: string
	arguments?: string
	icon_location?: string
	working_dir?: string
	imports?: string[]
	import_count?: number
	sections?: InspectorSection[]
	capabilities?: string[]
	strings?: string[]
	signature_present?: boolean
	timestamp?: number
	members?: Record<string, unknown>[]
	headers?: Record<string, string>
	body?: string
	attachments?: Record<string, unknown>[]
	note?: string
	[key: string]: unknown
}

export interface InspectorResult {
	sha256: string
	filename: string
	customer_code: string
	filetype: string
	magic: string
	extension_mismatch: boolean
	entropy: number
	hashes: InspectorHashes
	iocs: InspectorIocs
	av?: { engine?: string; signature?: string } | null
	previews: string[]
	content: InspectorContent
	flags: string[]
	analysis_incomplete: boolean
	verdict_hint: FileAnalysisVerdict
}

export interface SandboxSignature {
	name: string
	description?: string
	severity?: number
	mitre?: string[]
	/** True = CAPE-monitor/Windows-guest baseline that doesn't drive the verdict. */
	noise?: boolean
	/** True = static-PE/packer/.NET-JIT heuristic that fires on benign software. */
	low_confidence?: boolean
}

export interface SandboxProcess {
	name: string
	pid?: number
	ppid?: number
	command_line?: string
}

export interface SandboxDns {
	request: string
	type?: string
	answers: string[]
}

export interface SandboxHttp {
	method: string
	host: string
	uri: string
}

export interface SandboxConnection {
	proto: string
	dst: string
	dport?: number
}

export interface SandboxTtp {
	id: string
	signature?: string
}

export interface SandboxPayload {
	name: string
	sha256: string
	type?: string
}

export interface SandboxSummary {
	task_id?: number
	malscore: number
	family: string
	verdict?: string
	machine?: string
	duration?: number
	package?: string
	signatures: SandboxSignature[]
	/** C2 recovered from an extracted malware config — NOT merely-observed traffic. */
	c2_ips: string[]
	c2_domains: string[]
	/** Everything the guest actually contacted (mostly OS telemetry). */
	hosts?: string[]
	domains?: string[]
	dns?: SandboxDns[]
	http?: SandboxHttp[]
	connections?: SandboxConnection[]
	ttps?: SandboxTtp[]
	processes?: SandboxProcess[]
	payloads?: SandboxPayload[]
	dropped: { sha256: string; name?: string; type?: string }[]
	screenshots: string[]
	errors?: string[]
	/**
	 * Full behavioural record — what the sample touched on the host. Keys:
	 *  files, read_files, write_files, delete_files, registry_keys, read_keys,
	 *  write_keys, delete_keys, mutexes, executed_commands, created_services,
	 *  started_services, resolved_apis.
	 */
	behavior?: Record<string, string[]>
	/** CAPE's human-readable event stream (a plain-English action timeline). */
	enhanced?: { event: string; object: string; data?: Record<string, unknown> }[]
	/** Endpoints the sample tried to reach but were unreachable. */
	dead_hosts?: string[]
}

export interface VtDetection {
	engine: string
	result: string
	category: string
}
export interface VtBehaviour {
	mitre: { id: string; description?: string; severity?: string }[]
	contacted_ips: string[]
	contacted_domains: string[]
	contacted_urls: string[]
	dropped_files: { name: string; sha256?: string; type?: string }[]
	processes: string[]
	registry_keys: string[]
	mutexes: string[]
	tags: string[]
}
export interface VirusTotalIntel {
	threat_label?: string
	threat_categories?: string[]
	threat_names?: string[]
	type_description?: string
	size?: number | null
	reputation?: number | null
	harmless_votes?: number
	malicious_votes?: number
	times_submitted?: number | null
	first_seen?: string
	last_analysis?: string
	signed?: boolean
	signer?: string
	names?: string[]
	detections?: VtDetection[]
	detection_count?: number
	yara?: { rule: string; author?: string; description?: string; ruleset?: string }[]
	sigma?: { title: string; level?: string; source?: string }[]
	ids?: { msg: string; severity?: string; category?: string; source?: string }[]
	/** VT's OWN sandbox observations — populated even when our detonation is offline. */
	behaviour?: VtBehaviour | null
}

export interface FileAnalysisReputation {
	source: string
	found: boolean
	sha256?: string
	malicious?: number
	suspicious?: number
	total?: number
	family?: string
	meaningful_name?: string
	permalink?: string
	submitted?: boolean
	/** VirusTotal was turned off for this analysis (phase selection). */
	skipped?: boolean
	note?: string
	/** Deep VT intel (per-engine detections, crowdsourced rules, VT sandbox behaviour). */
	intel?: VirusTotalIntel | null
}

export interface FileAnalysisResult {
	job: FileAnalysisJob
	inspector: InspectorResult
	sandbox?: SandboxSummary | null
	reputation?: FileAnalysisReputation | null
	/** Preview object names, resolvable via Api.fileAnalysis.previewUrl(jobId, name). */
	preview_urls: string[]
	/** One line explaining what drove the verdict (surfaces tier disagreement). */
	verdict_reason?: string | null
}

export interface SubmitFileAnalysisPayload {
	source: "host_path" | "upload"
	customer_code: string
	tiers?: FileAnalysisTier[]
	/** VirusTotal phase: "off" | "lookup" (hash only) | "upload" (publishes if new). */
	reputation_mode?: "off" | "lookup" | "upload"
	client_id?: string
	target_path?: string
	hostname?: string
}

/** A Velociraptor endpoint shown in the submit dropdown (not the raw client_id). */
export interface FileAnalysisAgent {
	client_id: string
	hostname: string
	os: string
	online: boolean
	last_seen: number | null
	unassigned: boolean
}

/** A file matched by an endpoint glob (metadata only — bytes not yet pulled). */
export interface FileAnalysisMatch {
	path: string
	name: string
	size: number
	sha256: string
}

/** One row in a customer's analysis history. */
export interface FileAnalysisHistoryItem {
	job_id: string
	filename: string
	sha256: string
	verdict: FileAnalysisVerdict | null
	source: string
	status: string
	hardened: boolean
	created_at: string
	updated_at: string
	vt_malicious: number | null
	vt_total: number | null
}
