export interface FlowResult {
	client_id: string
	session_id: string
	request: FlowRequest
	backtrace: string
	create_time: number
	start_time: number
	active_time: number
	total_uploaded_files: number
	total_expected_uploaded_bytes: number
	total_uploaded_bytes: number
	total_collected_rows: number
	total_logs: number
	total_requests: number
	outstanding_requests: number
	next_response_id: number
	execution_duration: number
	state: string
	status: string
	artifacts_with_results: string[]
	query_stats: FlowQueryStat[]
	uploaded_files: string[]
	user_notified: boolean
	logs: string[]
	dirty: boolean
	total_loads: number
}

export interface FlowQueryStat {
	status: string
	error_message: string
	backtrace: string
	duration: number
	last_active: number
	first_active: number
	names_with_response: string[]
	Artifact: string
	log_rows: number
	uploaded_files: number
	uploaded_bytes: number
	expected_uploaded_bytes: number
	result_rows: number
	query_id: number
	total_queries: number
}

export interface FlowRequest {
	creator: string
	user_data: string
	client_id: string
	flow_id: string
	urgent: boolean
	artifacts: string[]
	specs: FlowRequestSpecs[]
	cpu_limit: number
	iops_limit: number
	progress_timeout: number
	timeout: number
	max_rows: number
	max_upload_bytes: number
	trace_freq_sec: number
	allow_custom_overrides: boolean
	log_batch_time: number
	compiled_collector_args: string[]
	ops_per_second: number
}

export interface FlowRequestSpecs {
	artifactstring: string
	parameters: {
		key: string
		value: string
		comment: string
	}[]
}

export interface CollectResult {
	[key: string]: string | number
}

export enum IPFamily {
	IPv4 = "IPv4",
	IPv6 = "IPv6"
}

export type ConnectionStatus = "ESTAB" | "LISTEN" | ""

export enum ConnectionType {
	TCP = "TCP",
	UDP = "UDP"
}
