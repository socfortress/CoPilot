export interface AlertTag {
    id: number
    tag: string
}

export interface TagAccessSettings {
    enabled: boolean
    untagged_alert_behavior: "visible" | "hidden"
}

export interface UserTagAssignment {
    user_id: number
    tag_ids: number[]
}

export interface UserTagsResponse {
    user_id: number
    username: string
    tag_ids: number[]
    tags: AlertTag[]
    success: boolean
    message: string
}

export interface TagAccessSettingsResponse {
    settings: TagAccessSettings
    success: boolean
    message: string
}

export interface AvailableTagsResponse {
    tags: AlertTag[]
    success: boolean
    message: string
}
