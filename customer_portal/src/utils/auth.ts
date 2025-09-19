import { decodeJwt } from "jose"
import _toNumber from "lodash/toNumber"

export function isDebounceTimeOver(lastCheck: Date | null) {
	const debounceTime = 30 // 30 seconds debounce for customer portal
	return !lastCheck || lastCheck.getTime() + _toNumber(debounceTime) * 1000 < Date.now()
}

/**
 * @param token jwt token
 * @param threshold in seconds
 */
export function isJwtExpiring(token: string, threshold: number): boolean {
	try {
		const { exp } = decodeJwt(token) || {}
		return exp ? Date.now() / 1000 > exp - threshold : true
	} catch {
		return false
	}
}
