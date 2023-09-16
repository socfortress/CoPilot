import { ENavPos, EToolbar, EViewAnimation, State, StateLayout } from "@/types/layout.d"
import { defineStore, acceptHMRUpdate } from "pinia"

export const useMainStore = defineStore("main", {
    state: (): State => ({
        layout: {
            navPos: ENavPos.left, //top, bottom, left, right, false
            toolbar: EToolbar.top, //top, bottom, false
            footer: true, //above, below, false
            boxed: false, //true, false
            roundedCorners: false, //true, false
            viewAnimation: EViewAnimation.fadeTop // fade-left, fade-right, fade-top, fade-top-in-out, fade-bottom, fade-bottom-in-out, fade, false
        },
        splashScreen: true,
        logged: true
    }),
    actions: {
        setLayout(payload: Partial<StateLayout>) {
            if (payload && payload.navPos !== undefined) this.layout.navPos = payload.navPos

            if (payload && payload.toolbar !== undefined) this.layout.toolbar = payload.toolbar

            if (payload && payload.footer !== undefined) this.layout.footer = payload.footer

            if (payload && payload.boxed !== undefined) this.layout.boxed = payload.boxed

            if (payload && payload.roundedCorners !== undefined) this.layout.roundedCorners = payload.roundedCorners

            if (payload && payload.viewAnimation !== undefined) this.layout.viewAnimation = payload.viewAnimation
        },
        setLogin() {
            this.logged = true
        },
        setLogout() {
            this.layout.navPos = null
            this.layout.toolbar = null
            this.logged = false
        },
        setSplashScreen(payload: boolean) {
            this.splashScreen = payload
        }
    },
    getters: {
        navPos(state) {
            return state.layout?.navPos
        },
        toolbar(state) {
            return state.layout?.toolbar
        },
        footer(state) {
            return state.layout?.footer
        },
        boxed(state) {
            return state.layout?.boxed
        },
        roundedCorners(state) {
            return state.layout?.roundedCorners
        },
        viewAnimation(state) {
            return state.layout?.viewAnimation
        },
        isLogged(state) {
            return state.logged
        }
    },
    persist: {
        paths: ["layout"]
    }
})

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useMainStore, import.meta.hot))
}
