import SecureLS from "secure-ls"

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

export function secureLocalStorage(options?: { session?: boolean }) {
	return {
		getItem(key: string) {
			try {
				return secureLS.get(persistentKey({ session: options?.session })(key))
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
		getItem: (key: string) => secureLS.get(persistentKey({ session: options?.session })(key)),
		setItem: (key: string, value: unknown) => secureLS.set(persistentKey({ session: options?.session })(key), value)
	}
}

export { secureLS }
