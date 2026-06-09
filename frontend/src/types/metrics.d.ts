export interface MetricsResponse<T = Record<string, unknown>> {
	data: T
}

export interface MetricsCpuData {
	cpu_usage_system?: TimeSeriesData
	cpu_usage_user?: TimeSeriesData
	cpu_iowait?: TimeSeriesData
	cpu_softirq?: TimeSeriesData
}

export interface HostsResponse {
	success: boolean
	message: string
	hosts: string[]
}

export interface TimeSeriesPoint {
	time: string
	value: number
}

export type TimeSeriesData = Record<string, TimeSeriesPoint[]>

export interface MetricsMemoryData {
	swap_total?: number | null
	swap_free?: number | null
	mem_used?: TimeSeriesData
}

export interface MetricsDisksData {
	disk_total?: number | null
	disk_usage?: TimeSeriesData
	disk_io?: TimeSeriesData
}

export interface MetricsProcessesData {
	running?: number | null
	sleeping?: number | null
	unknown?: number | null
	zombies?: number | null
	status?: TimeSeriesData
}

export interface MetricsNetworkData {
	tcp_established?: number | null
	traffic?: TimeSeriesData
	interface_errors?: TimeSeriesData
}

export interface MetricsKernelData {
	interrupts?: TimeSeriesData
	processes_forked?: TimeSeriesData
}

export interface MetricsSummaryData {
	uptime?: number | null
	total_mem?: number | null
	cpus?: number | null
	total_processes?: number | null
	cpu_idle?: number | null
	logged_on_users?: number | null
	swap_free?: number | null
	load?: TimeSeriesData
}
