import { defineStore, acceptHMRUpdate } from "pinia"
import {
	type ColorAction,
	type ColorKey,
	type ColorType,
	Layout,
	RouterTransition,
	type ThemeColor,
	ThemeEnum,
	type ThemeName
} from "@/types/theme.d"
import { type GlobalThemeOverrides, type ThemeCommonVars, darkTheme, lightTheme, useOsTheme } from "naive-ui"
import { exposure, hex2hsl, hex2rgb } from "@/utils"
import _get from "lodash/get"
import _set from "lodash/set"
import { type BuiltInGlobalTheme } from "naive-ui/es/themes/interface"
import tokens from "@/design-tokens.json"
const osTheme = useOsTheme()

export const useThemeStore = defineStore("theme", {
	state: () => ({
		layout: Layout.VerticalNav,
		themeName: osTheme.value || ThemeEnum.Light,
		routerTransition: RouterTransition.FadeUp,
		boxed: {
			enabled: true,
			toolbar: true,
			width: 1600
		},
		sidebar: {
			autoClose: true,
			collapsed: false,
			autoCloseBreakpoint: 1000,
			animEase: "ease-in-out",
			animDuration: 0.3,
			openWidth: 300,
			closeWidth: 64
		},
		footer: {
			show: true
		},
		responsive: {
			breakpoint: 700,
			override: {
				viewPadding: {
					desk: 40,
					mobile: 20
				},
				toolbarHeight: {
					desk: 80,
					mobile: 70
				}
			}
		} as { [key: string]: any },
		toolbarHeight: 80,
		viewPadding: 40,
		headerBarHeight: 60,
		colors: tokens["colors"],
		borderRadius: tokens["borderRadius"],
		lineHeight: tokens["lineHeight"],
		fontSize: tokens["fontSize"],
		fontFamily: tokens["fontFamily"]
	}),
	actions: {
		setLayout(layout: Layout): void {
			this.layout = layout
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
		setTheme(themeName: ThemeName): void {
			this.themeName = themeName
		},
		setThemeLight(): void {
			this.themeName = ThemeEnum.Light
		},
		setThemeDark(): void {
			this.themeName = ThemeEnum.Dark
		},
		setColor(theme: ThemeName, colorType: ColorType, color: string): void {
			this.colors[theme][colorType] = color
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
		updateVars() {
			for (const key in this.responsive.override) {
				if (_get(this, key) && this.responsive.override[key]) {
					_set(
						this,
						key,
						window.innerWidth <= this.responsive.breakpoint
							? this.responsive.override[key].mobile
							: this.responsive.override[key].desk
					)
				}
			}

			// auto close sidebar on resize
			if (this.sidebar.autoClose) {
				if (!this.sidebar.collapsed && window.innerWidth <= this.sidebar.autoCloseBreakpoint) {
					this.sidebar.collapsed = true
				}
			}
		}
	},
	getters: {
		naiveTheme(state): BuiltInGlobalTheme {
			return state.themeName === ThemeEnum.Dark ? darkTheme : lightTheme
		},
		themeOverrides(state): GlobalThemeOverrides {
			const { primary, success, warning, error, info, background, bodyBackground, text, textSecondary } =
				state.colors[state.themeName]

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
					fontFamilyMono: state.fontFamily.mono
				},
				Card: {
					color: background,
					titleFontSizeSmall: state.fontSize.cardTitle,
					titleFontSizeMedium: state.fontSize.cardTitle,
					titleFontSizeLarge: state.fontSize.cardTitle,
					titleFontSizeHuge: state.fontSize.cardTitle
				},
				LoadingBar: {
					colorLoading: primary
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
		secondaryColors(state): { [key: string]: string } {
			const { secondary1, secondary2, secondary3, secondary4 } = state.colors[state.themeName]
			return {
				secondary1,
				secondary2,
				secondary3,
				secondary4
			}
		},
		shadeColors(state): { [key: string]: string } {
			const { shade1 } = state.colors[state.themeName]
			return {
				shade1
			}
		},
		naiveCommon(): ThemeCommonVars {
			return { ...this.naiveTheme.common, ...this.themeOverrides.common }
		},
		style(state): CSSStyleDeclaration {
			const naive = this.naiveCommon

			const bgColor = naive.baseColor
			const bgColorRGB = hex2rgb(bgColor).join(", ")
			const fgColor = naive.textColorBase
			const fgColorRGB = hex2rgb(fgColor).join(", ")
			const fgSecondaryColor = naive.textColor3
			const fgSecondaryColorRGB = hex2rgb(fgSecondaryColor).join(", ")
			const tabFgColorActive = naive.textColor2
			const borderColor = naive.dividerColor
			const primaryColor = naive.primaryColor
			const primaryColorRGB = hex2rgb(primaryColor).join(", ")
			const primaryColorHS = [hex2hsl(primaryColor)[0], hex2hsl(primaryColor)[1] + "%"].join(" ")

			const successColor = naive.successColor
			const errorColor = naive.errorColor
			const warningColor = naive.warningColor
			const infoColor = naive.infoColor

			const modalColor = naive.modalColor
			const modalColorRGB = hex2rgb(modalColor).join(", ")
			const codeColor = naive.codeColor
			const tabColor = naive.tabColor
			const tabColorActive = naive.inputColor
			const bezierEase = naive.cubicBezierEaseInOut

			const buttonColorSecondary = naive.buttonColor2
			const buttonColorSecondaryHover = naive.buttonColor2Hover
			const buttonColorSecondaryPressed = naive.buttonColor2Pressed

			const bgSidebar = this.sidebarBackground
			const bgBody = this.bodyBackground
			const bgBodyRGB = hex2rgb(bgBody).join(", ")
			const boxedWidth = state.boxed.width
			const sidebarAnimEase = state.sidebar.animEase
			const sidebarAnimDuration = state.sidebar.animDuration
			const sidebarOpenWidth = state.sidebar.openWidth
			const sidebarCloseWidth = state.sidebar.closeWidth
			const toolbarHeight = state.toolbarHeight
			const viewPadding = state.viewPadding
			const headerBarHeight = state.headerBarHeight
			const fontFamily = state.fontFamily.base
			const fontFamilyDisplay = state.fontFamily.display
			const fontFamilyMono = state.fontFamily.mono

			const borderRadius = state.borderRadius.base
			const borderRadiusSmall = state.borderRadius.small

			const { secondary1, secondary2, secondary3, secondary4 } = this.secondaryColors
			const secondary1RGB = hex2rgb(secondary1).join(", ")
			const secondary2RGB = hex2rgb(secondary2).join(", ")
			const secondary3RGB = hex2rgb(secondary3).join(", ")
			const secondary4RGB = hex2rgb(secondary4).join(", ")

			const { shade1 } = this.shadeColors
			const shade1RGB = hex2rgb(shade1).join(", ")

			return {
				"--fg-color": `${fgColor}`,
				"--fg-color-rgb": `${fgColorRGB}`,
				"--fg-secondary-color": `${fgSecondaryColor}`,
				"--fg-secondary-color-rgb": `${fgSecondaryColorRGB}`,
				"--bg-color": `${bgColor}`,
				"--bg-color-rgb": `${bgColorRGB}`,
				"--bg-sidebar": `${bgSidebar}`,
				"--bg-body": `${bgBody}`,
				"--bg-body-rgb": `${bgBodyRGB}`,
				"--border-color": `${borderColor}`,
				"--bezier-ease": `${bezierEase}`,
				"--sidebar-anim-ease": `${sidebarAnimEase}`,
				"--sidebar-anim-duration": `${sidebarAnimDuration}s`,
				"--sidebar-open-width": `${sidebarOpenWidth}px`,
				"--sidebar-close-width": `${sidebarCloseWidth}px`,
				"--boxed-width": `${boxedWidth}px`,
				"--toolbar-height": `${toolbarHeight}px`,
				"--header-bar-height": `${headerBarHeight}px`,
				"--view-padding": `${viewPadding}px`,
				"--border-radius": `${borderRadius}`,
				"--border-radius-small": `${borderRadiusSmall}`,
				"--font-family": `${fontFamily}`,
				"--font-family-display": `${fontFamilyDisplay}`,
				"--font-family-mono": `${fontFamilyMono}`,
				"--code-color": `${codeColor}`,
				"--primary-color": `${primaryColor}`,
				"--primary-color-rgb": `${primaryColorRGB}`,
				"--primary-color-hs": `${primaryColorHS}`,
				"--tab-color": `${tabColor}`,
				"--tab-color-active": `${tabColorActive}`,
				"--tab-fg-color-active": `${tabFgColorActive}`,
				"--modal-color": `${modalColor}`,
				"--modal-color-rgb": `${modalColorRGB}`,

				"--button-color-secondary": `${buttonColorSecondary}`,
				"--button-color-secondary-hover": `${buttonColorSecondaryHover}`,
				"--button-color-secondary-pressed": `${buttonColorSecondaryPressed}`,

				"--success-color": `${successColor}`,
				"--error-color": `${errorColor}`,
				"--warning-color": `${warningColor}`,
				"--info-color": `${infoColor}`,
				"--secondary1-color": `${secondary1}`,
				"--secondary1-color-rgb": `${secondary1RGB}`,
				"--secondary2-color": `${secondary2}`,
				"--secondary2-color-rgb": `${secondary2RGB}`,
				"--secondary3-color": `${secondary3}`,
				"--secondary3-color-rgb": `${secondary3RGB}`,
				"--secondary4-color": `${secondary4}`,
				"--secondary4-color-rgb": `${secondary4RGB}`,
				"--shade1-color": `${shade1}`,
				"--shade1-color-rgb": `${shade1RGB}`
			} as unknown as CSSStyleDeclaration
		},
		isThemeDark(state): boolean {
			return state.themeName === ThemeEnum.Dark
		},
		isThemeLight(state): boolean {
			return state.themeName === ThemeEnum.Light
		},
		isBoxed(state): boolean {
			return state.boxed.enabled
		},
		isFooterShown(state): boolean {
			return state.footer.show
		},
		isToolbarBoxed(state): boolean {
			return state.boxed.toolbar && state.boxed.enabled
		}
	},
	persist: {
		paths: ["layout", "themeName", "routerTransition", "boxed", "sidebar", "colors"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useThemeStore, import.meta.hot))
}

function getThemeColors(colors: Record<ColorType, string>) {
	const colorActions: ColorAction[] = [
		{ scene: "", handler: color => color },
		{ scene: "Suppl", handler: color => exposure(color, 0.1) },
		{ scene: "Hover", handler: color => exposure(color, 0.05) },
		{ scene: "Pressed", handler: color => exposure(color, -0.2) }
	]

	const themeColor: ThemeColor = {}

	for (const colorType in colors) {
		const colorValue = colors[colorType as ColorType]

		colorActions.forEach(action => {
			const colorKey: ColorKey = `${colorType as ColorType}Color${action.scene}`
			themeColor[colorKey] = action.handler(colorValue)
		})
	}

	return themeColor
}
