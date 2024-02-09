export interface Pipeline {
	created_at: string
	description: string
	errors: null | string
	id: string
	modified_at: string
	source: string
	stages: PipelineStage[]
	title: string
}

export interface PipelineFull extends Pipeline {
	stages: PipelineFullStage[]
}

export interface PipelineStage {
	match: "EITHER" | "PASS"
	rules: string[]
	stage: number
}

export interface PipelineFullStage {
	match: "EITHER" | "PASS"
	rules: string[]
	rule_ids: string[]
	stage: number
}

export interface PipelineRule {
	created_at: string
	description: string
	errors: null | string
	id: string
	modified_at: string
	source: string
	title: string
}
