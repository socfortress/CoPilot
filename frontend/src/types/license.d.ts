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
	id: number
	name: string
	email: string
	companyName: string
	created: number
}

export interface LicenseDataObject {
	id: number
	name: string
	stringValue: string
	intValue: number
}

export type LicenseFeatures = "REPORTING" | "THREAT INTEL" | "HUNTRESS" | "MIMECAST" | "CARBONBLACK"

export type LicenseKey = `${string}-${string}-${string}-${string}`

export interface SubscriptionFeature {
	id: number
	subscription_price_id: string
	name: LicenseFeatures
	price: number
	currency: string
	info: string
	short_description: string
	full_description: string
}

export interface CheckoutPayload {
	feature_id: number
	cancel_url: string
	success_url: string
	customer_email: string
	company_name: string
}

export interface LicenseCheckoutSession {
	after_expiration: string | null
	allow_promotion_codes: string | null
	amount_subtotal: number
	amount_total: number
	automatic_tax: AutomaticTax
	billing_address_collection: string | null
	cancel_url: string
	client_reference_id: string | null
	client_secret: string | null
	consent: string | null
	consent_collection: string | null
	created: number
	currency: string
	currency_conversion: string | null
	custom_fields: { [key: string]: string }
	custom_text: CustomText
	customer: string | null
	customer_creation: string
	customer_details: LicenseCheckoutCustomerDetails
	customer_email: string
	expires_at: number
	id: string
	invoice: string | null
	invoice_creation: InvoiceCreation | null
	livemode: boolean
	locale: string | null
	metadata: Metadata
	mode: string
	object: string
	payment_intent: string | null
	payment_link: string | null
	payment_method_collection: string
	payment_method_configuration_details: string | null
	payment_method_options: PaymentMethodOptions
	payment_method_types: string[]
	payment_status: string
	phone_number_collection: PhoneNumberCollection
	recovered_from: string | null
	setup_intent: string | null
	shipping_address_collection: string | null
	shipping_cost: string | null
	shipping_details: string | null
	shipping_options: { [key: string]: string }
	status: string
	submit_type: string | null
	subscription: string | null
	success_url: string
	total_details: TotalDetails
	ui_mode: string
	url: string
}

export interface AutomaticTax {
	enabled: boolean
	liability: string | null
	status: string | null
}

export interface CustomText {
	after_submit: string | null
	shipping_address: string | null
	submit: string | null
	terms_of_service_acceptance: string | null
}

export interface LicenseCheckoutCustomerDetails {
	address: string | null
	email: string
	name: string | null
	phone: string | null
	tax_exempt: string
	tax_ids: string | null
}

export interface InvoiceCreation {
	enabled: boolean
	invoice_data: InvoiceData
}

export interface InvoiceData {
	account_tax_ids: string
	custom_fields: string
	description: string
	footer: string
	issuer: string
	metadata: { [key: string]: string }
	rendering_options: string
}

export interface PaymentMethodOptions {
	card: Card
}

export interface Card {
	request_three_d_secure: string
}

export interface PhoneNumberCollection {
	enabled: boolean
}

export interface TotalDetails {
	amount_discount: number
	amount_shipping: number
	amount_tax: number
}

export interface Metadata {
	company_name: string
	feature_id: string
	product_id: string
	user_id: string
}
