export interface InventoryQueryRequest {
	technology?: string
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

export interface CopilotActionListResponse {
	copilot_actions: CopilotAction[]
	total: number
	count: number
	limit: number
	offset: number
	has_more: boolean
	next_offset: number | number
	prev_offset: null | number
}

export interface CopilotAction {
	copilot_action_name: string
	description: string
	technology: string
	icon?: string
	script_parameters: ScriptParameter[]
	repo_url: string
	script_name?: string
	version?: string
	last_updated?: Date
	category?: null | string
	tags?: null | string[]
}

export type ScriptParameterType = "boolean" | "integer" | "string"

export interface ScriptParameter {
	name: string
	type: ScriptParameterType
	required: boolean
	description?: string
	default?: string | number | boolean | null
	enum?: string[] | null
	arg_position?: string
}

export interface CopilotActionInvokeResponse {
	session_id?: string
	flow_id?: string
}
