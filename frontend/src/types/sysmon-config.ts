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

/** This CoPilot's default Sysmon config, which pre-fills "Add new Configuration". */
export interface DefaultConfigResponse {
	/** Whether a default is set on this CoPilot. */
	present: boolean
	/** The default, rendered for `rendered_for` when a customer code was given. */
	config_content: string | null
	/**
	 * The customer code that replaced each __INSTALLDIRNAME__ placeholder. Null when no customer code was given, or when
	 * the default has no placeholder: then it comes back as stored.
	 */
	rendered_for: string | null
	/** How many times __INSTALLDIRNAME__ occurs in the stored default. Each was replaced when `rendered_for` is set. */
	placeholders: number
}

export interface SaveDefaultConfigResponse {
	/** How many times __INSTALLDIRNAME__ occurs in what was saved. */
	placeholders: number
	/** How many of the customer's install-folder paths were turned back into the placeholder. */
	restored: number
}
