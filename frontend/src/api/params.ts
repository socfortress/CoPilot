/** Builds the `?search=&limit=` query params shared by every search-palette endpoint. */
export function searchLimitParams(query: { search?: string; limit?: number }): Record<string, number | string> {
	const params: Record<string, number | string> = {}
	if (query.search) params.search = query.search
	if (query.limit !== undefined) params.limit = query.limit
	return params
}
