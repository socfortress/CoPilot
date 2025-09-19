import type { AxiosError, AxiosResponse } from "axios"
import type { FlaskBaseResponse } from "./flask"

export type OsTypesFull = "Unknown" | "Windows" | "MacOS" | "UNIX" | "Linux"
export type OsTypesLower = "linux" | "windows" | "macos"
export type SafeAny = string | number | boolean | object
export type ApiError = AxiosError<FlaskBaseResponse>
export type ApiCommonResponse<T = unknown> = AxiosResponse<FlaskBaseResponse & T>
export type DeepNullable<T> = {
	[K in keyof T]: DeepNullable<T[K]> | null
}

export type Nullable<T> = {
	[K in keyof T]: T[K] | null
}

export type RecursiveKeyOf<TObj extends object> = {
	[TKey in keyof TObj & (string | number)]: TObj[TKey] extends object
		? `${TKey}` | `${TKey}.${RecursiveKeyOf<TObj[TKey]>}`
		: `${TKey}`
}[keyof TObj & (string | number)]
