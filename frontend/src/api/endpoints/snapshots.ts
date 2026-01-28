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
    SnapshotStatusResponse
} from "@/types/snapshots.d"
import { HttpClient } from "../httpClient"

export default {
    // Repository endpoints
    getRepositories() {
        return HttpClient.get<SnapshotRepositoryListResponse>("/snapshots/repositories")
    },

    // Snapshot endpoints
    getSnapshotStatus(repository?: string, snapshot?: string) {
        const params = new URLSearchParams()
        if (repository) params.append("repository", repository)
        if (snapshot) params.append("snapshot", snapshot)
        const queryString = params.toString()
        return HttpClient.get<SnapshotStatusResponse>(`/snapshots/status${queryString ? `?${queryString}` : ""}`)
    },

    listSnapshots(repository: string) {
        return HttpClient.get<SnapshotListResponse>(`/snapshots/repositories/${repository}/snapshots`)
    },

    createSnapshot(request: CreateSnapshotRequest) {
        return HttpClient.post<CreateSnapshotResponse>("/snapshots/create", request)
    },

    restoreSnapshot(request: RestoreSnapshotRequest) {
        return HttpClient.post<RestoreSnapshotResponse>("/snapshots/restore", request)
    },

    // Schedule endpoints
    getSchedules(enabledOnly: boolean = false) {
        return HttpClient.get<SnapshotScheduleListResponse>(`/snapshots/schedules?enabled_only=${enabledOnly}`)
    },

    getSchedule(scheduleId: number) {
        return HttpClient.get<SnapshotScheduleOperationResponse>(`/snapshots/schedules/${scheduleId}`)
    },

    createSchedule(request: SnapshotScheduleCreate) {
        return HttpClient.post<SnapshotScheduleOperationResponse>("/snapshots/schedules", request)
    },

    updateSchedule(scheduleId: number, request: SnapshotScheduleUpdate) {
        return HttpClient.put<SnapshotScheduleOperationResponse>(`/snapshots/schedules/${scheduleId}`, request)
    },

    deleteSchedule(scheduleId: number) {
        return HttpClient.delete<SnapshotScheduleOperationResponse>(`/snapshots/schedules/${scheduleId}`)
    }
}
