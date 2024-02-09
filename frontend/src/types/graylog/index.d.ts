export interface Message {
	caller: string
	content: string
	node_id: string
	timestamp: string
}

export interface MessageExtended extends Message {
	id?: string
}

export interface ThroughputMetric {
	metric: string
	value: number
}
