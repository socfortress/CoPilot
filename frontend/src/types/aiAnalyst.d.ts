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

// --- Review / Palace / Replay ---

export type OverallVerdict = "up" | "down"
export type TemplateChoice = "correct" | "wrong" | "partial"
export type LessonType = "environment" | "false_positives" | "assets" | "threat_intel" | "alerts"
export type Durability = "one_off" | "durable"
export type PalaceLessonStatus = "pending" | "ingested" | "failed"

export interface AiAnalystIocReview {
	id: number
	review_id: number
	ioc_id: number
	verdict_correct: boolean
	note: string | null
	created_at: string
}

export interface AiAnalystReview {
	id: number
	report_id: number
	alert_id: number
	customer_code: string
	reviewer_user_id: number
	overall_verdict: OverallVerdict | null
	template_choice: TemplateChoice | null
	template_used: string | null
	rating_instructions: number | null
	rating_artifacts: number | null
	rating_severity: number | null
	missing_steps: string | null
	suggested_edits: string | null
	created_at: string
	updated_at: string | null
	ioc_reviews: AiAnalystIocReview[]
}

export interface IocVerdictCorrection {
	ioc_id: number
	verdict_correct: boolean
	note?: string
}

export interface SubmitReviewPayload {
	overall_verdict?: OverallVerdict
	template_choice?: TemplateChoice
	template_used?: string
	rating_instructions?: number
	rating_artifacts?: number
	rating_severity?: number
	missing_steps?: string
	suggested_edits?: string
	ioc_reviews?: IocVerdictCorrection[]
}

export interface AiAnalystPalaceLesson {
	id: number
	review_id: number | null
	customer_code: string
	lesson_type: string
	lesson_text: string
	durability: string
	status: string
	ingested_at: string | null
	created_at: string
}

export interface QueuePalaceLessonPayload {
	customer_code: string
	lesson_type: LessonType
	lesson_text: string
	durability?: Durability
	review_id?: number
}

export interface ReplayPayload {
	template_override: string
	customer_code: string
	sender?: string
}

export interface PalaceSearchHit {
	id: string | null
	room: string | null
	wing: string | null
	text: string | null
	source_file: string | null
	score: number | null
	metadata: Record<string, unknown> | null
}

// --- Feedback dashboard ---

export interface ReviewStatsTemplate {
	template_used: string | null
	total: number
	thumbs_up: number
	thumbs_down: number
	correct: number
	partial: number
	wrong: number
	avg_rating_instructions: number | null
	avg_rating_artifacts: number | null
	avg_rating_severity: number | null
}

export interface ReviewStatsIocAccuracy {
	total: number
	correct: number
	incorrect: number
	accuracy_pct: number | null
}

export interface AiAnalystReviewStats {
	customer_code: string
	total_reviews: number
	thumbs_up: number
	thumbs_down: number
	thumbs_up_pct: number | null
	template_choice_correct: number
	template_choice_partial: number
	template_choice_wrong: number
	avg_rating_instructions: number | null
	avg_rating_artifacts: number | null
	avg_rating_severity: number | null
	ioc_accuracy: ReviewStatsIocAccuracy
	per_template: ReviewStatsTemplate[]
	recent_reviews: AiAnalystReview[]
}
