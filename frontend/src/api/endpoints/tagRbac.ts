import type { FlaskBaseResponse } from "@/types/flask.d"
import type {
    AlertTag,
    TagAccessSettings,
    UserTagAssignment,
    UserTagsResponse,
    TagAccessSettingsResponse,
    AvailableTagsResponse
} from "@/types/incidentManagement/tags.d"
import { HttpClient } from "../httpClient"

export default {
    // Get tag RBAC settings
    getSettings() {
        return HttpClient.get<TagAccessSettingsResponse>("/incidents/tag_access/settings")
    },

    // Update tag RBAC settings
    updateSettings(settings: TagAccessSettings) {
        return HttpClient.put<TagAccessSettingsResponse>("/incidents/tag_access/settings", settings)
    },

    // Get all available alert tags
    getAvailableTags() {
        return HttpClient.get<AvailableTagsResponse>("/incidents/tag_access/tags")
    },

    // Get tags assigned to a user
    getUserTags(userId: number) {
        return HttpClient.get<UserTagsResponse>(`/incidents/tag_access/user/${userId}/tags`)
    },

    // Assign tags to a user
    assignUserTags(userId: number, tagIds: number[]) {
        return HttpClient.put<UserTagsResponse>(`/incidents/tag_access/user/${userId}/tags`, {
            tag_ids: tagIds
        })
    },

    // Remove all tags from a user (grant full access)
    clearUserTags(userId: number) {
        return HttpClient.delete<FlaskBaseResponse>(`/incidents/tag_access/user/${userId}/tags`)
    }
}
