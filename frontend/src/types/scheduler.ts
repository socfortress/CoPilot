export interface Job {
	id: string
	name: string
	enabled: boolean
	/** minutes */
	time_interval: number
	last_success: Date
	description: string
}
