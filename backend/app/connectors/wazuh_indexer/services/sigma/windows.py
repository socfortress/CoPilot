from sigma.pipelines.common import generate_windows_logsource_items
from sigma.processing.transformations import (
    FieldMappingTransformation,
    AddFieldnamePrefixTransformation,
)
from sigma.processing.conditions import (
    LogsourceCondition,
    IncludeFieldCondition,
    FieldNameProcessingItemAppliedCondition,
)
from sigma.processing.pipeline import ProcessingItem, ProcessingPipeline

ecs_windows_variable_mappings = {
    "FileVersion": (
        ("category", "process_creation", "process.pe.file_version"),
        ("category", "image_load", "file.pe.file_version"),
    ),
    "Description": (
        ("category", "process_creation", "process.pe.description"),
        ("category", "image_load", "file.pe.description"),
        ("category", "sysmon_error", "winlog.event_data.Description"),
    ),
    "Product": (
        ("category", "process_creation", "process.pe.product"),
        ("category", "image_load", "file.pe.product"),
    ),
    "Company": (
        ("category", "process_creation", "process.pe.company"),
        ("category", "image_load", "file.pe.company"),
    ),
    "OriginalFileName": (
        ("category", "process_creation", "data_win_eventdata_image"),
        ("category", "process_creation", "data_win_eventdata_image"),
        ("category", "image_load", "file.pe.original_file_name"),
    ),
    "CommandLine": (
        ("category", "process_creation", "data_win_eventdata_commandLine"),
        ("service", "security", "data_win_eventdata_commandLine"),
        ("service", "powershell-classic", "powershell.command.value"),
    ),
    "Protocol": (("category", "network_connection", "network.transport"),),
    "Initiated": (("category", "network_connection", "network.direction"),),
    "Signature": (
        ("category", "driver_loaded", "file.code_signature.subject_name"),
        ("category", "image_loaded", "file.code_signature.subject_name"),
    ),
    "EngineVersion": (("service", "powershell-classic", "powershell.engine.version"),),
    "HostVersion": (
        ("service", "powershell-classic", "powershell.process.executable_version"),
    ),
    "SubjectLogonId": (("service", "security", "winlog.logon.id"),),
    "ServiceName": (("service", "security", "service.name"),),
    "SubjectDomainName": (("service", "security", "user.domain"),),
    "SubjectUserName": (("service", "security", "user.name"),),
    "SubjectUserSid": (("service", "security", "user.id"),),
    "TargetLogonId": (("service", "security", "winlog.logon.id"),),
}


def ecs_windows() -> ProcessingPipeline:
    return ProcessingPipeline(
        name="Elastic Common Schema (ECS) Windows log mappings from Winlogbeat from version 7",
        priority=20,
        allowed_backends=("elasticsearch", "eql", "lucene", "opensearch"),
        items=generate_windows_logsource_items("data_win_system_channel", "{source}")
        + [  # Variable field mapping depending on category/service
            ProcessingItem(
                identifier=f"elasticsearch_windows-{field}-{logsrc_field}-{logsrc}",
                transformation=FieldMappingTransformation({field: mapped}),
                rule_conditions=[
                    LogsourceCondition(
                        **{
                            "product": "windows",
                            logsrc_field: logsrc,
                        }
                    ),
                ],
            )
            for field, mappings in ecs_windows_variable_mappings.items()
            for (logsrc_field, logsrc, mapped) in mappings
        ]
        + [
            ProcessingItem(  # Field mappings
                identifier="ecs_windows_field_mapping",
                transformation=FieldMappingTransformation(
                    {
                    'Accesses': 'data_win_eventdata_accesses',
                    'AccessList': 'data_win_eventdata_accessList',
                    'AccessMask': 'data_win_eventdata_accessMask',
                    'AccountName': 'data_win_eventdata_targetUserName',
                    'Action': 'data_win_eventdata_action',
                    'AllowedToDelegateTo': 'data_win_eventdata_allowedToDelegateTo',
                    'Application': 'data_win_eventdata_application',
                    'ApplicationPath': 'data_win_eventdata_applicationPath',
                    'AttributeLDAPDisplayName': 'data_win_eventdata_attributeLDAPDisplayName',
                    'AttributeValue': 'data_win_eventdata_attributeValue',
                    'AuditPolicyChanges': 'data_win_evendata_auditPolicyChanges',
                    'AuditSourceName': 'data_win_eventdata_auditSourceName',
                    'AuthenticationPackage': 'data_win_eventdata_authenticationPackageName',
                    'AuthenticationPackageName': 'data_win_eventdata_authenticationPackageName',
                    'CallTrace': 'data_win_eventdata_callTrace',
                    'Caption': 'data_win_eventdata_caption',
                    'Channel': 'data_win_eventdata_channel',
                    'ChildImage': 'data_win_eventdata_image',
                    'CommandLine': 'data_win_eventdata_commandLine',
                    'Company': 'data_win_eventdata_company',
                    'ComputerName': 'data_win_system_computer',
                    'ContextInfo': 'data_win_system_contextInfo',
                    'CurrentDirectory': 'data_win_eventdata_currentDirectory',
                    'Description': 'data_win_eventdata_description',
                    'DestAddress': 'data_win_eventdata_destAddress',
                    'Destination': 'data_win_eventdata_destination',
                    'DestinationHostname': 'data_win_eventdata_destinationHostname',
                    'DestinationIp': 'data_win_eventdata_destinationIp',
                    'DestinationIsIpv6': 'data_win_eventdata_destinationIsIpv6',
                    'DestinationPort': 'data_win_eventdata_destinationPort',
                    'Details': 'data_win_eventdata_details',
                    'DeviceClassName': 'data_win_eventdata_deviceClassName',
                    'DeviceDescription': 'data_win_eventdata_deviceDescription',
                    'DeviceName': 'data_win_eventdata_deviceName',
                    'DestPort': 'data_win_eventdata_destinationPort',
                    'EngineVersion': 'data_win_eventdata_engineVersion',
                    'EventID': 'data_win_system_eventID',
                    'EventType': 'data_win_eventdata_eventType',
                    'FailureCode': 'data_win_eventdata_failureCode',
                    'FileVersion': 'data_win_eventdata_fileVersion',
                    'FilterName': 'data_win_evendata_filterName',
                    'FilterOrigin': 'data_win_eventdata_filterOrigin',
                    'FolderPath': 'data_win_eventdata_image',
                    'GrantedAccess': 'data_win_eventdata_grantedAccess',
                    'Hash': 'data_win_eventdata_hashes',
                    'Hashes': 'data_win_eventdata_hashes',
                    'HostApplication': 'data_win_eventdata_hostApplication',
                    'HostName': 'data_win_eventdata_hostName',
                    'HostVersion': 'data_win_eventdata_hostVersion',
                    'Image': 'data_win_eventdata_image',
                    'ImageName': 'data_win_evendata_imageName',
                    'ImagePath': 'data_win_eventdata_imagePath',
                    'ImageLoaded': 'data_win_eventdata_imageLoaded',
                    'ImpHash': 'data_win_eventdata_impHash',
                    'Imphash': 'data_win_eventdata_imphash',
                    'ImpersonationLevel': 'data_win_eventdata_impersonationLevel',
                    'Initiated': 'data_win_eventdata_initiated',
                    'IntegrityLevel': 'data_win_eventdata_integrityLevel',
                    'IpAddress': 'data_win_eventdata_ipAddress',
                    'KeyLength': 'data_win_eventdata_keyLength',
                    'Keywords': 'data_win_eventdata_keywords',
                    'LayerRTID': 'data_win_eventdata_layerRTID',
                    'Level': 'data_win_system_level',
                    'LogonGuid': 'data_win_eventdata_logonGuid',
                    'LogonId': 'data_win_eventdata_logonId',
                    'LogonProcessName': 'data_win_eventdata_logonProcessName',
                    'LogonType': 'data_win_eventdata_logonType',
                    'md5': 'data_win_eventdata_hashes',
                    'Message': 'data_win_system_message',
                    'ModifyingApplication': 'data_win_system_modifyingApplication',
                    'NewName': 'data_win_eventdata_newName',
                    'NewTargetUserName': 'data_win_evendata_newTargetUserName',
                    'NewUacValue': 'data_win_eventdata_newUacValue',
                    'NewValue': 'data_win_eventdata_newValue',
                    'ObjectClass': 'data_win_eventdata_objectClass',
                    'ObjectName': 'data_win_eventdata_objectName',
                    'ObjectServer': 'data_win_eventdata_objectServer',
                    'ObjectType': 'data_win_eventdata_objectType',
                    'ObjectValueName': 'data_win_eventdata_objectValueName',
                    'OldUacValue': 'data_win_eventdata_oldUacValue',
                    'Origin': 'data_win_eventdata_origin',
                    'OriginalFileName': 'data_win_eventdata_originalFileName',
                    'PackageName': 'data_win_eventdata_packageName',
                    'Param1': 'data_win_evendata_param1',
                    'Param2': 'data_win_evendata_param2',
                    'Param3': 'data_win_evendata_param3',
                    'Param4': 'data_win_evendata_Param4',
                    'Param5': 'data_win_evendata_param5',
                    'Param6': 'data_win_evendata_param6',
                    'Param7': 'data_win_evendata_param7',
                    'Param8': 'data_win_evendata_Param8',
                    'Param9': 'data_win_evendata_Param9',
                    'Param10': 'data_win_evendata_Param10',
                    'ParentCommandLine': 'data_win_eventdata_parentCommandLine',
                    'ParentImage': 'data_win_eventdata_parentImage',
                    'ParentIntegrityLevel': 'data_win_eventdata_parentIntegrityLevel',
                    'ParentProcessGuid': 'data_win_eventdata_parentProcessGuid',
                    'ParentUser': 'data_win_eventdata_parentUser',
                    'Payload': 'data_win_eventdata_payload',
                    'PipeName': 'data_win_eventdata_pipeName',
                    'PrivilegeList': 'data_win_eventdata_privilegeList',
                    'ProcessCommandLine': 'data_win_eventdata_commandLine',
                    'ProcessID': 'data_win_eventdata_processId',
                    'ProcessName': 'data_win_eventdata_processName',
                    'ProcessPath': 'data_win_eventdata_processPath',
                    'Product': 'data_win_eventdata_product',
                    'Properties': 'data_win_eventdata_properties',
                    'ProviderContextName': 'data_win_evendata_providerContextName',
                    'ProviderName': 'data_win_eventdata_providerName',
                    'Provider_Name': 'data_win_eventdata_providerName',
                    'QueryName': 'data_win_eventdata_queryName',
                    'RelativeTargetName': 'data_win_eventdata_relativeTargetName',
                    'RemoteAddress': 'data_win_eventdata_remoteAddress',
                    'SamAccountName': 'data_win_eventdata_samAccountName',
                    'ScriptBlockText': 'data_win_eventdata_scriptBlockText',
                    'Service': 'data_win_eventdata_service',
                    'ServerName': 'data_win_eventdata_serverName',
                    'ServiceFileName': 'data_win_eventdata_serviceFileName',
                    'ServiceName': 'data_win_eventdata_serviceName',
                    'ServiceStartType': 'data_win_evendata_serviceStartType',
                    'ServiceType': 'data_win_evendata_serviceType',
                    'sha1': 'data_win_eventdata_hashes',
                    'sha256': 'data_win_eventdata_hashes',
                    'ShareName': 'data_win_eventdata_shareName',
                    'SidHistory': 'data_win_eventdata_sidHistory',
                    'Signed': 'data_win_eventdata_signed',
                    'Source': 'data_win_eventdata_source',
                    'Source_Name': 'data_win_eventdata_sourceName',
                    'SourceAddress': 'data_win_eventdata_sourceAddress',
                    'SourceImage': 'data_win_eventdata_sourceImage',
                    'SourceNetworkAddress': 'data_win_eventdata_ipAddress',
                    'TargetObject': 'data_win_eventdata_targetObject',
                    }
                ),
                rule_conditions=[LogsourceCondition(product="windows")],
            ),
            ProcessingItem(  # Prepend each field that was not processed by previous field mapping transformation with "winlog.event_data."
                identifier="ecs_windows_winlog_eventdata_prefix",
                #transformation=AddFieldnamePrefixTransformation("winlog.event_data."),
                transformation=AddFieldnamePrefixTransformation(""),
                field_name_conditions=[
                    FieldNameProcessingItemAppliedCondition(
                        "ecs_windows_field_mapping"
                    ),
                    IncludeFieldCondition(fields=["\\w+\\."], type="re"),
                ],
                field_name_condition_negation=True,
                field_name_condition_linking=any,
                rule_conditions=[LogsourceCondition(product="windows")],
            ),
        ],
    )


def ecs_windows_old() -> ProcessingPipeline:
    return ProcessingPipeline(
        name="Elastic Common Schema (ECS) Windows log mappings from Winlogbeat up to version 6",
        priority=20,
        allowed_backends=("elasticsearch", "eql", "lucene", "opensearch"),
        items=generate_windows_logsource_items("winlog.channel", "{source}")
        + [
            ProcessingItem(  # Field mappings
                identifier="ecs_windows_field_mapping",
                transformation=FieldMappingTransformation(
                    {
                        "EventID": "event_id",
                        "Channel": "winlog.channel",
                    }
                ),
                rule_conditions=[LogsourceCondition(product="windows")],
            ),
            ProcessingItem(  # Prepend each field that was not processed by previous field mapping transformation with "winlog.event_data."
                identifier="ecs_windows_eventdata_prefix",
                transformation=AddFieldnamePrefixTransformation("event_data."),
                field_name_conditions=[
                    FieldNameProcessingItemAppliedCondition(
                        "ecs_windows_field_mapping"
                    ),
                    IncludeFieldCondition(fields=["\\w+\\."], type="re"),
                ],
                field_name_condition_negation=True,
                field_name_condition_linking=any,
                rule_conditions=[LogsourceCondition(product="windows")],
            ),
        ],
    )
