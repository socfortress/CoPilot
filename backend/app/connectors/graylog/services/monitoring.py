from loguru import logger

from app.connectors.graylog.schema.monitoring import GraylogMessages
from app.connectors.graylog.schema.monitoring import GraylogMessagesResponse
from app.connectors.graylog.schema.monitoring import GraylogMetricsResponse
from app.connectors.graylog.schema.monitoring import GraylogThroughputMetrics
from app.connectors.graylog.schema.monitoring import GraylogThroughputMetricsCollection
from app.connectors.graylog.schema.monitoring import GraylogUncommittedJournalEntries
from app.connectors.graylog.utils.universal import send_get_request


def get_messages(page_number: int) -> GraylogMessagesResponse:
    """Get messages from Graylog."""
    logger.info("Getting messages from Graylog")
    params = {"page": page_number}
    messages_collected = send_get_request(endpoint="/api/system/messages", params=params)
    if messages_collected["success"]:
        graylog_messages_list = []
        for message in messages_collected["data"]["messages"]:
            graylog_message = GraylogMessages(
                caller=message["caller"],
                content=message["content"],
                node_id=message["node_id"],
                timestamp=message["timestamp"],
            )
            graylog_messages_list.append(graylog_message)
        return GraylogMessagesResponse(
            graylog_messages=graylog_messages_list,
            success=True,
            message="Messages collected successfully",
            total_messages=messages_collected["data"]["total"],
        )
    else:
        return GraylogMessagesResponse(graylog_messages=[], success=False, message="Failed to collect messages")


def fetch_metrics_from_graylog() -> dict:
    return send_get_request(endpoint="/api/system/metrics")


def fetch_uncommitted_journal_entries() -> dict:
    return send_get_request(endpoint="/api/system/journal")


def merge_metrics_data(throughput_metrics_collected: dict) -> dict:
    throughput_metrics = throughput_metrics_collected["data"]["gauges"]
    input_output_metrics = throughput_metrics_collected["data"]["counters"]
    return {**throughput_metrics, **input_output_metrics}


def filter_and_create_throughput_metrics(merged_metrics: dict) -> list:
    model_fields = [field_info.alias for field_info in GraylogThroughputMetricsCollection.__fields__.values()]
    throughput_metrics_list = [
        GraylogThroughputMetrics(metric=metric_name, value=metric_data.get("value", 0))
        for metric_name, metric_data in merged_metrics.items()
        if metric_name in model_fields
    ]
    return throughput_metrics_list


def get_metrics() -> GraylogMetricsResponse:
    logger.info("Getting metrics from Graylog")
    throughput_metrics_collected = fetch_metrics_from_graylog()
    uncommitted_journal_entries_collected = fetch_uncommitted_journal_entries()

    if throughput_metrics_collected["success"] and uncommitted_journal_entries_collected["success"]:
        merged_metrics = merge_metrics_data(throughput_metrics_collected)
        throughput_metrics_list = filter_and_create_throughput_metrics(merged_metrics)

        uncommitted_journal_entries = GraylogUncommittedJournalEntries(
            uncommitted_journal_entries=uncommitted_journal_entries_collected["data"]["uncommitted_journal_entries"],
        )

        return GraylogMetricsResponse(
            throughput_metrics=throughput_metrics_list,
            uncommitted_journal_entries=uncommitted_journal_entries.uncommitted_journal_entries,
            success=True,
            message="Metrics collected successfully",
        )
    else:
        return GraylogMetricsResponse(
            throughput_metrics=[],
            uncommitted_journal_entries=0,
            success=False,
            message="Failed to collect metrics",
        )
