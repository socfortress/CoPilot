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

/** Every key leading to a string, dotted (`alerts.list.title`): what a translation call may name. */
export type StringKeys<T, Prefix extends string = ""> = {
	[K in keyof T]: T[K] extends string
		? `${Prefix}${Extract<K, string>}`
		: T[K] extends object
			? StringKeys<T[K], `${Prefix}${Extract<K, string>}.`>
			: never
}[keyof T]
