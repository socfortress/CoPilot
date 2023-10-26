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

export interface PipelineStage {
	match: string
	rules: string[]
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
