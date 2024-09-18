export interface AvailableMonitoringAlert {
	name: string
	value: string
}

export interface MonitoringAlert {
	id: number
	alert_id: string
	alert_index: string
	customer_code: string
	alert_source: string
}

export enum CustomProvisionPriority {
	LOW = 1,
	MEDIUM = 2,
	HIGH = 3
}
