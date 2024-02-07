export interface InfluxDBAlert {
	time: string | Date
	message: string
	checkID: string
	checkName: string
	level: InfluxDBAlertLevel
}

export enum InfluxDBAlertLevel {
	Ok = "ok",
	Crit = "crit"
}
