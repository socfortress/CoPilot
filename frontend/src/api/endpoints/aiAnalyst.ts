import type {
	AiAnalystIoc,
	AiAnalystJob,
	AiAnalystPalaceLesson,
	AiAnalystReport,
	AiAnalystReview,
	AiAnalystReviewStats,
	AlertWithReport,
	PalaceSearchHit,
	QueuePalaceLessonPayload,
	ReplayPayload,
	SubmitReviewPayload
} from "@/types/aiAnalyst.d"
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
	},

	// --- Reviews ---
	/**
	 * Fetch the current user's existing review for a report (if any).
	 * Returns review=null in create-mode so the UI shows a fresh rubric.
	 */
	getMyReview(reportId: number) {
		return HttpClient.get<FlaskBaseResponse & { review: AiAnalystReview | null }>(
			`/ai_analyst/reports/${reportId}/review/mine`
		)
	},
	/**
	 * Upsert the current user's review for a report. Backend enforces
	 * one review per (report, user) via unique constraint — a second call
	 * updates the existing row and sets updated_at.
	 */
	submitReview(reportId: number, payload: SubmitReviewPayload) {
		return HttpClient.post<FlaskBaseResponse & { review: AiAnalystReview }>(
			`/ai_analyst/reports/${reportId}/review`,
			payload
		)
	},
	getReviewsByCustomer(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { reviews: AiAnalystReview[] }>(
			`/ai_analyst/reviews/customer/${customerCode}`
		)
	},
	/**
	 * SQL-side feedback dashboard rollup — counts, averages, template
	 * breakdown, IOC accuracy, and embedded recent reviews for drill-in.
	 */
	getReviewStats(customerCode: string, recentLimit = 10) {
		return HttpClient.get<FlaskBaseResponse & AiAnalystReviewStats>(
			`/ai_analyst/reviews/customer/${customerCode}/stats`,
			{
				params: { recent_limit: recentLimit }
			}
		)
	},

	// --- Replay ---
	/**
	 * Re-run an investigation for the report's alert with a forced template.
	 * The replay creates its own new job/report via Talon's normal callbacks —
	 * this call does not mutate local DB itself.
	 */
	replayReport(reportId: number, payload: ReplayPayload) {
		return HttpClient.post<FlaskBaseResponse & { data?: Record<string, unknown> }>(
			`/ai_analyst/reports/${reportId}/replay`,
			payload
		)
	},

	// --- Palace lessons ---
	queuePalaceLesson(payload: QueuePalaceLessonPayload) {
		return HttpClient.post<FlaskBaseResponse & { lesson: AiAnalystPalaceLesson }>(
			`/ai_analyst/palace_lessons`,
			payload
		)
	},
	/**
	 * Preview similar lessons already stored in MemPalace — debounced against
	 * the lesson-text textarea so the reviewer can see overlap before queueing.
	 */
	searchPalaceLessons(customerCode: string, query: string, room?: string, limit = 5) {
		return HttpClient.get<FlaskBaseResponse & { lessons: PalaceSearchHit[] }>(
			`/ai_analyst/palace_lessons/customer/${customerCode}`,
			{
				params: {
					query,
					limit,
					...(room ? { room } : {})
				}
			}
		)
	}
}
