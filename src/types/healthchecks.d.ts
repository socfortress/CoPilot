export interface InfluxDBAlert {
	time: string | Date
	message: string
	checkID: string
	checkName: string
	level: string
}
