import type { AlertsEventElement } from "@/types/graylog/alerts"

export const alerts_event_element: AlertsEventElement[] = [
	{
		event: {
			alert: true,
			event_definition_id: "event_def_001",
			event_definition_type: "threshold",
			fields: {
				field1: "value1",
				field2: "value2",
				field3: "value3"
			},
			group_by_fields: {},
			id: "event_12345",
			key: null,
			key_tuple: [],
			message: "Alert triggered due to threshold breach",
			origin_context: "system_monitor",
			priority: 1,
			source: "source_system",
			source_streams: ["stream_1", "stream_2"],
			streams: ["stream_1", "stream_2", "stream_3"],
			timerange_end: null,
			timerange_start: null,
			timestamp: "2024-10-22T10:15:30Z",
			timestamp_processing: "2024-10-22T10:16:00Z"
		},
		index_name: "alert_index_001",
		index_type: "logs"
	},
	{
		event: {
			alert: false,
			event_definition_id: "event_def_002",
			event_definition_type: "aggregation",
			fields: {
				fieldA: "valueA",
				fieldB: "valueB"
			},
			group_by_fields: {},
			id: "event_67890",
			key: null,
			key_tuple: [],
			message: "No issues detected, monitoring continues",
			origin_context: "network_monitor",
			priority: 3,
			source: "network_system",
			source_streams: ["stream_3"],
			streams: ["stream_3", "stream_4"],
			timerange_end: null,
			timerange_start: null,
			timestamp: "2024-10-22T10:17:45Z",
			timestamp_processing: "2024-10-22T10:18:00Z"
		},
		index_name: "alert_index_002",
		index_type: "metrics"
	}
]
