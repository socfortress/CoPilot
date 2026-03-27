export type SafeAny = string | number | boolean | object | Date | null

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
