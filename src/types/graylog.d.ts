export interface Message {
    caller: string
    content: string
    node_id: string
    timestamp: string
}

export interface ThroughputMetric {
    metric: string
    value: number
}

export interface Documents {
    count: number
    deleted: number
}

export interface OperationDetails {
    time_seconds: number
    total: number
}

// ShardDetails encapsulates all the details for both all_shards and primary_shards
export interface ShardDetails {
    documents: Documents
    flush: OperationDetails
    get: OperationDetails
    index: OperationDetails
    merge: OperationDetails
    open_search_contexts: number
    refresh: OperationDetails
    search_fetch: OperationDetails
    search_query: OperationDetails
    segments: number
    store_size_bytes: number
}

// Routing information for each index
export interface Routing {
    active: boolean
    id: number
    node_hostname: string
    node_id: string
    node_name: string
    primary: boolean
    relocating_to: null | string
    state: string
}

// Interface for each individual index like 'wazuh_00001'
export interface IndexDetails {
    all_shards: ShardDetails
    primary_shards: ShardDetails
    reopened: boolean
    routing: Routing[]
}

// Main interface encapsulating the entire JSON structure of IndexData
export interface IndexData {
    index_names: string[]
    indices: { [key: string]: IndexDetails }
    message: string
    success: boolean
}

// Graylog Inputs

export enum InputState {
    RUNNING = "RUNNING",
    STOPPED = "STOPPED"
}

export interface ConfiguredInput {
    port: number
    title: string
}

export interface RunningInput {
    port: number
    state: string
    title: string
}

export interface ConfiguredInputsData {
    configured_inputs: ConfiguredInput[]
    message: string
    success: boolean
}

export interface RunningInputsData {
    inputs: RunningInput[]
    message: string
    success: boolean
}

export interface Inputs {
    configured_inputs: ConfiguredInputsData
    running_inputs: RunningInputsData
}

// Stream Rule
export interface StreamRule {
    description: null | string
    field: string
    id: string
    inverted: boolean
    stream_id: string
    type: number
    value: string
}

// Stream
export interface Stream {
    content_pack: null | string
    created_at: string
    creator_user_id: string
    description: string
    disabled: boolean
    id: string
    index_set_id: string
    is_default: boolean
    is_editable: boolean
    matching_type: string
    outputs: any[] // Replace with the appropriate type if known
    remove_matches_from_default_stream: boolean
    rules: StreamRule[]
    title: string
}

// Streams Array
export interface Streams extends Array<Stream> {}
