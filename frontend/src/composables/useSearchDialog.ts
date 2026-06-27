import { ref } from "vue"

const listener = ref<(() => void) | undefined>()
let addCustomerHandler: (() => void) | undefined

export function useSearchDialog() {
	return {
		trigger: (cb: () => void): void => {
			listener.value = cb
		},
		open: (): void => {
			listener.value?.()
		},
		registerAddCustomer: (handler: () => void): (() => void) => {
			addCustomerHandler = handler
			return () => {
				if (addCustomerHandler === handler) {
					addCustomerHandler = undefined
				}
			}
		},
		openAddCustomer: (): void => {
			addCustomerHandler?.()
		}
	}
}
