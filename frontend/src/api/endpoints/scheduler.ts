import type { FlaskBaseResponse } from "@/types/flask"
import type { Job } from "@/types/scheduler"
import { HttpClient } from "../http-client"
import { searchLimitParams } from "../params"

export interface UpdateJobPayload {
	/** minutes */
	time_interval: number
	extra_data: string
}

export default {
	getAllJobs(query: { search?: string; limit?: number } = {}, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { jobs: Job[] }>(`/scheduler`, {
			params: searchLimitParams(query),
			signal
		})
	},
	getJob(jobId: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { job: Job }>(`/scheduler/${encodeURIComponent(jobId)}`, { signal })
	},
	getNextRun(job_id: string) {
		return HttpClient.get<FlaskBaseResponse & { next_run_time: Date }>(`/scheduler/next_run/${job_id}`)
	},
	jobAction(job_id: string, action: "run" | "start" | "pause") {
		const endpoint = action === "run" ? "jobs/run" : action
		return HttpClient.post<FlaskBaseResponse>(`/scheduler/${endpoint}/${job_id}`)
	},
	updateJob(job_id: string, payload: UpdateJobPayload) {
		return HttpClient.put<FlaskBaseResponse>(`/scheduler/update/${job_id}`, {}, { params: payload })
	}
}
