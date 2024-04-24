import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { Job } from "@/types/scheduler"

export interface UpdateJobPayload {
	time_interval: number
	extra_data: string
}

export default {
	getAllJobs() {
		return HttpClient.get<FlaskBaseResponse & { jobs: Job[] }>(`/scheduler`)
	},
	getNextRun(job_id: string) {
		return HttpClient.get<FlaskBaseResponse & { next_run_time: Date }>(`/scheduler/next_run/${job_id}`)
	},
	jobAction(job_id: string, action: "run" | "start" | "pause") {
		return HttpClient.post<FlaskBaseResponse>(`/scheduler/jobs/${action}/${job_id}`)
	},
	updateJob(job_id: string, payload: UpdateJobPayload) {
		return HttpClient.put<FlaskBaseResponse>(`/scheduler/jobs/update/${job_id}`, {}, { params: payload })
	}
}
