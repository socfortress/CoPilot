export interface MetricsResponse {
	success: boolean
	message: string
	data: Record<string, any>
}

export interface HostsResponse {
	success: boolean
	message: string
	hosts: string[]
}

export interface TimeSeriesPoint {
	time: string
	value: number
}

export type TimeSeriesData = Record<string, TimeSeriesPoint[]>
