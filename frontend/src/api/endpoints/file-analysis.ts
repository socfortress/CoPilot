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

	/** Analyst-only direct file upload (multipart). Returns a job id. */
	upload(file: File, customerCode: string) {
		const form = new FormData()
		form.append("file", file)
		form.append("customer_code", customerCode)
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

	/** Start (or reuse) an interactive detonation session; returns a Guacamole iframe URL. */
	startInteractive(jobId: string) {
		return HttpClient.post<FlaskBaseResponse & { guac_url: string }>(`/file-analysis/job/${jobId}/interactive`)
	},

	/** Cache lookup by SHA256 — returns an existing job id if this hash was analyzed before. */
	searchHash(sha256: string) {
		return HttpClient.get<FlaskBaseResponse & { job_id?: string }>(`/file-analysis/search/${sha256}`)
	},

	/** Recent analyses for a customer (newest first) — powers the history table. */
	getHistory(customerCode: string, limit = 50) {
		return HttpClient.get<FlaskBaseResponse & { items: FileAnalysisHistoryItem[] }>(`/file-analysis/history`, {
			params: { customer_code: customerCode, limit }
		})
	}
}
