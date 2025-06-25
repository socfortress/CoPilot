export interface Organization {
	name: string
	description: string | null
	company_type: string
	id: string
	org: string | null
	org_auth: OrgAuth
	users: string[] | null
	role: string
	roles: string[]
	active_apps: string[]
	cloud_sync: boolean
	cloud_sync_active: boolean
	sync_config: OrgSyncConfig
	sync_features: OrgSyncFeatures
	invites: string[] | null
	child_orgs?: string[] | null
	manager_orgs: string[] | null
	creator_org: string
	disabled: boolean
	partner_info: OrgPartnerInfo
	sso_config: OrgSsoConfig
	main_priority: string
	region: string
	region_url: string
	tutorials: OrgTutorial[]
	image?: string
}

export interface OrgAuth {
	token: string
	expires: Date | null
}

export interface OrgPartnerInfo {
	reseller: boolean
	reseller_level: string
}

export interface OrgSsoConfig {
	sso_entrypoint: string
	sso_certificate: string
	client_id: string
	client_secret: string
	openid_authorization: string
	openid_token: string
}

export interface OrgSyncConfig {
	interval: number
	api_key: string
	source: string
}

export interface OrgSyncFeatures {
	editing: boolean
	mail_sent: null | boolean
	app_executions: OrgSyncFeature
	multi_env: OrgSyncFeature
	multi_tenant: OrgSyncFeature
	multi_region: OrgSyncFeature
	webhook: OrgSyncFeature
	schedules: OrgSyncFeature
	user_input: OrgSyncFeature
	send_mail: OrgSyncFeature
	send_sms: OrgSyncFeature
	updates: OrgSyncFeature
	email_trigger: OrgSyncFeature
	notifications: OrgSyncFeature
	workflows: OrgSyncFeature
	autocomplete: OrgSyncFeature
	workflow_executions: OrgSyncFeature
	authentication: OrgSyncFeature
	schedule: OrgSyncFeature
	apps: OrgSyncFeature
	shuffle_gpt: OrgSyncFeature
}

export interface OrgSyncFeature {
	active: boolean
	description?: string
	usage: number
	limit: number
}

export interface OrgTutorial {
	name: string
	description: string
	link: string
	done: boolean
	active: boolean
}
