export interface MitreTechnique {
	technique_id: string
	technique_name: string
	count: number
	last_seen: string
	tactics: {
		[key: string]: string
	}
}
