export type OsTypesFull = "Unknown" | "Windows" | "MacOS" | "UNIX" | "Linux"
export type OsTypesLower = "linux" | "windows" | "macos"
export type SafeAny = string | number | object
export type ApiError = AxiosError<FlaskBaseResponse>
export type ApiCommonResponse<T extends object = {}> = AxiosResponse<FlaskBaseResponse & T>
