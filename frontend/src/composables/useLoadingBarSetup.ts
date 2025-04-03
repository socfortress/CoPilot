import { useMainStore } from "@/stores/main"
import { useLoadingBar } from "naive-ui"
import { onMounted } from "vue"
import { useRouter } from "vue-router"

export function useLoadingBarSetup() {
	const router = useRouter()
	const mainStore = useMainStore()

	onMounted(() => {
		const loadingBar = useLoadingBar()
		router.beforeEach(() => loadingBar?.start())
		router.afterEach(() => loadingBar?.finish())
		mainStore.setLoadingBar(loadingBar)
	})
}
