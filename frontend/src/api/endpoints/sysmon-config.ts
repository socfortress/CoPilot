import type { FlaskBaseResponse } from "@/types/flask"
import type {
	ConfigContent,
	DefaultConfigResponse,
	DefaultSyncRunResponse,
	DefaultSyncStatusResponse,
	DeployConfigResponse,
	SaveDefaultConfigResponse,
	StatsPreviewResponse,
	StatsRunResponse,
	StatsSharingBody,
	StatsSharingResponse,
	StatsStatusResponse,
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
	},
	/** Where this CoPilot's default comes from: the SOCFortress default sync's mode, last check and release. Admin only. */
	getDefaultSyncStatus(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & DefaultSyncStatusResponse>(`/sysmon_config/default-config/sync`, {
			signal
		})
	},
	/**
	 * Check SOCFortress for a newer default now. With force, a default changed on this CoPilot is replaced too (older
	 * releases are refused either way). Admin only.
	 */
	syncDefaultConfig(force = false) {
		return HttpClient.post<FlaskBaseResponse & DefaultSyncRunResponse>(`/sysmon_config/default-config/sync`, null, {
			params: { force }
		})
	},
	/** The weekly Sysmon noise statistics sent to SOCFortress: mode, last run, and per customer its sharing. Admin only. */
	getStatsStatus(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & StatsStatusResponse>(`/sysmon_config/stats`, { signal })
	},
	/** Turn a customer's noise statistics off or on (off also asks SOCFortress to delete its reports). Admin only. */
	setStatsSharing(customerCode: string, body: StatsSharingBody) {
		return HttpClient.put<FlaskBaseResponse & StatsSharingResponse>(
			`/sysmon_config/stats/customers/${encodeURIComponent(customerCode)}`,
			body
		)
	},
	/** The exact report a customer's week would send. Sends nothing. Admin only. */
	previewStats(customerCode: string, week?: string) {
		return HttpClient.post<FlaskBaseResponse & StatsPreviewResponse>(
			`/sysmon_config/stats/customers/${encodeURIComponent(customerCode)}/preview`,
			null,
			{ params: week ? { week } : undefined }
		)
	},
	/** Send the due reports now (each week once per customer). resume lifts the pause after a refusal. Admin only. */
	sendStatsNow(options: { customerCode?: string; resume?: boolean } = {}) {
		const params: Record<string, string | boolean> = {}
		if (options.customerCode) params.customer_code = options.customerCode
		if (options.resume) params.resume = true
		return HttpClient.post<FlaskBaseResponse & StatsRunResponse>(`/sysmon_config/stats/send-now`, null, { params })
	}
}
