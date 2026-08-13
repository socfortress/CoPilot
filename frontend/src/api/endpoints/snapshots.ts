import type { FlaskBaseResponse } from "@/types/flask"
import type {
	CreateSnapshotRequest,
	CreateSnapshotResponse,
	RestoreSnapshotRequest,
	RestoreSnapshotResponse,
	SnapshotListResponse,
	SnapshotRepositoryListResponse,
	SnapshotScheduleCreate,
	SnapshotScheduleListResponse,
	SnapshotScheduleOperationResponse,
	SnapshotScheduleUpdate,
	SnapshotStatusQuery,
	SnapshotStatusResponse
} from "@/types/snapshots"
import { HttpClient } from "../http-client"

export default {
	// Repository endpoints
	getRepositories(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & SnapshotRepositoryListResponse>("/snapshots/repositories", { signal })
	},

	// Snapshot endpoints
	getSnapshotStatus({ repository, snapshot }: SnapshotStatusQuery, signal?: AbortSignal) {
		const params = new URLSearchParams()
		if (repository) params.append("repository", repository)
		if (snapshot) params.append("snapshot", snapshot)
		const queryString = params.toString()
		return HttpClient.get<FlaskBaseResponse & SnapshotStatusResponse>(
			`/snapshots/status${queryString ? `?${queryString}` : ""}`,
			{ signal }
		)
	},

	listSnapshots(repository: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & SnapshotListResponse>(
			`/snapshots/repositories/${repository}/snapshots`,
			{ signal }
		)
	},

	createSnapshot(request: CreateSnapshotRequest) {
		return HttpClient.post<FlaskBaseResponse & CreateSnapshotResponse>("/snapshots/create", request)
	},

	restoreSnapshot(request: RestoreSnapshotRequest) {
		return HttpClient.post<FlaskBaseResponse & RestoreSnapshotResponse>("/snapshots/restore", request)
	},

	// Schedule endpoints
	getSchedules(query: { enabledOnly?: boolean }, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & SnapshotScheduleListResponse>(
			`/snapshots/schedules?enabled_only=${query.enabledOnly ?? false}`,
			{ signal }
		)
	},

	getSchedule(scheduleId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & SnapshotScheduleOperationResponse>(
			`/snapshots/schedules/${scheduleId}`,
			{ signal }
		)
	},

	createSchedule(request: SnapshotScheduleCreate) {
		return HttpClient.post<FlaskBaseResponse & SnapshotScheduleOperationResponse>("/snapshots/schedules", request)
	},

	updateSchedule(scheduleId: number, request: SnapshotScheduleUpdate) {
		return HttpClient.put<FlaskBaseResponse & SnapshotScheduleOperationResponse>(
			`/snapshots/schedules/${scheduleId}`,
			request
		)
	},

	deleteSchedule(scheduleId: number) {
		return HttpClient.delete<FlaskBaseResponse & SnapshotScheduleOperationResponse>(
			`/snapshots/schedules/${scheduleId}`
		)
	}
}
