import type { AxiosError, AxiosResponse } from "axios"

export interface HttpCommonResponse {
	message: string
	detail?: string
	success: boolean
}

export interface ValidationError {
	type: string
	loc: (string | number)[]
	msg: string
	input?: any
}

export type OsTypesFull = "Unknown" | "Windows" | "MacOS" | "UNIX" | "Linux"
export type OsTypesLower = "linux" | "windows" | "macos"
export type Severity = "critical" | "high" | "medium" | "low" | "info"
export type ApiError = AxiosError<HttpCommonResponse>
export type ApiResponse<T = unknown> = AxiosResponse<HttpCommonResponse & T>
export type CommonResponse<T = unknown> = HttpCommonResponse & T

export interface Pagination {
	page: number
	pageSize: number
	order: "asc" | "desc"
}

export interface Tag {
	tag: string
	id: number
}
