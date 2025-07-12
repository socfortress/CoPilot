export interface WazuhFileItem {
	filename: string
	relative_dirname: string
	status: WazuhFileItemStatus
}

export enum WazuhFileItemStatus {
	Disabled = "disabled",
	Enabled = "enabled"
}

export interface WazuhFileDetails {
	filename: string
	content: string
	is_raw: boolean
}
