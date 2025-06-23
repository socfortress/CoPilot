import _get from "lodash/get"

export function getMetaFieldLabel(key: string): string {
	const labelsMap: Record<string, string> = {
		id: "ID",
		customer_code: "Customer Code",
		integration_name: "Integration Name",
		network_connector_name: "Network Connector Name",
		graylog_input_id: "Graylog Input ID",
		graylog_index_id: "Graylog Index ID",
		graylog_stream_id: "Graylog Stream ID",
		graylog_pipeline_id: "Graylog Pipeline ID",
		graylog_content_pack_input_id: "Graylog Content Pack Input ID",
		graylog_content_pack_stream_id: "Graylog Content Pack Stream ID",
		grafana_org_id: "Grafana Org ID",
		grafana_datasource_uid: "Grafana Datasource UID"
	}

	return _get(labelsMap, key, key)
}
