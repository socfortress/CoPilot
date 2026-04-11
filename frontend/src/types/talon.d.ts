export interface TalonMessageRequest {
	message: string
	sender?: string
}

export interface TalonInvestigateRequest {
	alert_id: number
	customer_code: string
	sender?: string
}

export interface TalonStatusData {
	[key: string]: unknown
}

export interface TalonJobData {
	id: string
	alert_id: number
	customer_code: string
	status: string
	alert_type: string | null
	triggered_by: string
	template_used: string | null
	created_at: string
	started_at: string | null
	completed_at: string | null
	error_message: string | null
	reports: {
		id: number
		job_id: string
		alert_id: number
		customer_code: string
		severity_assessment: string | null
		summary: string | null
		report_markdown: string | null
		recommended_actions: string | null
		created_at: string
	}[]
}
