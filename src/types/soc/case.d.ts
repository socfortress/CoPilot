export interface SocCase {
	access_level: number
	case_close_date: DateFormatted
	case_description: string
	case_id: number
	case_name: string
	case_open_date: DateFormatted
	case_soc_id: string
	case_uuid: string
	classification_id: number | null
	classification: string | null
	client_name: string
	customer_code: string
	opened_by_user_id: number
	opened_by: string
	owner_id: number
	owner: string
	state_id: number
	state_name: StateName
}

type DateDay = number
type DateMonth = number
type DateYear = number
export type DateFormatted = `${DateMonth}/${DateDay}/${DateYear}`
type DayFormatted = `${DateYear}-${DateMonth}-${DateDay}`

export enum StateName {
	Closed = "Closed",
	Open = "Open"
}

export interface SocCaseExt {
	case_description: string
	case_id: number
	case_name: string
	case_soc_id: string
	case_tags: string
	case_uuid: string
	classification: string | null
	classification_id: number | null
	close_date: DayFormatted
	custom_attributes: string | null
	customer_id: number
	customer_name: string
	customer_code: string
	initial_date: Date | string
	modification_history: { [key: string]: ModificationHistory }
	open_by_user: string
	open_by_user_id: number
	open_date: DayFormatted
	owner: string
	owner_id: number
	protagonists: string[]
	reviewer: string | null
	reviewer_id: number | null
	state_id: number
	state_name: StateName
	status_id: number
	status_name: string
}

export interface ModificationHistory {
	action: string
	user: string
	user_id: number
}
