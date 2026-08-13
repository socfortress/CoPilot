export interface CustomerSecurityUser {
	id: number
	username: string
	email: string
	role_id?: number | null
	role_name?: string | null
	last_login_at?: string | null
	totp_enabled: boolean
}

/**
 * A temporary-password email template, as the send dialog's picker needs it.
 *
 * These are rows in the shared `notification_template` table scoped to the
 * `temp_password_issued` trigger — the same ones the Message Templates editor
 * writes. This is a narrower projection: the picker needs to label them, not
 * render them.
 */
export interface TempPasswordTemplateOption {
	id: number
	name: string
	description?: string | null
	format: string
	/** null means shared with every customer. */
	customer_code?: string | null
	/** Seeded built-in. Read-only in the editor; still selectable here. */
	is_default: boolean
}

export interface TempPasswordEmailOptions {
	templates: TempPasswordTemplateOption[]
	/** What a send with no override would use. null means the built-in plaintext body. */
	resolved_template_id?: number | null
	/** Which customer's template and branding apply. null for a multi-customer user. */
	customer_code?: string | null
	smtp_configured: boolean
}

export interface TempPasswordEmailPreview {
	subject?: string | null
	body: string
	/** "html" or "text" — tells the dialog whether to sandbox-iframe the body. */
	format: string
	/** Non-null when rendering failed; shown instead of the body. */
	error?: string | null
}
