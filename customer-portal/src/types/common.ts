import type { AxiosError, AxiosResponse } from "axios"

export interface HttpCommonResponse {
	message: string
	success: boolean
}

export interface ValidationError {
	type: string
	loc: (string | number)[]
	msg: string
	input?: any
}

export interface HttpError {
	detail: string | ValidationError[]
}

export type OsTypesFull = "Unknown" | "Windows" | "MacOS" | "UNIX" | "Linux"
export type OsTypesLower = "linux" | "windows" | "macos"
export type Severity = "critical" | "high" | "medium" | "low" | "info"
export type Status =
	| "pending"
	| "running"
	| "completed"
	| "failed"
	| "not_provided"
	| "unknown"
	| "error"
	| "success"
	| "progress"
	| "failure"
export type ApiError = AxiosError<HttpError>
export type ApiResponse<T = unknown> = AxiosResponse<HttpCommonResponse & T>
export type CommonResponse<T = unknown> = HttpCommonResponse & T

export interface PaginationMetadata {
	currentPage: number
	pageSize: number
	totalItems: number
	totalPages: number
	hasNextPage: boolean
	hasPreviousPage: boolean
	startIndex: number
	endIndex: number
}
