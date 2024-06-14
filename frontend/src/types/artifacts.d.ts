export interface Artifact {
	description: string
	name: string
}

export interface CollectResult {
	[key: string]: string | number
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
