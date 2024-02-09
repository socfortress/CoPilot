import { useFullscreen } from "@vueuse/core"
const { toggle, isFullscreen } = useFullscreen()

export function useFullscreenSwitch() {
	return {
		toggle: () => {
			toggle()
		},
		isFullscreen
	}
}
