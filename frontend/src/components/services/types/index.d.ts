export type ServiceItemType = "integration" | "network-connector"
export interface ServiceItemData {
	id: number
	name: string
	description: string
	details: string
	keys: {
		auth_key_name: string
	}[]
}
