import type { FlaskBaseResponse } from "@/types/flask.d"
import type { AlertTag, EffectiveAccessResponse, TagAccessSettings, TagAccessSettingsItem } from "@/types/tags"
import { HttpClient } from "../httpClient"

export default {
	// Get tag RBAC settings
	getSettings() {
		return HttpClient.get<FlaskBaseResponse & { settings: TagAccessSettingsItem }>("/incidents/tag_access/settings")
	},

	// Update tag RBAC settings
	updateSettings(settings: TagAccessSettings) {
		return HttpClient.put<FlaskBaseResponse & { settings: TagAccessSettingsItem }>(
			"/incidents/tag_access/settings",
			settings
		)
	},

	// Get all available alert tags
	getAvailableTags() {
		return HttpClient.get<FlaskBaseResponse & { tags: AlertTag[] }>("/incidents/tag_access/tags")
	},

	// Get tags assigned to a user (matches: GET /user/{user_id})
	getUserTags(userId: number) {
		return HttpClient.get<FlaskBaseResponse & { user_id: number; username: string; accessible_tags: AlertTag[] }>(
			`/incidents/tag_access/user/${userId}`
		)
	},

	// Assign tags to a user (matches: PUT /user/{user_id})
	assignUserTags(userId: number, tagIds: number[]) {
		return HttpClient.put<FlaskBaseResponse & { user_id: number; username: string; accessible_tags: AlertTag[] }>(
			`/incidents/tag_access/user/${userId}`,
			{
				tag_ids: tagIds
			}
		)
	},

	// Add tags to a user (matches: POST /user/{user_id}/add)
	addUserTags(userId: number, tagIds: number[]) {
		return HttpClient.post<FlaskBaseResponse & { user_id: number; username: string; accessible_tags: AlertTag[] }>(
			`/incidents/tag_access/user/${userId}/add`,
			{
				tag_ids: tagIds
			}
		)
	},

	// Remove tags from a user (matches: POST /user/{user_id}/remove)
	removeUserTags(userId: number, tagIds: number[]) {
		return HttpClient.post<FlaskBaseResponse & { user_id: number; username: string; accessible_tags: AlertTag[] }>(
			`/incidents/tag_access/user/${userId}/remove`,
			{
				tag_ids: tagIds
			}
		)
	},

	// Get current user's effective access
	getMyEffectiveAccess() {
		return HttpClient.get<FlaskBaseResponse & EffectiveAccessResponse>("/incidents/tag_access/me")
	}
}
