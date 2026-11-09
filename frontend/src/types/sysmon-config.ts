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
	/** The Sysmon health apply run after an admin's deploy (it adds the sysmon-reload wodle). */
	sysmon_health?: { success: boolean; message: string } | null
	/** Set when the endpoints will not apply the deployed config yet, and why. */
	sysmon_health_warning?: string | null
}
