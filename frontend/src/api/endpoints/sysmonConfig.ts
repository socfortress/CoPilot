import type { FlaskBaseResponse } from "@/types/flask.d"
import type { ConfigContent, DeployConfigResponse, UploadConfigFileResponse } from "@/types/sysmonConfig.d"
import { HttpClient } from "../httpClient"

export default {
	getAll() {
		return HttpClient.get<FlaskBaseResponse & { customer_codes: string[] }>(`/sysmon_config`)
	},
	getConfigContent(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & ConfigContent>(`/sysmon_config/content/${customerCode}`)
	},
	getConfigFile(customerCode: string) {
		return HttpClient.get<Blob>(`/sysmon_config/${customerCode}`, {
			responseType: "blob"
		})
	},
	uploadConfigFile(customerCode: string, config: File) {
		const form = new FormData()
		form.append("file", new Blob([config], { type: config.type }), config.name)
		form.append("customer_code", customerCode)

		return HttpClient.post<FlaskBaseResponse & UploadConfigFileResponse>(`/sysmon_config/upload`, form)
	},
	deployConfig(customerCode: string) {
		return HttpClient.post<FlaskBaseResponse & DeployConfigResponse>(`/sysmon_config/deploy/${customerCode}`)
	}
}
