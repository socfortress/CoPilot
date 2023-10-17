import { useThemeStore } from "@/stores/theme"

export function useThemeSwitch() {
	return {
		toggle: () => {
			useThemeStore().toggleTheme()
		}
	}
}
