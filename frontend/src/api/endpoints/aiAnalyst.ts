import type { AiAnalystIoc, AiAnalystJob, AiAnalystReport, AlertWithReport } from "@/types/aiAnalyst.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export default {
	// Jobs
	createJob(payload: {
		id: string
		alert_id: number
		customer_code: string
		triggered_by: "scheduled" | "manual" | "webhook"
		alert_type?: string
		template_used?: string
	}) {
		return HttpClient.post<FlaskBaseResponse & { job: AiAnalystJob }>(`/ai_analyst/jobs`, payload)
	},
	updateJob(
		jobId: string,
		payload: {
			status: "pending" | "running" | "completed" | "failed"
			alert_type?: string
			template_used?: string
			error_message?: string
		}
	) {
		return HttpClient.patch<FlaskBaseResponse & { job: AiAnalystJob }>(`/ai_analyst/jobs/${jobId}`, payload)
	},
	getJob(jobId: string) {
		return HttpClient.get<FlaskBaseResponse & { job: AiAnalystJob }>(`/ai_analyst/jobs/${jobId}`)
	},
	getJobsByAlert(alertId: number) {
		return HttpClient.get<FlaskBaseResponse & { jobs: AiAnalystJob[] }>(`/ai_analyst/jobs/alert/${alertId}`)
	},
	getJobsByCustomer(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { jobs: AiAnalystJob[] }>(`/ai_analyst/jobs/customer/${customerCode}`)
	},

	// Reports
	submitReport(payload: {
		job_id: string
		alert_id: number
		customer_code: string
		severity_assessment?: "Critical" | "High" | "Medium" | "Low" | "Informational"
		summary?: string
		report_markdown?: string
		recommended_actions?: string
	}) {
		return HttpClient.post<FlaskBaseResponse & { report: AiAnalystReport }>(`/ai_analyst/reports`, payload)
	},
	getReportsByAlert(alertId: number) {
		return HttpClient.get<FlaskBaseResponse & { reports: AiAnalystReport[] }>(
			`/ai_analyst/reports/alert/${alertId}`
		)
	},

	// IOCs
	submitIocs(payload: {
		report_id: number
		alert_id: number
		customer_code: string
		iocs: {
			ioc_value: string
			ioc_type: "ip" | "domain" | "hash" | "process" | "url" | "user" | "command"
			vt_verdict?: "malicious" | "suspicious" | "clean" | "unknown"
			vt_score?: string
			details?: string
		}[]
	}) {
		return HttpClient.post<FlaskBaseResponse & { iocs_created: number; iocs: AiAnalystIoc[] }>(
			`/ai_analyst/iocs`,
			payload
		)
	},
	getIocsByReport(reportId: number) {
		return HttpClient.get<FlaskBaseResponse & { iocs: AiAnalystIoc[] }>(`/ai_analyst/iocs/report/${reportId}`)
	},
	getIocsByAlert(alertId: number) {
		return HttpClient.get<FlaskBaseResponse & { iocs: AiAnalystIoc[] }>(`/ai_analyst/iocs/alert/${alertId}`)
	},
	getIocsByCustomer(customerCode: string, vtVerdict?: string) {
		return HttpClient.get<FlaskBaseResponse & { iocs: AiAnalystIoc[] }>(
			`/ai_analyst/iocs/customer/${customerCode}`,
			{
				params: vtVerdict ? { vt_verdict: vtVerdict } : {}
			}
		)
	},

	// Alerts with reports
	getAlertsWithReports(customerCode?: string) {
		return HttpClient.get<FlaskBaseResponse & { alerts: AlertWithReport[] }>(`/ai_analyst/alerts_with_reports`, {
			params: customerCode ? { customer_code: customerCode } : {}
		})
	},

	// Combined alert analysis
	getAlertAnalysis(alertId: number) {
		return HttpClient.get<
			FlaskBaseResponse & {
				job: AiAnalystJob | null
				report: AiAnalystReport | null
				iocs: AiAnalystIoc[] | null
			}
		>(`/ai_analyst/alert/${alertId}`)
	}
}
