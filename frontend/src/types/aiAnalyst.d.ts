export interface AiAnalystJob {
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
}

export interface AiAnalystReport {
	id: number
	job_id: string
	alert_id: number
	customer_code: string
	severity_assessment: string | null
	summary: string | null
	report_markdown: string | null
	recommended_actions: string | null
	created_at: string
}

export interface AiAnalystIoc {
	id: number
	report_id: number
	alert_id: number
	customer_code: string
	ioc_value: string
	ioc_type: string
	vt_verdict: string
	vt_score: string | null
	details: string | null
	created_at: string
}

export interface AlertWithReport {
	alert_id: number
	alert_name: string
	customer_code: string
	status: string
	source: string
	assigned_to: string | null
	alert_creation_time: string
	report: AiAnalystReport
}
