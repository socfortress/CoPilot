import tokens from "@/design-tokens.json"
import { Layout, RouterTransition, ThemeNameEnum } from "@/types/theme.d"
import { hex2rgb } from "@/utils/theme"
import { type ThemeCommonVars, useOsTheme } from "naive-ui"

type ThemeState = ReturnType<typeof getDefaultState>

interface ThemeGetters {
	dividerColors: { [key: string]: string }
	hoverColors: { [key: string]: string }
	primaryColors: { [key: string]: string }
	secondaryOpacityColors: { [key: string]: string }
	secondaryColors: { [key: string]: string }
	sidebarBackground: string
	bodyBackground: string
	backgroundSecondaryColor: string
	naiveCommon: ThemeCommonVars
}

const osTheme = useOsTheme()

export function getDefaultState() {
	return {
		layout: Layout.HorizontalNav, // Type of layout, with vertical or horizontal navigation
		themeName: osTheme.value === "dark" ? ThemeNameEnum.Dark : ThemeNameEnum.Light, // Theme name (Dark, Light), with fallback to the light theme
		routerTransition: RouterTransition.FadeUp, // Type of transition for the router
		routerTransitionDuration: 0.3, // Duration of the router transition in seconds
		rtl: false, // RTL (right to left) mode toggle
		boxed: {
			enabled: true, // Choose whether to apply a maximum width to the page
			toolbar: true, // Choose whether to apply the maximum width to the toolbar as well
			width: 1600 // Maximum width size in pixels
		},
		sidebar: {
			autoClose: true, // Choose whether to automatically close the sidebar when the view goes below the "autoCloseBreakpoint" value
			collapsed: false, // Indicates if the sidebar is collapsed
			autoCloseBreakpoint: 1000, // Breakpoint for the automatic closing of the sidebar (in pixels)
			animEase: "ease-in-out", // Type of easing for animations
			animDuration: 0.3, // Duration of sidebar animations (in seconds)
			openWidth: 300, // Width of the open sidebar (in pixels)
			closeWidth: 64 // Width of the closed sidebar (in pixels)
		},
		footer: {
			show: true // Show or hide the footer
		},
		responsive: {
			breakpoint: 700, // Breakpoint in pixels (Desk -> Mobile)
			// Parameters to be adjusted based on the breakpoint
			override: {
				viewPadding: {
					desk: 40, // View padding for desktop
					mobile: 20 // View padding for mobile devices
				},
				toolbarHeight: {
					desk: 80, // Height of the toolbar for desktop
					mobile: 70 // Height of the toolbar for mobile devices
				}
			}
		},
		toolbarHeight: 80, // Default toolbar height (in pixels)
		viewPadding: 40, // Default view padding (in pixels)
		headerBarHeight: 60, // Height of the header bar (in pixels)
		colors: tokens.colors, // Color definitions from the token
		borderRadius: tokens.borderRadius, // Border radius from the token
		lineHeight: tokens.lineHeight, // Line height from the token
		fontSize: tokens.fontSize, // Font size from the token
		fontFamily: tokens.fontFamily, // Font family from the token
		typography: tokens.typography // Typography configurations from the token
	}
}

export function getCssVars(state: ThemeState, getters: ThemeGetters): { [key: string]: string } {
	const naive = getters.naiveCommon

	const bgColor = naive.baseColor
	const bgColorRGB = hex2rgb(bgColor).join(", ")
	const bgSecondaryColor = getters.backgroundSecondaryColor
	const fgColor = naive.textColorBase
	const fgSecondaryColor = naive.textColor3

	const tabFgColorActive = naive.textColor2
	const borderColor = naive.dividerColor
	const primaryColor = naive.primaryColor

	const successColor = naive.successColor
	const errorColor = naive.errorColor
	const warningColor = naive.warningColor
	const infoColor = naive.infoColor
	const successColorRGB = hex2rgb(successColor).join(", ")
	const errorColorRGB = hex2rgb(errorColor).join(", ")
	const warningColorRGB = hex2rgb(warningColor).join(", ")
	const infoColorRGB = hex2rgb(infoColor).join(", ")

	const {
		success005,
		warning005,
		error005,
		info005,
		success010,
		warning010,
		error010,
		info010,
		success020,
		warning020,
		error020,
		info020,
		success030,
		warning030,
		error030,
		info030,
		success040,
		warning040,
		error040,
		info040,
		success050,
		warning050,
		error050,
		info050,
		success060,
		warning060,
		error060,
		info060,
		success070,
		warning070,
		error070,
		info070,
		success080,
		warning080,
		error080,
		info080,
		success090,
		warning090,
		error090,
		info090
	} = state.colors[state.themeName]

	const modalColor = naive.modalColor
	const modalColorRGB = hex2rgb(modalColor).join(", ")
	const codeColor = naive.codeColor
	const tabColor = naive.tabColor
	const tabColorActive = naive.inputColor
	const bezierEase = naive.cubicBezierEaseInOut

	const buttonColorSecondary = naive.buttonColor2
	const buttonColorSecondaryHover = naive.buttonColor2Hover
	const buttonColorSecondaryPressed = naive.buttonColor2Pressed

	const bgSidebar = getters.sidebarBackground
	const bgSidebarRGB = hex2rgb(bgSidebar).join(", ")
	const bgBody = getters.bodyBackground
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

	const { divider005, divider010, divider020, divider030 } = getters.dividerColors
	const { hover005, hover010, hover050 } = getters.hoverColors
	const { primary005, primary010, primary015, primary020, primary030, primary040, primary050, primary060 } =
		getters.primaryColors
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
	} = getters.secondaryOpacityColors

	const { secondary1, secondary2, secondary3, secondary4 } = getters.secondaryColors
	const secondary1RGB = hex2rgb(secondary1).join(", ")
	const secondary2RGB = hex2rgb(secondary2).join(", ")
	const secondary3RGB = hex2rgb(secondary3).join(", ")
	const secondary4RGB = hex2rgb(secondary4).join(", ")

	// This style object, imported via the themeStore, will be available application-wide and is exposed in the HTML tag as a list of CSS variables, which you can use in your CSS/SCSS code like: var(-–bg-color)
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

		"success-010-color": `${success010}`,
		"error-010-color": `${error010}`,
		"warning-010-color": `${warning010}`,
		"info-010-color": `${info010}`,

		"success-020-color": `${success020}`,
		"error-020-color": `${error020}`,
		"warning-020-color": `${warning020}`,
		"info-020-color": `${info020}`,

		"success-030-color": `${success030}`,
		"error-030-color": `${error030}`,
		"warning-030-color": `${warning030}`,
		"info-030-color": `${info030}`,

		"success-040-color": `${success040}`,
		"error-040-color": `${error040}`,
		"warning-040-color": `${warning040}`,
		"info-040-color": `${info040}`,

		"success-050-color": `${success050}`,
		"error-050-color": `${error050}`,
		"warning-050-color": `${warning050}`,
		"info-050-color": `${info050}`,

		"success-060-color": `${success060}`,
		"error-060-color": `${error060}`,
		"warning-060-color": `${warning060}`,
		"info-060-color": `${info060}`,

		"success-070-color": `${success070}`,
		"error-070-color": `${error070}`,
		"warning-070-color": `${warning070}`,
		"info-070-color": `${info070}`,

		"success-080-color": `${success080}`,
		"error-080-color": `${error080}`,
		"warning-080-color": `${warning080}`,
		"info-080-color": `${info080}`,

		"success-090-color": `${success090}`,
		"error-090-color": `${error090}`,
		"warning-090-color": `${warning090}`,
		"info-090-color": `${info090}`,

		"success-color-rgb": `${successColorRGB}`,
		"error-color-rgb": `${errorColorRGB}`,
		"warning-color-rgb": `${warningColorRGB}`,
		"info-color-rgb": `${infoColorRGB}`,

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
		"secondary4-opacity-030-color": `${secondary4Opacity030}`,

		"border-small-050": `1px solid ${borderColor}`,
		"border-small-100": `1px solid ${divider010}`
	}
}
