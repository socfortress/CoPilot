export interface AlertsListFilter {
	type: AlertsFilterTypes
	label: string
	value: string | string[] | AlertStatus | null
}
