export interface InfluxDBAlert {
    time: string | Date
    check_name: string
    sensor_type: string
    severity: InfluxDBAlertSeverity
    message: string
    status: InfluxDBAlertStatus
    check_id?: string
}

export enum InfluxDBAlertSeverity {
    Ok = "ok",
    Info = "info",
    Warning = "warning",
    Critical = "critical"
}

export enum InfluxDBAlertStatus {
    Active = "active",
    Cleared = "cleared"
}

export interface InfluxDBAlertResponse {
    success: boolean
    message: string
    alerts: InfluxDBAlert[]
    total_count: number
    filtered_count: number
    active_alerts_count: number
    cleared_alerts_count: number
}

export interface InfluxDBAlertQueryParams {
    days?: number
    severity?: InfluxDBAlertSeverity[]
    check_name?: string
    sensor_type?: string
    status?: "active" | "cleared" | "all"
    latest_only?: boolean
    exclude_ok?: boolean
}

export interface InfluxDBCheckNamesResponse {
    success: boolean
    message: string
    check_names: string[]
    total_count: number
}
