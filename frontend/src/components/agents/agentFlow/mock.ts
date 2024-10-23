import type { CollectResult } from "@/types/flow"

export const flow_results = [
	{
		id: "sedrftg",
		client_id: "client_12345",
		session_id: "session_abc123",
		request: {
			creator: "user123",
			user_data: "some_user_data",
			client_id: "client_12345",
			flow_id: "flow_xyz789",
			urgent: true,
			artifacts: ["artifact_1", "artifact_2"],
			specs: [
				{
					artifactstring: "artifact_spec_1",
					parameters: [
						{
							key: "param1",
							value: "value1",
							comment: "Parameter 1"
						},
						{
							key: "param2",
							value: "value2",
							comment: "Parameter 2"
						}
					]
				}
			],
			cpu_limit: 4,
			iops_limit: 1000,
			progress_timeout: 30,
			timeout: 600,
			max_rows: 1000,
			max_upload_bytes: 10485760,
			trace_freq_sec: 60,
			allow_custom_overrides: true,
			log_batch_time: 5,
			compiled_collector_args: ["arg1", "arg2"],
			ops_per_second: 100
		},
		backtrace: "no_errors_backtrace",
		create_time: 1697884800,
		start_time: 1697884900,
		active_time: 100,
		total_uploaded_files: 5,
		total_expected_uploaded_bytes: 5242880,
		total_uploaded_bytes: 4194304,
		total_collected_rows: 2000,
		total_logs: 15,
		total_requests: 10,
		outstanding_requests: 2,
		next_response_id: 11,
		execution_duration: 3600,
		state: "running",
		status: "active",
		artifacts_with_results: ["artifact_result_1", "artifact_result_2"],
		query_stats: [
			{
				status: "complete",
				error_message: "",
				backtrace: "",
				duration: 200,
				last_active: 1697885000,
				first_active: 1697884800,
				names_with_response: ["name1", "name2"],
				Artifact: "artifact_1",
				log_rows: 50,
				uploaded_files: 3,
				uploaded_bytes: 2097152,
				expected_uploaded_bytes: 3145728,
				result_rows: 500,
				query_id: 1,
				total_queries: 3
			},
			{
				status: "in_progress",
				error_message: "",
				backtrace: "",
				duration: 150,
				last_active: 1697885100,
				first_active: 1697884900,
				names_with_response: ["name3", "name4"],
				Artifact: "artifact_2",
				log_rows: 30,
				uploaded_files: 2,
				uploaded_bytes: 1048576,
				expected_uploaded_bytes: 2097152,
				result_rows: 300,
				query_id: 2,
				total_queries: 5
			}
		],
		uploaded_files: ["file1.txt", "file2.txt"],
		user_notified: true,
		logs: ["log1", "log2", "log3"],
		dirty: false,
		total_loads: 20
	}
]

export const collect_result: CollectResult[] = [
	{
		___id: "2345678",
		uno: 1,
		due: new Date().getTime(),
		tre: "tre"
	}
]
