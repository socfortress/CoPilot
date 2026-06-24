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
import { HttpClient } from "../httpClient"

export default {
	// Repository endpoints
	getRepositories() {
		return HttpClient.get<FlaskBaseResponse & SnapshotRepositoryListResponse>("/snapshots/repositories")
	},

	// Snapshot endpoints
	getSnapshotStatus({ repository, snapshot }: SnapshotStatusQuery = {}) {
		const params = new URLSearchParams()
		if (repository) params.append("repository", repository)
		if (snapshot) params.append("snapshot", snapshot)
		const queryString = params.toString()
		return HttpClient.get<FlaskBaseResponse & SnapshotStatusResponse>(
			`/snapshots/status${queryString ? `?${queryString}` : ""}`
		)
	},

	listSnapshots(repository: string) {
		return HttpClient.get<FlaskBaseResponse & SnapshotListResponse>(
			`/snapshots/repositories/${repository}/snapshots`
		)
	},

	createSnapshot(request: CreateSnapshotRequest) {
		return HttpClient.post<FlaskBaseResponse & CreateSnapshotResponse>("/snapshots/create", request)
	},

	restoreSnapshot(request: RestoreSnapshotRequest) {
		return HttpClient.post<FlaskBaseResponse & RestoreSnapshotResponse>("/snapshots/restore", request)
	},

	// Schedule endpoints
	getSchedules(enabledOnly: boolean = false) {
		return HttpClient.get<FlaskBaseResponse & SnapshotScheduleListResponse>(
			`/snapshots/schedules?enabled_only=${enabledOnly}`
		)
	},

	getSchedule(scheduleId: number) {
		return HttpClient.get<FlaskBaseResponse & SnapshotScheduleOperationResponse>(
			`/snapshots/schedules/${scheduleId}`
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
