export interface ConfigContent {
	customer_code: string
	config_content: string
}

export interface UploadConfigFileResponse {
	customer_code: string
	filename: string
	overwritten: boolean
}

export interface DeployConfigResponse {
	customer_code: string
	worker_success: boolean
	worker_message: string
	error_detail: string
}
