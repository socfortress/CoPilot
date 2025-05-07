export interface MitreTechnique {
	technique_id: string
	technique_name: string
	count: number
	last_seen: string
	tactics: MitreTactic[]
}

export interface MitreTactic {
	id: string
	name: string
	short_name: string
}

export interface MitreTechniqueDetails {
	description: string
	name: string
	id: string
	modified_time: Date
	created_time: Date
	tactics: string[]
	url: string
	source: string
	external_id: string
	references: MitreTechniqueDetailsReference[]
	mitigations: string[]
	subtechnique_of: string | null
	techniques: string[] | null
	groups: string[]
	software: string[]
	mitre_detection: string
	mitre_version: string
	deprecated: number
	remote_support: number
	network_requirements: number
	platforms: string[]
	data_sources: string[]
	is_subtechnique: boolean
}

export interface MitreTechniqueDetailsReference {
	url: string
	description: string
	source: string
}
