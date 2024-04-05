export interface License {
	product_id: number
	id: number
	key: string
	created: string
	expires: string
	period: number
	f1: boolean
	f2: boolean
	f3: boolean
	f4: boolean
	f5: boolean
	f6: boolean
	f7: boolean
	f8: boolean
	notes: string
	block: boolean
	global_id: number
	customer: LicenseCustomer
	activated_machines: { [key: string]: string }
	trial_activation: boolean
	max_no_of_machines: number
	allowed_machines: null | string
	data_objects: LicenseDataObject[]
	sign_date: string
	reseller: null | string
}

export interface LicenseCustomer {
	Id: number
	Name: string
	Email: string
	CompanyName: string
	Created: number
}

export interface LicenseDataObject {
	Id: number
	Name: string
	StringValue: string
	IntValue: number
}

export enum LicenseFeatures {
	"Reporting" = "REPORTING"
}

export type LicenseKey = `${string}-${string}-${string}-${string}`

export interface SubscriptionFeature {
	id: number
	subscription_price_id: string
	name: string
	price: number
	currency: string
	info: string
	short_description: string
	full_description: string
}
