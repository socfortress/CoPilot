import type { FlaskBaseResponse } from "@/types/flask"
import type {
	ConfigContent,
	DefaultConfigResponse,
	DeployConfigResponse,
	SaveDefaultConfigResponse,
	UploadConfigFileResponse
} from "@/types/sysmon-config"
import { HttpClient } from "../http-client"

export default {
	getAll(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { customer_codes: string[] }>(`/sysmon_config`, { signal })
	},
	getConfigContent(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & ConfigContent>(`/sysmon_config/content/${customerCode}`, { signal })
	},
	getConfigFile(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<Blob>(`/sysmon_config/${customerCode}`, { responseType: "blob", signal })
	},
	uploadConfigFile(customerCode: string, config: File) {
		const form = new FormData()
		form.append("file", new Blob([config], { type: config.type }), config.name)
		form.append("customer_code", customerCode)

		return HttpClient.post<FlaskBaseResponse & UploadConfigFileResponse>(`/sysmon_config/upload`, form)
	},
	deployConfig(customerCode: string) {
		return HttpClient.post<FlaskBaseResponse & DeployConfigResponse>(`/sysmon_config/deploy/${customerCode}`)
	},
	/** This CoPilot's default Sysmon config, rendered for the customer when a code is given. Admin only. */
	getDefaultConfig(customerCode?: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & DefaultConfigResponse>(`/sysmon_config/default-config`, {
			params: customerCode ? { customer_code: customerCode } : undefined,
			signal
		})
	},
	/**
	 * Replace this CoPilot's default Sysmon config. With a customer code, its install-folder paths are turned back into
	 * the __INSTALLDIRNAME__ placeholder first. Admin only.
	 */
	saveDefaultConfig(configContent: string, customerCode?: string) {
		return HttpClient.put<FlaskBaseResponse & SaveDefaultConfigResponse>(`/sysmon_config/default-config`, {
			config_content: configContent,
			customer_code: customerCode || null
		})
	}
}
