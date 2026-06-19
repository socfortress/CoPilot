export interface AlertTag {
	id: number
	tag: string
}

export type UntaggedAlertBehavior = "visible_to_all" | "admin_only" | "default_tag"

export interface TagAccessSettings {
	enabled: boolean
	untagged_alert_behavior: UntaggedAlertBehavior
	default_tag_id?: number | null
}

export interface TagAccessSettingsItem {
	enabled: boolean
	untagged_alert_behavior: UntaggedAlertBehavior
	default_tag_id: number | null
	default_tag_name: string | null
}

export interface EffectiveAccessResponse {
	user_id: number
	username: string
	role_id: number
	role_name: string
	accessible_customers: string[]
	accessible_tags: AlertTag[]
	is_tag_unrestricted: boolean
	tag_rbac_enabled: boolean
}
