export interface AvailableContentPack {
	name: string
	description: string
}

export interface AvailableInfluxDbCheck {
	name: string
	description: string
	check_name: string
	provisioned: boolean
}

export interface ProvisionedInfluxDbCheck {
	name: string
	check_name: string
	action: "created" | "updated" | "skipped"
	check_id?: string | null
}
