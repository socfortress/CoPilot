import { useThemeStore } from "@/stores/theme"

export function useThemeSwitch() {
	const themeStore = useThemeStore()

	return {
		toggle: () => {
			themeStore.toggleTheme()
		}
	}
}
