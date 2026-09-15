import type { AxiosError } from "axios"
import axios from "axios"

/**
 * Whether a 401 means the caller's session is gone, as opposed to a 401 the
 * browser manufactured on our behalf (#1133).
 *
 * The browser drops `Authorization` whenever it follows a redirect to another
 * origin. Behind nginx the backend builds its trailing-slash redirect as an
 * absolute `http://` URL, so any request whose path the browser had already
 * rewritten (a `\` in a search term becomes `/`) came back as "Not authenticated"
 * for a user holding a perfectly valid token — and the interceptor logged them
 * out. A redirected response is recognisable: it was served from a URL other
 * than the one we asked for. Only a 401 served from the requested URL is the
 * backend rejecting *our* token.
 *
 * When either URL cannot be determined the historical behaviour (log out) is kept,
 * so an adapter without `responseURL` never turns a real expiry into a silent 401.
 */
export function isSessionExpiry(error: AxiosError): boolean {
	if (error.response?.status !== 401) return false

	const requested = requestedUrl(error)
	const served = servedUrl(error)
	if (!requested || !served) return true

	return requested === served
}

/** The absolute URL axios was asked for, normalised the way the browser will send it. */
function requestedUrl(error: AxiosError): string | null {
	if (!error.config) return null
	try {
		return new URL(axios.getUri(error.config), window.location.href).href
	} catch {
		return null
	}
}

/** The URL the response was actually served from — after any redirect the browser followed. */
function servedUrl(error: AxiosError): string | null {
	const request = error.request as { responseURL?: unknown } | undefined
	const served = request?.responseURL
	return typeof served === "string" && served ? served : null
}
