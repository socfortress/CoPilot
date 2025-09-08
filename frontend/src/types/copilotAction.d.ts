export enum Technology {
	WAZUH = "Wazuh",
	LINUX = "Linux",
	WINDOWS = "Windows",
	MACOS = "macOS",
	NETWORK = "Network",
	CLOUD = "Cloud",
	VELOCIRAPTOR = "Velociraptor"
}

export interface ScriptParameter {
	name: string
	type: string
	required: boolean
	description?: string
	default?: string | number | boolean | Array<any> | Record<string, any>
	enum?: string[]
	arg_position?: string
}

export interface ActiveResponseItem {
	copilot_action_name: string
	description: string
	technology: Technology
	icon?: string
	script_parameters: ScriptParameter[]
	repo_url: string
	script_name?: string
	version?: string
	last_updated?: Date
	category?: string
	tags?: string[]
}

export interface InventoryQueryRequest {
	technology?: Technology
	category?: string
	tag?: string
	q?: string
	limit?: number
	offset?: number
	refresh?: boolean
	include?: string
}

export interface InventoryResponse {
	copilot_actions: ActiveResponseItem[]
	message: string
	success: boolean
}

export interface ActionDetailResponse {
	copilot_action: ActiveResponseItem
	message: string
	success: boolean
}

export interface InventoryMetricsResponse {
	status: string
	metrics: Record<string, any>
	message: string
	success: boolean
}

export interface InvokeCopilotActionRequest {
	copilot_action_name: string
	agent_names: string[]
	parameters: Record<string, any>
}

export interface CollectArtifactResponse {
	message: string
	success: boolean
	session_id?: string
	flow_id?: string
}

export interface InvokeCopilotActionResponse {
	responses: CollectArtifactResponse[]
	message: string
	success: boolean
}

export interface TechnologiesResponse {
	technologies: Technology[]
	message: string
	success: boolean
}
