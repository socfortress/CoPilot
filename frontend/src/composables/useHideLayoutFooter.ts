import { onBeforeMount, onBeforeUnmount } from "vue"
import { useThemeStore } from "@/stores/theme"

// :has() CSS relational pseudo-class not yet supported by Firefox
// (https://caniuse.com/css-has)
// at the moment this worker around permit to hide Layout Footer

export function useHideLayoutFooter() {
	const themeStore = useThemeStore()

	if (themeStore.isFooterShown) {
		onBeforeMount(() => {
			themeStore.setFooterShow(false)
		})
		onBeforeUnmount(() => {
			themeStore.setFooterShow(true)
		})
	}
}
