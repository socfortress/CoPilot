export interface WazuhGroup {
	name: string
	count: number
	mergedSum: string
	configSum: string
}

export interface WazuhGroupFile {
	filename: string
	hash: string
}

export interface WazuhGroupFileDetails {
	group_id: string
	filename: string
	content: string
	is_raw: boolean
}

export interface WazuhGroupConfigurationUpdate {
	success: boolean
	message: string
	group_id: string
	filename: string
}
