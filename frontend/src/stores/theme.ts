import { defineStore, acceptHMRUpdate } from "pinia"
import {
	type ColorAction,
	type ColorKey,
	type ColorType,
	type ThemeColor,
	type ThemeName,
	Layout,
	RouterTransition,
	ThemeEnum
} from "@/types/theme.d"
import { type GlobalThemeOverrides, type ThemeCommonVars, darkTheme, lightTheme, useOsTheme } from "naive-ui"
import { exportPrimaryShades, exposure, getTypeValue, hex2rgb, type PrimaryShade } from "@/utils/theme"
import _get from "lodash/get"
import _set from "lodash/set"
import _pick from "lodash/pick"
import { type BuiltInGlobalTheme } from "naive-ui/es/themes/interface"
import tokens from "@/design-tokens.json"
const osTheme = useOsTheme()

export const useThemeStore = defineStore("theme", {
	state: () => ({
		layout: Layout.HorizontalNav,
		themeName: osTheme.value || ThemeEnum.Dark,
		routerTransition: RouterTransition.FadeUp,
		routerTransitionDuration: 0.3,
		rtl: false,
		boxed: {
			enabled: false,
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
		},
		toolbarHeight: 80,
		viewPadding: 40,
		headerBarHeight: 60,
		colors: tokens["colors"],
		borderRadius: tokens["borderRadius"],
		lineHeight: tokens["lineHeight"],
		fontSize: tokens["fontSize"],
		fontFamily: tokens["fontFamily"],
		typography: tokens["typography"]
	}),
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

			if (colorType === "primary") {
				const primaryShades = exportPrimaryShades(color)

				for (const k in primaryShades) {
					const name = k as PrimaryShade
					const shade = primaryShades[name]
					const colorsTheme = this.colors[theme]
					const colorKey = (colorType + name) as keyof typeof colorsTheme
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
		updateVars() {
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
			const {
				primary,
				success,
				warning,
				error,
				info,
				background,
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
			const naive = this.naiveCommon

			const bgColor = naive.baseColor
			const bgColorRGB = hex2rgb(bgColor).join(", ")
			const bgSecondaryColor = this.backgroundSecondaryColor
			const fgColor = naive.textColorBase
			const fgSecondaryColor = naive.textColor3

			const tabFgColorActive = naive.textColor2
			const borderColor = naive.dividerColor
			const primaryColor = naive.primaryColor

			const successColor = naive.successColor
			const errorColor = naive.errorColor
			const warningColor = naive.warningColor
			const infoColor = naive.infoColor

			const { success005, warning005, error005, info005 } = state.colors[state.themeName]

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
			const bgSidebarRGB = hex2rgb(bgSidebar).join(", ")
			const bgBody = this.bodyBackground
			const bgBodyRGB = hex2rgb(bgBody).join(", ")

			const boxedWidth = state.boxed.width
			const routerTransitionDuration = state.routerTransitionDuration
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

			const { divider005, divider010, divider020, divider030 } = this.dividerColors
			const { hover005, hover010, hover050 } = this.hoverColors
			const { primary005, primary010, primary015, primary020, primary030, primary040, primary050, primary060 } =
				this.primaryColors
			const {
				secondary1Opacity005,
				secondary1Opacity010,
				secondary1Opacity020,
				secondary1Opacity030,
				secondary2Opacity005,
				secondary2Opacity010,
				secondary2Opacity020,
				secondary2Opacity030,
				secondary3Opacity005,
				secondary3Opacity010,
				secondary3Opacity020,
				secondary3Opacity030,
				secondary4Opacity005,
				secondary4Opacity010,
				secondary4Opacity020,
				secondary4Opacity030
			} = this.secondaryOpacityColors

			const { secondary1, secondary2, secondary3, secondary4 } = this.secondaryColors
			const secondary1RGB = hex2rgb(secondary1).join(", ")
			const secondary2RGB = hex2rgb(secondary2).join(", ")
			const secondary3RGB = hex2rgb(secondary3).join(", ")
			const secondary4RGB = hex2rgb(secondary4).join(", ")

			return {
				"bg-body": `${bgBody}`,
				"bg-body-rgb": `${bgBodyRGB}`,
				"bg-sidebar": `${bgSidebar}`,
				"bg-sidebar-rgb": `${bgSidebarRGB}`,

				"fg-color": `${fgColor}`,
				"fg-secondary-color": `${fgSecondaryColor}`,
				"bg-color": `${bgColor}`,
				"bg-color-rgb": `${bgColorRGB}`,
				"bg-secondary-color": `${bgSecondaryColor}`,

				"border-color": `${borderColor}`,
				"bezier-ease": `${bezierEase}`,
				"router-transition-duration": `${routerTransitionDuration}s`,
				"sidebar-anim-ease": `${sidebarAnimEase}`,
				"sidebar-anim-duration": `${sidebarAnimDuration}s`,
				"sidebar-open-width": `${sidebarOpenWidth}px`,
				"sidebar-close-width": `${sidebarCloseWidth}px`,
				"boxed-width": `${boxedWidth}px`,
				"toolbar-height": `${toolbarHeight}px`,
				"header-bar-height": `${headerBarHeight}px`,
				"view-padding": `${viewPadding}px`,
				"border-radius": `${borderRadius}`,
				"border-radius-small": `${borderRadiusSmall}`,
				"font-family": `${fontFamily}`,
				"font-family-display": `${fontFamilyDisplay}`,
				"font-family-mono": `${fontFamilyMono}`,
				"code-color": `${codeColor}`,
				"primary-color": `${primaryColor}`,
				"tab-color": `${tabColor}`,
				"tab-color-active": `${tabColorActive}`,
				"tab-fg-color-active": `${tabFgColorActive}`,
				"modal-color": `${modalColor}`,
				"modal-color-rgb": `${modalColorRGB}`,

				"button-color-secondary": `${buttonColorSecondary}`,
				"button-color-secondary-hover": `${buttonColorSecondaryHover}`,
				"button-color-secondary-pressed": `${buttonColorSecondaryPressed}`,

				"primary-005-color": `${primary005}`,
				"primary-010-color": `${primary010}`,
				"primary-015-color": `${primary015}`,
				"primary-020-color": `${primary020}`,
				"primary-030-color": `${primary030}`,
				"primary-040-color": `${primary040}`,
				"primary-050-color": `${primary050}`,
				"primary-060-color": `${primary060}`,

				"hover-005-color": `${hover005}`,
				"hover-010-color": `${hover010}`,
				"hover-050-color": `${hover050}`,

				"divider-005-color": `${divider005}`,
				"divider-010-color": `${divider010}`,
				"divider-020-color": `${divider020}`,
				"divider-030-color": `${divider030}`,

				"success-color": `${successColor}`,
				"error-color": `${errorColor}`,
				"warning-color": `${warningColor}`,
				"info-color": `${infoColor}`,
				"success-005-color": `${success005}`,
				"error-005-color": `${error005}`,
				"warning-005-color": `${warning005}`,
				"info-005-color": `${info005}`,

				"secondary1-color": `${secondary1}`,
				"secondary1-color-rgb": `${secondary1RGB}`,
				"secondary2-color": `${secondary2}`,
				"secondary2-color-rgb": `${secondary2RGB}`,
				"secondary3-color": `${secondary3}`,
				"secondary3-color-rgb": `${secondary3RGB}`,
				"secondary4-color": `${secondary4}`,
				"secondary4-color-rgb": `${secondary4RGB}`,

				"secondary1-opacity-005-color": `${secondary1Opacity005}`,
				"secondary1-opacity-010-color": `${secondary1Opacity010}`,
				"secondary1-opacity-020-color": `${secondary1Opacity020}`,
				"secondary1-opacity-030-color": `${secondary1Opacity030}`,
				"secondary2-opacity-005-color": `${secondary2Opacity005}`,
				"secondary2-opacity-010-color": `${secondary2Opacity010}`,
				"secondary2-opacity-020-color": `${secondary2Opacity020}`,
				"secondary2-opacity-030-color": `${secondary2Opacity030}`,
				"secondary3-opacity-005-color": `${secondary3Opacity005}`,
				"secondary3-opacity-010-color": `${secondary3Opacity010}`,
				"secondary3-opacity-020-color": `${secondary3Opacity020}`,
				"secondary3-opacity-030-color": `${secondary3Opacity030}`,
				"secondary4-opacity-005-color": `${secondary4Opacity005}`,
				"secondary4-opacity-010-color": `${secondary4Opacity010}`,
				"secondary4-opacity-020-color": `${secondary4Opacity020}`,
				"secondary4-opacity-030-color": `${secondary4Opacity030}`
			}
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
		paths: ["layout", "themeName", "routerTransition", "boxed", "sidebar.collapsed"]
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
