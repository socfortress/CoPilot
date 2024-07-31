from sigma.processing.transformations import (
    AddConditionTransformation,
    ChangeLogsourceTransformation,
)
from sigma.processing.conditions import LogsourceCondition
from sigma.processing.pipeline import ProcessingItem, ProcessingPipeline
from sigma.pipelines.base import Pipeline

sysmon_generic_logsource_eventid_mapping = (
    {  # map generic Sigma log sources to Sysmon event ids
        "process_creation": 1,
        "file_change": 2,
        "network_connection": 3,
        "process_termination": 5,
        "sysmon_status": [4, 16],
        "driver_load": 6,
        "image_load": 7,
        "create_remote_thread": 8,
        "raw_access_thread": 9,
        "process_access": 10,
        "file_event": 11,
        "registry_add": 12,
        "registry_delete": 12,
        "registry_set": 13,
        "registry_rename": 14,
        "registry_event": [12, 13, 14],
        "create_stream_hash": 15,
        "pipe_created": [17, 18],
        "wmi_event": [19, 20, 21],
        "dns_query": 22,
        "file_delete": [23, 26],
        "clipboard_capture": 24,
        "process_tampering": 25,
        "sysmon_error": 255,
    }
)


@Pipeline
def sysmon_pipeline() -> ProcessingPipeline:
    return ProcessingPipeline(
        name="Generic Log Sources to Sysmon Transformation",
        priority=10,
        items=[
            processing_item
            for log_source, event_id in sysmon_generic_logsource_eventid_mapping.items()
            for processing_item in (
                ProcessingItem(
                    identifier=f"sysmon_{log_source}_eventid",
                    transformation=AddConditionTransformation(
                        {
                            "EventID": event_id,
                        }
                    ),
                    rule_conditions=[
                        LogsourceCondition(category=log_source, product="windows")
                    ],
                ),
                ProcessingItem(
                    identifier=f"sysmon_{log_source}_logsource",
                    transformation=ChangeLogsourceTransformation(
                        product="windows",
                        service="sysmon",
                        category=log_source,
                    ),
                    rule_conditions=[
                        LogsourceCondition(category=log_source, product="windows")
                    ],
                ),
            )
        ],
    )
