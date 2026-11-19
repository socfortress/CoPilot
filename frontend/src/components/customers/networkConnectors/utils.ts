/**
 * Network connector keys the create form accepts empty. Every other key is required, as before.
 * The backend checks only that every key is sent; whether a value is needed depends on how the
 * connector is deployed.
 */
const OPTIONAL_AUTH_KEYS: Record<string, string[]> = {
	// Only the TLS input reads them: a SonicWall deployed over UDP never does.
	Sonicwall: ["TLS_CERT_FILE", "TLS_KEY_FILE"]
}

export function isOptionalAuthKey(networkConnectorName: string, authKeyName: string): boolean {
	return OPTIONAL_AUTH_KEYS[networkConnectorName]?.includes(authKeyName) ?? false
}

const AUTH_KEY_HINTS: Record<string, Record<string, string>> = {
	Sonicwall: {
		TLS_CERT_FILE: "TLS only: leave empty for UDP",
		TLS_KEY_FILE: "TLS only: leave empty for UDP"
	}
}

export function authKeyPlaceholder(networkConnectorName: string, authKeyName: string): string {
	return AUTH_KEY_HINTS[networkConnectorName]?.[authKeyName] ?? `Input ${authKeyName}...`
}
