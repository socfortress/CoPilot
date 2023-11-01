export interface ConfiguredInput {
	title: string
	global: boolean
	name: string
	content_pack: null | string
	created_at: string
	type: string
	creator_user_id: string
	attributes: ConfiguredInputAttributes
	static_fields: StaticFields
	node: string
	id: string
}

export interface ConfiguredInputAttributes {
	recv_buffer_size: number
	tcp_keepalive: boolean
	use_null_delimiter: boolean
	number_worker_threads: number
	tls_client_auth_cert_file: string
	force_rdns: null | boolean
	bind_address: string
	tls_cert_file: string
	store_full_message: null | boolean
	expand_structured_data: null | boolean
	port: number
	tls_key_file: string
	tls_enable: boolean
	tls_key_password: string
	max_message_size: number
	tls_client_auth: string
	override_source: null | string
	charset_name: null | string
	allow_override_date: null | boolean
}

export interface RunningInput {
	id: string
	state: "RUNNING" | string
	started_at: string
	detailed_message: null | string
	message_input: MessageInput
}

export interface MessageInput {
	title: string
	global: boolean
	name: string
	content_pack: null | string
	created_at: string
	type: string
	creator_user_id: string
	attributes: MessageInputAttributes
	static_fields: StaticFields
	node: string
	id: string
}

export interface MessageInputAttributes {
	recv_buffer_size: number
	tcp_keepalive: boolean
	use_null_delimiter: boolean
	number_worker_threads: number
	tls_client_auth_cert_file: string
	bind_address: string
	tls_cert_file: string
	port: number
	tls_key_file: string
	tls_enable: boolean
	tls_key_password: string
	max_message_size: number
	tls_client_auth: string
}

export interface StaticFields {
	[key: string]: string
}

export interface InputExtended
	extends ConfiguredInput,
		Pick<RunningInput, "state" | "started_at" | "detailed_message"> {}
