export interface ScriptParameter {
	name: string
	type: string
	required: boolean
	description?: string
	default?: string | number | boolean
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

export interface InvokeCopilotActionRequest {
	copilot_action_name: string
	agent_names: string[]
	parameters: Record<string, string | number>
}

export interface CollectArtifactResponse {
	message: string
	success: boolean
	session_id?: string
	flow_id?: string
}

export interface TechnologiesResponse {
	technologies: Technology[]
	message: string
	success: boolean
}
