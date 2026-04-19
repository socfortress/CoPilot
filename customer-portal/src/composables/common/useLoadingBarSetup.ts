import { useLoadingBar } from "naive-ui"
import { onMounted } from "vue"
import { useRouter } from "vue-router"
import { useMainStore } from "@/stores/main"

export function useLoadingBarSetup() {
	const router = useRouter()
	const mainStore = useMainStore()

	onMounted(() => {
		const loadingBar = useLoadingBar()
		router.beforeEach((to, current) => {
			if (to.path !== current.path) {
				loadingBar?.start()
			}
		})
		router.afterEach(() => loadingBar?.finish())
		mainStore.setLoadingBar(loadingBar)
	})
}
