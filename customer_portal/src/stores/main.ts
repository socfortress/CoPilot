import type { LoadingBarInst } from "naive-ui/es/loading-bar/src/LoadingBarProvider"
import { acceptHMRUpdate, defineStore } from "pinia"

export const useMainStore = defineStore("main", {
	state: () => ({
		forceRefresh: Date.now(),
		loadingBar: null as LoadingBarInst | null
	}),
	actions: {
		softReload() {
			this.forceRefresh = Date.now()
			this.loadingBar?.start()
			setTimeout(() => {
				this.loadingBar?.finish()
			}, 1000)
		},
		setLoadingBar(loadingBar: LoadingBarInst) {
			this.loadingBar = loadingBar
		}
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useMainStore, import.meta.hot))
}
