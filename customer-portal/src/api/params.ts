import type { AxiosRequestConfig } from "axios"

/**
 * Merge an optional multi-customer filter into an axios request config.
 *
 * When `customerCodes` has entries they are appended as repeated query params
 * (`customer_codes=a&customer_codes=b`) — the shape FastAPI's
 * `List[str] = Query(...)` expects — via `paramsSerializer: { indexes: null }`.
 * When empty/undefined the original config is returned untouched, so callers
 * fall back to "all accessible customers" exactly as before.
 */
export function withCustomerCodes(customerCodes?: string[], config: AxiosRequestConfig = {}): AxiosRequestConfig {
	if (!customerCodes?.length) {
		return config
	}

	return {
		...config,
		params: { ...(config.params ?? {}), customer_codes: customerCodes },
		paramsSerializer: { indexes: null }
	}
}
