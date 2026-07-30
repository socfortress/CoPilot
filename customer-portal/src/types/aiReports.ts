/**
 * Read-only AI Analyst types for the portal.
 *
 * Mirrors backend/app/customer_portal/schema/ai_reports.py, which is a
 * deliberately narrower projection of the ai_analyst_* tables than the one the
 * SOC frontend consumes: no job ids, template names or agent error messages.
 */

export interface AiReportIoc {
	id: number
	ioc_value: string
	ioc_type: string
	vt_verdict: string
	vt_score: string | null
	details: string | null
	created_at: string
}

export interface AiReport {
	id: number
	alert_id: number
	customer_code: string
	severity_assessment: string | null
	summary: string | null
	report_markdown: string | null
	recommended_actions: string | null
	created_at: string
}

export interface AiInvestigation {
	status: string
	triggered_by: string
	created_at: string
	started_at: string | null
	completed_at: string | null
}

export interface AiReportAvailability {
	customer_code: string | null
	enabled: boolean
}

export interface AiAlertAnalysis {
	alert_id: number
	/** False when the customer's AI report switch is off — no data is returned at all. */
	enabled: boolean
	has_analysis: boolean
	investigation: AiInvestigation | null
	report: AiReport | null
	iocs: AiReportIoc[]
}

export interface AiInsightAlert {
	alert_id: number
	alert_name: string
	customer_code: string
	severity_assessment: string | null
	summary: string | null
	report_created_at: string
}

export interface AiInsights {
	total_reports: number
	severity_counts: Record<string, number>
	recent: AiInsightAlert[]
}
