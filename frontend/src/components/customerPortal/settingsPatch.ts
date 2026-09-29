import type { CustomerPortalSettingsPatch } from "@/api/endpoints/customer-portal"

/** The editable global settings, with the logo as a data URL. */
export interface SettingsFields {
	title: string | null
	logo: string | null
	brand_color: string | null
}

const DATA_URL_REGEX = /^data:([^;,]+);base64,(.+)$/

/** Split a `data:<mime>;base64,<payload>` URL; null when it is not one. */
export function parseLogoDataUrl(logo: string | null): { base64: string; mime_type: string } | null {
	const [, mime_type, base64] = logo?.match(DATA_URL_REGEX) ?? []
	return mime_type && base64 ? { mime_type, base64 } : null
}

/**
 * The `PATCH /customer_portal/settings` body that turns `saved` into `current`: only the
 * fields that changed, a cleared one as a `reset`. Null when nothing changed.
 *
 * `POST` rewrote every field, so saving a new title re-uploaded the logo (up to 5MB).
 */
export function buildSettingsPatch(saved: SettingsFields, current: SettingsFields): CustomerPortalSettingsPatch | null {
	const patch: CustomerPortalSettingsPatch = {}
	const reset: NonNullable<CustomerPortalSettingsPatch["reset"]> = []

	const title = current.title?.trim() || null
	if (title !== (saved.title?.trim() || null)) {
		if (title) patch.title = title
		else reset.push("title")
	}

	if ((current.logo || null) !== (saved.logo || null)) {
		const logo = parseLogoDataUrl(current.logo)
		if (logo) {
			patch.logo_base64 = logo.base64
			patch.logo_mime_type = logo.mime_type
		} else {
			reset.push("logo")
		}
	}

	const color = current.brand_color || null
	if (color !== (saved.brand_color || null)) {
		if (color) patch.brand_color = color
		else reset.push("brand_color")
	}

	if (reset.length) patch.reset = reset
	return Object.keys(patch).length ? patch : null
}
