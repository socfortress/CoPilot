import * as jose from "jose"

/**
 * @param token jwt token
 * @param threshold in seconds
 */
export function isJwtExpiring(token: string, threshold: number): boolean {
	try {
		if (!token) {
			return false
		}

		const { exp } = jose.decodeJwt(token)
		const now = new Date().getTime() / 1000
		const gap = now + threshold

		if (!exp) {
			return true
		}

		return exp > now && exp < gap
	} catch (err) {
		return false
	}
}
