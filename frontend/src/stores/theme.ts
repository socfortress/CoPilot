import type { ColorType, Layout, RouterTransition } from "@/types/theme.d"
import type { BuiltInGlobalTheme } from "naive-ui/es/themes/interface"
import { getCssVars, getDefaultState } from "@/theme"
import { ThemeNameEnum } from "@/types/theme.d"
import { exportPrimaryShades, getThemeColors, getTypeValue, type PrimaryShade } from "@/utils/theme"
import { useWindowSize } from "@vueuse/core"
import _get from "lodash/get"
import _pick from "lodash/pick"
import _set from "lodash/set"
import { darkTheme, type GlobalThemeOverrides, lightTheme, type ThemeCommonVars } from "naive-ui"
import { acceptHMRUpdate, defineStore } from "pinia"
import { watch } from "vue"

export const useThemeStore = defineStore("theme", {
	state: () => getDefaultState(),
	actions: {
		setLayout(layout: Layout): void {
			this.layout = layout
		},
		setRTL(rtl: boolean): void {
			this.rtl = rtl
		},
		setBoxed(boxed: boolean): void {
			this.boxed.enabled = boxed
		},
		setFooterShow(show: boolean): void {
			this.footer.show = show
		},
		setToolbarBoxed(boxed: boolean): void {
			this.boxed.toolbar = boxed
		},
		setRouterTransition(routerTransition: RouterTransition): void {
			this.routerTransition = routerTransition
		},
		setTheme(themeName: ThemeNameEnum): void {
			this.themeName = themeName
		},
		setThemeLight(): void {
			this.themeName = ThemeNameEnum.Light
		},
		setThemeDark(): void {
			this.themeName = ThemeNameEnum.Dark
		},
		setColor(theme: ThemeNameEnum, colorType: ColorType, color: string): void {
			this.colors[theme][colorType] = color

			if (colorType === "primary") {
				const primaryShades = exportPrimaryShades(color)

				for (const k in primaryShades) {
					const name = k as PrimaryShade
					const shade = primaryShades[name]

					const colorKey = `${colorType}${name}` as keyof (typeof this.colors)[typeof theme]
					this.colors[theme][colorKey] = shade
				}
			}
		},
		toggleTheme(): void {
			if (this.isThemeDark) {
				this.setThemeLight()
			} else {
				this.setThemeDark()
			}
		},
		toggleSidebar(): void {
			this.sidebar.collapsed = !this.sidebar.collapsed
		},
		refreshSidebar(): void {
			// this is useful in context like NUXT
			this.sidebar.collapsed = !this.sidebar.collapsed
			setTimeout(() => {
				this.sidebar.collapsed = !this.sidebar.collapsed
			}, 10)
		},
		openSidebar(): void {
			this.sidebar.collapsed = false
		},
		closeSidebar(): void {
			this.sidebar.collapsed = true
		},
		updateResponsiveVars() {
			for (const key in this.responsive.override) {
				if (_get(this, key) && key in this.responsive.override) {
					_set(
						this,
						key,
						window.innerWidth <= this.responsive.breakpoint
							? this.responsive.override[key as keyof typeof this.responsive.override].mobile
							: this.responsive.override[key as keyof typeof this.responsive.override].desk
					)
				}
			}
		},
		ensureSidebarState() {
			// auto close sidebar on resize
			if (this.sidebar.autoClose) {
				if (!this.sidebar.collapsed && window.innerWidth <= this.sidebar.autoCloseBreakpoint) {
					this.sidebar.collapsed = true
				}
			}
		},
		setDocumentThemeName(val: ThemeNameEnum, old?: ThemeNameEnum) {
			if (document) {
				const html = document.children[0] as HTMLElement
				if (old) {
					html.classList.remove(`theme-${old}`)
				}
				html.classList.add(`theme-${val}`)
			}
		},
		// This function allows you to utilize the values in the style object as variables within your CSS/SCSS code like: var(-–bg-color)
		setCssGlobalVars() {
			if (document) {
				const html = document.children[0] as HTMLElement
				const body = document.getElementsByTagName("body")?.[0]
				if (this.isRTL && body) {
					body.classList.add("direction-rtl")
					body.classList.remove("direction-ltr")
				} else {
					body.classList.remove("direction-rtl")
					body.classList.add("direction-ltr")
				}
				// html.dir = this.isRTL ? "rtl" : "ltr"
				const { style: htmlStyle } = html
				for (const key in this.style) {
					htmlStyle.setProperty(`--${key}`, this.style[key])
				}
			}
		},
		startWatchers() {
			const { width } = useWindowSize()

			watch([() => this.isRTL, () => this.style], () => {
				this.setCssGlobalVars()
			})

			watch(
				() => this.themeName,
				(val, old) => {
					this.setDocumentThemeName(val, old)
				}
			)

			watch(width, () => {
				this.updateResponsiveVars()
				this.ensureSidebarState()
			})
		},
		initTheme() {
			this.updateResponsiveVars()
			this.ensureSidebarState()
			this.setCssGlobalVars()
			this.setDocumentThemeName(this.themeName)
			this.startWatchers()
		}
	},
	getters: {
		naiveTheme(state): BuiltInGlobalTheme {
			return state.themeName === ThemeNameEnum.Dark ? darkTheme : lightTheme
		},
		themeOverrides(state): GlobalThemeOverrides {
			const {
				primary,
				success,
				warning,
				error,
				info,
				background,
				backgroundSecondary,
				bodyBackground,
				text,
				textSecondary,
				divider005,
				hover010
			} = state.colors[state.themeName]

			const themeColors = getThemeColors({ primary, success, warning, error, info })

			const lineHeight = state.lineHeight.base
			const borderRadius = state.borderRadius.base
			const borderRadiusSmall = state.borderRadius.small

			return {
				common: {
					...themeColors,
					textColorBase: text,
					textColor1: text,
					textColor2: text,
					textColor3: textSecondary,
					bodyColor: bodyBackground,
					baseColor: background,
					popoverColor: background,
					cardColor: background,
					modalColor: background,
					lineHeight,
					borderRadius,
					borderRadiusSmall,
					fontSize: state.fontSize.base,
					fontFamily: state.fontFamily.base,
					fontFamilyMono: state.fontFamily.mono,
					dividerColor: divider005,
					hoverColor: hover010
				},
				Card: {
					color: background,
					colorEmbedded: backgroundSecondary,
					titleFontSizeSmall: state.fontSize.cardTitle,
					titleFontSizeMedium: state.fontSize.cardTitle,
					titleFontSizeLarge: state.fontSize.cardTitle,
					titleFontSizeHuge: state.fontSize.cardTitle
				},
				LoadingBar: {
					colorLoading: primary
				},
				Typography: {
					headerFontSize1: getTypeValue(state, state.typography.h1.fontSize),
					headerFontSize2: getTypeValue(state, state.typography.h2.fontSize),
					headerFontSize3: getTypeValue(state, state.typography.h3.fontSize),
					headerFontSize4: getTypeValue(state, state.typography.h4.fontSize),
					headerFontSize5: getTypeValue(state, state.typography.h5.fontSize),
					headerFontSize6: getTypeValue(state, state.typography.h6.fontSize)
				}
			}
		},
		darkPrimaryColor(state): string {
			return state.colors.dark.primary
		},
		lightPrimaryColor(state): string {
			return state.colors.light.primary
		},
		primaryColor(state): string {
			return state.colors[state.themeName].primary
		},
		sidebarBackground(state): string {
			return state.colors[state.themeName].sidebarBackground
		},
		bodyBackground(state): string {
			return state.colors[state.themeName].bodyBackground
		},
		backgroundSecondaryColor(state): string {
			return state.colors[state.themeName].backgroundSecondary
		},
		secondaryColors(state): { [key: string]: string } {
			const pick = ["secondary1", "secondary2", "secondary3", "secondary4"]
			return _pick(state.colors[state.themeName], pick)
		},
		secondaryOpacityColors(state): { [key: string]: string } {
			const pick = [
				"secondary1Opacity005",
				"secondary1Opacity010",
				"secondary1Opacity020",
				"secondary1Opacity030",
				"secondary2Opacity005",
				"secondary2Opacity010",
				"secondary2Opacity020",
				"secondary2Opacity030",
				"secondary3Opacity005",
				"secondary3Opacity010",
				"secondary3Opacity020",
				"secondary3Opacity030",
				"secondary4Opacity005",
				"secondary4Opacity010",
				"secondary4Opacity020",
				"secondary4Opacity030"
			]
			return _pick(state.colors[state.themeName], pick)
		},
		dividerColors(state): { [key: string]: string } {
			const pick = ["divider005", "divider010", "divider020", "divider030"]
			return _pick(state.colors[state.themeName], pick)
		},
		hoverColors(state): { [key: string]: string } {
			const pick = ["hover005", "hover010", "hover050"]
			return _pick(state.colors[state.themeName], pick)
		},
		primaryColors(state): { [key: string]: string } {
			const pick = [
				"primary005",
				"primary010",
				"primary015",
				"primary020",
				"primary030",
				"primary040",
				"primary050",
				"primary060"
			]
			return _pick(state.colors[state.themeName], pick)
		},
		naiveCommon(): ThemeCommonVars {
			return { ...this.naiveTheme.common, ...this.themeOverrides.common }
		},
		style(state): { [key: string]: string } {
			return getCssVars(state, this)
		},
		isThemeDark(state): boolean {
			return state.themeName === ThemeNameEnum.Dark
		},
		isThemeLight(state): boolean {
			return state.themeName === ThemeNameEnum.Light
		},
		isBoxed(state): boolean {
			return state.boxed.enabled
		},
		isRTL(state): boolean {
			return state.rtl
		},
		isFooterShown(state): boolean {
			return state.footer.show
		},
		isToolbarBoxed(state): boolean {
			return state.boxed.toolbar && state.boxed.enabled
		}
	},
	persist: {
		// use this param to save specific state chunk on localStorage
		pick: ["layout", "themeName", "routerTransition", "boxed", "sidebar.collapsed"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useThemeStore, import.meta.hot))
}
