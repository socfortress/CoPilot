export interface IncidentCustomerReport {
	id: number
	report_name: string
	customer_code: string
	file_name: string
	file_size: number
	generated_at: string
	generated_by: number
	generated_by_role?: string | null
	generated_by_name?: string | null
	date_from: string
	date_to: string
	filters_applied: Record<string, string | number | boolean>
	total_alerts: number
	total_cases: number
	open_cases: number
	closed_cases: number
	visible_to_customer: boolean
	status: "processing" | "completed" | "failed"
	error_message?: string | null
	download_url?: string | null
}

export type IncidentReportBrandTheme = "socfortress" | "customer"

/**
 * Report layout: full = everything, executive = one-look synthesis,
 *  operational = case detail w/ assets & IOCs, analytics = charts & trends.
 */
export type IncidentReportTemplate = "full" | "executive" | "operational" | "analytics"

export interface IncidentCustomerReportGenerateRequest {
	customer_code: string
	date_from: string
	date_to: string
	report_name?: string
	visible_to_customer?: boolean
	brand_theme?: IncidentReportBrandTheme
	report_template?: IncidentReportTemplate
}

export interface IncidentCustomerReportGenerateBackgroundResponse {
	report_id: number
	report_name: string
	customer_code: string
	status: IncidentCustomerReport["status"]
	check_status_url: string
	download_url: string
}

export interface IncidentCustomerReportListResponse {
	reports: IncidentCustomerReport[]
	total_count: number
}
