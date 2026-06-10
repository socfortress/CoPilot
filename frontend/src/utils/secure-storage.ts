import SecureLSModule from "secure-ls"

type SecureLSConstructor = typeof SecureLSModule

const SecureLS: SecureLSConstructor =
	typeof SecureLSModule === "function"
		? SecureLSModule
		: (SecureLSModule as unknown as { default: SecureLSConstructor }).default

const secureLS = new SecureLS({
	encodingType: "aes",
	isCompression: false
})

const PREFIX_PERSISTED = "__persisted__"
const PREFIX_SESSION = "__persisted-session__"

export function persistentKey(options?: { session?: boolean }) {
	const prefix = options?.session ? PREFIX_SESSION : PREFIX_PERSISTED
	return (id: string) => `${prefix}${id}`
}

export function removePersistentSessionKey() {
	for (const key of secureLS.getAllKeys()) {
		if (key.includes(PREFIX_SESSION)) {
			secureLS.remove(key)
		}
	}
}

/** secure-ls returns parsed values; Storage adapters expect JSON strings. */
function normalizeStorageGetItem(value: unknown): string | null {
	if (value == null) return null
	if (typeof value === "string") return value === "" ? null : value
	return JSON.stringify(value)
}

export function secureLocalStorage(options?: { session?: boolean }) {
	return {
		getItem(key: string) {
			try {
				return normalizeStorageGetItem(secureLS.get(persistentKey({ session: options?.session })(key)))
			} catch (err) {
				console.warn(`[secureLocalStorage] Failed to get "${key}"`, err)
				return null
			}
		},

		setItem(key: string, value: string): void {
			try {
				secureLS.set(persistentKey({ session: options?.session })(key), value)
			} catch (err) {
				console.warn(`[secureLocalStorage] Failed to set "${key}"`, err)
			}
		},

		removeItem(key: string): void {
			try {
				secureLS.remove(persistentKey({ session: options?.session })(key))
			} catch (err) {
				console.warn(`[secureLocalStorage] Failed to remove "${key}"`, err)
			}
		}
	}
}

export function piniaStorage(options?: { session?: boolean }) {
	return {
		getItem: (key: string) => {
			try {
				return normalizeStorageGetItem(secureLS.get(persistentKey({ session: options?.session })(key)))
			} catch (err) {
				console.warn(`[piniaStorage] Failed to get "${key}"`, err)
				return null
			}
		},
		setItem: (key: string, value: unknown) => secureLS.set(persistentKey({ session: options?.session })(key), value)
	}
}

export { secureLS }
