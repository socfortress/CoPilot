import type {
	CloudAccount,
	CloudAccountCreatePayload,
	CloudAccountUpdatePayload,
	CloudAvailability,
	CloudCheck,
	CloudChecksQuery,
	CloudComplianceFramework,
	CloudConnectionTest,
	CloudFinding,
	CloudFindingsQuery,
	CloudReportKind,
	CloudRequirement,
	CloudScan,
	CloudScanStatus
} from "@/types/cloud-assessment"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

// Cloud security assessment with Prowler (#1328). A copilot-prowler failure comes back as 502/503
// with a fixed text, never 401/403, so it shows as an ordinary error, not a session logout.
const base = (customerCode: string) => `/cloud_assessment/${encodeURIComponent(customerCode)}`

interface AccountList extends FlaskBaseResponse {
	accounts: CloudAccount[]
	encryption_key_configured: boolean
	runner_configured: boolean
}

interface Paged {
	total: number
	page: number
	page_size: number
}

// Repeated keys (severity=high&severity=low), which is what FastAPI reads as a list.
const repeated = { paramsSerializer: { indexes: null } }

export default {
	availability(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & CloudAvailability>("/cloud_assessment/availability", { signal })
	},
	/** Every account of the customers the caller can see: the page's overview. */
	getAllAccounts(signal?: AbortSignal) {
		return HttpClient.get<AccountList>("/cloud_assessment/accounts", { signal })
	},
	getAccounts(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<AccountList>(`${base(customerCode)}/accounts`, { signal })
	},
	getAccount(customerCode: string, accountId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { account: CloudAccount }>(`${base(customerCode)}/accounts/${accountId}`, {
			signal
		})
	},
	/** Admin only. */
	createAccount(customerCode: string, payload: CloudAccountCreatePayload) {
		return HttpClient.post<FlaskBaseResponse & { account: CloudAccount }>(`${base(customerCode)}/accounts`, payload)
	},
	/** Admin only. Fields not sent stay; a credential not sent stays. */
	updateAccount(customerCode: string, accountId: number, payload: CloudAccountUpdatePayload) {
		return HttpClient.put<FlaskBaseResponse & { account: CloudAccount }>(
			`${base(customerCode)}/accounts/${accountId}`,
			payload
		)
	},
	/** Admin only. Deletes the account's scans, findings and reports too. */
	deleteAccount(customerCode: string, accountId: number) {
		return HttpClient.delete<FlaskBaseResponse & { scans_deleted: number }>(`${base(customerCode)}/accounts/${accountId}`)
	},
	/** Asks copilot-prowler whether the credential works. Takes up to two minutes. */
	testConnection(customerCode: string, accountId: number) {
		return HttpClient.post<FlaskBaseResponse & CloudConnectionTest>(`${base(customerCode)}/accounts/${accountId}/test`)
	},
	startScan(customerCode: string, accountId: number) {
		return HttpClient.post<FlaskBaseResponse & { scan: CloudScan }>(`${base(customerCode)}/accounts/${accountId}/scans`)
	},
	getScans(
		customerCode: string,
		query: { account_id?: number; status?: CloudScanStatus; page?: number; page_size?: number },
		signal?: AbortSignal
	) {
		return HttpClient.get<FlaskBaseResponse & Paged & { scans: CloudScan[] }>(`${base(customerCode)}/scans`, {
			params: query,
			signal
		})
	},
	getScan(customerCode: string, scanId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { scan: CloudScan }>(`${base(customerCode)}/scans/${scanId}`, { signal })
	},
	cancelScan(customerCode: string, scanId: number) {
		return HttpClient.post<FlaskBaseResponse & { scan: CloudScan }>(`${base(customerCode)}/scans/${scanId}/cancel`)
	},
	/** Admin only. */
	deleteScan(customerCode: string, scanId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`${base(customerCode)}/scans/${scanId}`)
	},
	getChecks(customerCode: string, scanId: number, query: CloudChecksQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & Paged & { checks: CloudCheck[]; services: string[] }>(
			`${base(customerCode)}/scans/${scanId}/checks`,
			{ params: query, signal, ...repeated }
		)
	},
	getFindings(customerCode: string, scanId: number, query: CloudFindingsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & Paged & { findings: CloudFinding[] }>(
			`${base(customerCode)}/scans/${scanId}/findings`,
			{ params: query, signal, ...repeated }
		)
	},
	getCompliance(customerCode: string, scanId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { frameworks: CloudComplianceFramework[]; catalog_available: boolean }>(
			`${base(customerCode)}/scans/${scanId}/compliance`,
			{ signal }
		)
	},
	getComplianceFramework(customerCode: string, scanId: number, frameworkKey: string, signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & {
				framework: CloudComplianceFramework
				requirements: CloudRequirement[]
				catalog_available: boolean
			}
		>(`${base(customerCode)}/scans/${scanId}/compliance/${encodeURIComponent(frameworkKey)}`, { signal })
	},
	/** Prowler's report, as a file to save: never shown as a page of CoPilot's. */
	downloadReport(customerCode: string, scanId: number, kind: CloudReportKind) {
		return HttpClient.get<Blob>(`${base(customerCode)}/scans/${scanId}/reports/${kind}`, {
			responseType: "blob",
			keepOnNavigation: true
		})
	}
}
