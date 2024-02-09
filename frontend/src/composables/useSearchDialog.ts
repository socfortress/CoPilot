import { ref } from "vue"

const listener = ref()
export function useSearchDialog() {
	return {
		trigger: (cb: () => void): void => {
			listener.value = cb
		},
		open: (): void => {
			listener.value && listener.value()
		}
	}
}
