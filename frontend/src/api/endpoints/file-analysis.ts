// API client for the File Analysis module (issue #974). Mirrors the backend
// router (design/file-analysis/docs/03 section 3). The backend routes are mounted
// under /file-analysis; the HttpClient baseURL already prefixes /api.
//
// Preview images are fetched as blobs (not <img src="…">) so the JWT interceptor
// on HttpClient authenticates the request; the caller converts to an object URL.

import type {
	FileAnalysisAgent,
	FileAnalysisHistoryItem,
	FileAnalysisJob,
	FileAnalysisMatch,
	FileAnalysisResult,
	ReputationMode,
	SubmitFileAnalysisPayload
} from "@/types/file-analysis"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export default {
	/** Collect a file from an endpoint (host path) and analyze it. Returns a job id. */
	submit(payload: SubmitFileAnalysisPayload) {
		return HttpClient.post<FlaskBaseResponse & { job_id: string }>(`/file-analysis/submit`, payload)
	},

	/** List a customer's Velociraptor-enrolled endpoints (hostname/os/online). */
	listAgents(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { agents: FileAnalysisAgent[] }>(
			`/file-analysis/velociraptor/agents`,
			{ params: { customer_code: customerCode } }
		)
	},

	/** Enumerate files matching a path/glob on an endpoint (hashes only, no bytes pulled). */
	enumerateFiles(payload: { customer_code: string; client_id: string; target_path: string }) {
		return HttpClient.post<FlaskBaseResponse & { matches: FileAnalysisMatch[] }>(
			`/file-analysis/velociraptor/enumerate`,
			payload
		)
	},

	/**
	 * Analyst-only direct file upload (multipart). Returns a job id.
	 *  opts.sandbox → run Tier-2 detonation; opts.reputationMode → VirusTotal phase
	 *  ("off" | "lookup" = hash only, never uploads | "upload" = publishes if new).
	 */
	upload(file: File, customerCode: string, opts?: { sandbox?: boolean; reputationMode?: ReputationMode }) {
		const form = new FormData()
		form.append("file", file)
		form.append("customer_code", customerCode)
		form.append("sandbox", String(opts?.sandbox ?? true))
		form.append("reputation_mode", opts?.reputationMode ?? "lookup")
		return HttpClient.post<FlaskBaseResponse & { job_id: string }>(`/file-analysis/upload`, form, {
			headers: { "Content-Type": "multipart/form-data" }
		})
	},

	/** Poll the status of both tiers. Carries sandbox_enabled + hardened flags. */
	getJob(jobId: string) {
		return HttpClient.get<FlaskBaseResponse & { job: FileAnalysisJob }>(`/file-analysis/job/${jobId}`)
	},

	/** Merged Tier 1 + Tier 2 result (inspector JSON + preview names + sandbox summary). */
	getResult(jobId: string) {
		return HttpClient.get<FlaskBaseResponse & { result: FileAnalysisResult }>(`/file-analysis/result/${jobId}`)
	},

	/** Fetch one preview PNG as a blob (authenticated); caller makes an object URL. */
	getPreview(jobId: string, name: string) {
		return HttpClient.get<Blob>(`/file-analysis/result/${jobId}/preview/${encodeURIComponent(name)}`, {
			responseType: "blob"
		})
	},

	/**
	 * "Have we already analyzed this hash?" — the cache is tenant-scoped, so the
	 * customer_code is required; without it the backend answers "not analyzed"
	 * rather than leaking a hit across tenants. Returns the job id on a cache hit.
	 */
	search(sha256: string, customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { job_id: string | null }>(
			`/file-analysis/search/${encodeURIComponent(sha256)}`,
			{ params: { customer_code: customerCode } }
		)
	},

	/** Recent analyses for a customer (newest first) — powers the history table. */
	getHistory(customerCode: string, limit = 50) {
		return HttpClient.get<FlaskBaseResponse & { items: FileAnalysisHistoryItem[] }>(`/file-analysis/history`, {
			params: { customer_code: customerCode, limit }
		})
	},

	/** Delete a stored analysis (result + previews + job). The CAPE detonation is kept. */
	deleteAnalysis(jobId: string) {
		return HttpClient.delete<FlaskBaseResponse & { removed: number }>(`/file-analysis/analysis/${jobId}`)
	},

	/** The COMPLETE raw CAPE report (every API call + all behaviour), fetched on demand. */
	getCapeReport(jobId: string) {
		return HttpClient.get<Record<string, unknown>>(`/file-analysis/result/${jobId}/cape-report`)
	},

	/** A shareable PDF analyst report (verdict + static + reputation + detonation, screenshots embedded). */
	getReportPdf(jobId: string) {
		return HttpClient.get<Blob>(`/file-analysis/result/${jobId}/report.pdf`, { responseType: "blob" })
	}
}
