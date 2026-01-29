export interface AlertTag {
    id: number
    tag: string
}

export interface TagAccessSettings {
    enabled: boolean
    untagged_alert_behavior: "visible_to_all" | "admin_only" | "default_tag"
    default_tag_id?: number | null
}

export interface TagAccessSettingsItem {
    enabled: boolean
    untagged_alert_behavior: "visible_to_all" | "admin_only" | "default_tag"
    default_tag_id: number | null
    default_tag_name: string | null
}

// Response from GET /settings - settings nested under 'settings' key
export interface TagAccessSettingsResponse {
    settings: TagAccessSettingsItem
    success: boolean
    message: string
}

// Response from GET /user/{user_id}
export interface UserTagsResponse {
    user_id: number
    username: string
    accessible_tags: AlertTag[]
    success: boolean
    message: string
}

// Response from GET /tags
export interface AvailableTagsResponse {
    tags: AlertTag[]
    success: boolean
    message: string
}
