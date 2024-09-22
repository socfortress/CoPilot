import type { AxiosError, AxiosResponse } from "axios"
import type { FlaskBaseResponse } from "./flask"

export type OsTypesFull = "Unknown" | "Windows" | "MacOS" | "UNIX" | "Linux"
export type OsTypesLower = "linux" | "windows" | "macos"
export type SafeAny = string | number | object
export type ApiError = AxiosError<FlaskBaseResponse>
export type ApiCommonResponse<T = unknown> = AxiosResponse<FlaskBaseResponse & T>
