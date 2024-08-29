export interface SigmaQuery {
	id: number
	rule_name: string
	rule_query: string
	active: boolean
	time_interval: SigmaTimeInterval
	last_updated: Date
	last_execution_time: Date
}

export type SigmaTimeIntervalValue = number
export type SigmaTimeIntervalUnit = "m" | "h" | "d"
export type SigmaTimeInterval = `${SigmaTimeIntervalValue}${SigmaTimeIntervalUnit}`

export type SigmaRuleLevels = "high" | "critical"
