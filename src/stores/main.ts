import { defineStore, acceptHMRUpdate } from "pinia"
import { type LoadingBarInst } from "naive-ui/es/loading-bar/src/LoadingBarProvider"

export const useMainStore = defineStore("main", {
	state: () => ({
		forceRefresh: new Date().getTime(),
		loadingBar: null as LoadingBarInst | null
	}),
	actions: {
		softReload() {
			this.forceRefresh = new Date().getTime()
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
