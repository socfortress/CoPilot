export interface SocCaseAsset {
	analysis_status: string
	analysis_status_id: number
	asset_compromise_status_id: number
	asset_description: string
	asset_domain: string
	asset_icon_compromised: string
	asset_icon_not_compromised: string
	asset_id: number
	asset_ip: string
	asset_name: string
	asset_tags: string
	asset_type: string
	asset_type_id: number
	asset_uuid: string
	ioc_links: null | string
	link: SocCaseAssetLink[]
}
type DateDay = number
type DateMonth = number
type DateYear = number
type DayFormatted = `${DateYear}-${DateMonth}-${DateDay}`

export interface SocCaseAssetLink {
	case_name: string
	case_open_date: DayFormatted
	asset_description: string
	asset_compromise_status_id: number | null
	asset_id: number
	case_id: number
}

export interface SocCaseAssetsState {
	object_last_update: string | Date
	object_state: number
}

export interface SocAlertAsset {
	analysis_status_id?: number
	asset_compromise_status_id?: string
	asset_description: string
	asset_domain?: string
	asset_enrichment?: string
	asset_id: number
	asset_info?: string
	asset_ip: string
	asset_name: string
	asset_tags: string
	asset_type_id: number
	asset_type: SocAlertAssetType
	asset_uuid: string
	case_id?: number
	custom_attributes?: string
	date_added?: string
	date_update?: string
	user_id?: number
}

export interface SocAlertAssetType {
	asset_id: number
	asset_icon_compromised: string
	asset_name: string
	asset_icon_not_compromised: string
	asset_description: string
}
