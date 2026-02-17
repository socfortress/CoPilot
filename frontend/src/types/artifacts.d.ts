// TODO: refactor
export interface Artifact {
	description: string
	name: string
	author?: string | null
	precondition?: string | null
	parameters?: ArtifactParameter[]
}

export interface ArtifactParameter {
	name: string
	description?: string
	type?: string
	default?: string | boolean | null
}

export interface CollectResult {
	[key: string]: string | number | null | object
}

export interface CommandResult {
	Stdout: string
	Stderr: string
	ReturnCode: number
	Complete: boolean
}

export interface QuarantineResult {
	Time: string
	Result: string
}

export interface Recommendation {
	name: string
	description: string
	explanation: string
}

export interface MatchingParameter {
	name: string
	description: string
	type: string
	default?: string
}

export interface FileCollection {
	flow_id?: string
	session_id?: string
}
