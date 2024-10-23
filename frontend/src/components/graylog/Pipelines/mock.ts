import type { PipelineFull } from "@/types/graylog/pipelines"

export const pipeline_full: PipelineFull[] = [
	{
		created_at: "2023-10-01T12:00:00Z",
		description: "Pipeline for processing customer data",
		errors: null,
		id: "pipeline_001",
		modified_at: "2023-10-10T15:30:00Z",
		source: "internal_system",
		stages: [
			{
				match: "PASS",
				rules: ["rule_001", "rule_002"],
				rule_ids: ["rule_id_001", "rule_id_002"],
				stage: 1
			},
			{
				match: "EITHER",
				rules: ["rule_003", "rule_004"],
				rule_ids: ["rule_id_003", "rule_id_004"],
				stage: 2
			}
		],
		title: "Customer Data Pipeline"
	},
	{
		created_at: "2023-09-15T08:45:00Z",
		description: "Pipeline for processing transaction data",
		errors: "Error in stage 3",
		id: "pipeline_002",
		modified_at: "2023-09-20T11:00:00Z",
		source: "external_system",
		stages: [
			{
				match: "PASS",
				rules: ["rule_005"],
				rule_ids: ["rule_id_005"],
				stage: 1
			},
			{
				match: "PASS",
				rules: ["rule_006", "rule_007"],
				rule_ids: ["rule_id_006", "rule_id_007"],
				stage: 2
			},
			{
				match: "EITHER",
				rules: ["rule_008"],
				rule_ids: ["rule_id_008"],
				stage: 3
			}
		],
		title: "Transaction Data Pipeline"
	}
]
