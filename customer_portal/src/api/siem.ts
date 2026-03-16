import { httpClient } from "@/utils/httpClient"

export interface EventSource {
	id: number
	customer_code: string
	name: string
	index_pattern: string
	event_type: string
	time_field: string
	enabled: boolean
	created_at: string
	updated_at: string
}

export interface EventSearchResult {
	[key: string]: any
}

export interface FieldMapping {
	field: string
	type: string
}

export class SiemAPI {
	static async getCustomerCodes(): Promise<{ success: boolean; customer_codes: string[] }> {
		return (await httpClient.get("/auth/me/customers")).data
	}

	static async getEventSources(
		customerCode: string
	): Promise<{ success: boolean; message: string; event_sources: EventSource[] }> {
		return (await httpClient.get(`/siem/event_sources/${customerCode}`)).data
	}

	static async queryEvents(
		customerCode: string,
		sourceName: string,
		params: { timerange?: string; page_size?: number; scroll_id?: string; query?: string }
	): Promise<{
		success: boolean
		message: string
		events: EventSearchResult[]
		total: number
		scroll_id: string | null
		page_size: number
	}> {
		return (await httpClient.get(`/siem/events/${customerCode}/${sourceName}`, { params })).data
	}

	static async getFieldMappings(
		customerCode: string,
		sourceName: string
	): Promise<{
		success: boolean
		message: string
		fields: FieldMapping[]
		total: number
		index_pattern: string
	}> {
		return (await httpClient.get(`/siem/events/${customerCode}/${sourceName}/fields`)).data
	}
}
