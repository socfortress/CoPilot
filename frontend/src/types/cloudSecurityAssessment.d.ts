export type ScoutSuiteReport = string

export enum ScoutSuiteReportType {
	AWS = "aws",
	Azure = "azure"
}
export interface ScoutSuiteReportPayload {
	report_type: ScoutSuiteReportType
	report_name: string
}
export interface ScoutSuiteAwsReportPayload {
	access_key_id: string
	secret_access_key: string
}
export interface ScoutSuiteAzureReportPayload {
	username: string
	password: string
	tenant_id: string
}
