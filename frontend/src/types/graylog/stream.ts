export interface Stream {
	content_pack: string | null
	created_at: string
	creator_user_id: string
	description: string
	disabled: boolean
	id: string
	index_set_id: string
	is_default: boolean
	is_editable: boolean
	matching_type: "AND" | "OR" | string
	outputs: string[]
	remove_matches_from_default_stream: boolean
	rules: StreamRule[]
	title: string
}

export interface StreamRule {
	description: string | null
	field: string
	id: string
	inverted: boolean
	stream_id: string
	type: number
	value: string
}
