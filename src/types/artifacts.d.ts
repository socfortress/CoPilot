export interface Artifact {
	description: string
	name: string
}

export interface CollectResult {
	Pid: number
	Name: string
	Family: CollectResultFamily
	Type: CollectResultType
	Status: CollectResultStatus
	"Laddr.IP": string
	"Laddr.Port": number
	"Raddr.IP": string
	"Raddr.Port": number
	Timestamp: string
}

export enum CollectResultFamily {
	IPv4 = "IPv4",
	IPv6 = "IPv6"
}

export enum CollectResultStatus {
	Empty = "",
	Estab = "ESTAB",
	Listen = "LISTEN"
}

export enum CollectResultType {
	TCP = "TCP",
	UDP = "UDP"
}

export interface CommandResult {
	Stdout: string
	Stderr: string
	ReturnCode: number
	Complete: boolean
}

export interface QuarantineResult {
	Time: string
	Result: string
}
