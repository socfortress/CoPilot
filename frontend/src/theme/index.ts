import tokens from "@/design-tokens.json"
import { Layout, RouterTransition, ThemeNameEnum } from "@/types/theme.d"
import { colorToArray, expandPattern, getThemeColors, getTypeValue } from "@/utils/theme"
import { type GlobalThemeOverrides, type ThemeCommonVars, useOsTheme } from "naive-ui"

type ThemeState = ReturnType<typeof getDefaultState>

interface ThemeGetters {
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
		fontWeight: tokens.fontWeight, // Font weight from the token
		fontFamily: tokens.fontFamily, // Font family from the token
		typography: tokens.typography // Typography configurations from the token
	}
}

export function getThemeOverrides(state: ThemeState): GlobalThemeOverrides {
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
		textTertiary,
		border,
		hover
	} = state.colors[state.themeName]

	const themeColors = getThemeColors({ primary, success, warning, error, info })

	const lineHeight = state.lineHeight.default
	const borderRadius = state.borderRadius.default
	const borderRadiusSmall = state.borderRadius.small
	const borderColor = border
	const hoverColor = hover

	return {
		common: {
			...themeColors,
			textColorBase: text,
			textColor1: text,
			textColor2: text,
			textColor3: textTertiary,
			bodyColor: bodyBackground,
			baseColor: background,
			popoverColor: background,
			cardColor: background,
			modalColor: background,
			lineHeight,
			borderRadius,
			borderRadiusSmall,
			fontSize: state.fontSize.default,
			fontWeight: state.fontWeight.default,
			fontWeightStrong: state.fontWeight.strong,
			fontFamily: state.fontFamily.default,
			fontFamilyMono: state.fontFamily.mono,
			borderColor,
			hoverColor,
			dividerColor: borderColor
		},
		Card: {
			color: background,
			colorEmbedded: backgroundSecondary,
			titleFontSizeSmall: state.fontSize.cardTitle,
			titleFontSizeMedium: state.fontSize.cardTitle,
			titleFontSizeLarge: state.fontSize.cardTitle,
			titleFontSizeHuge: state.fontSize.cardTitle,
			titleFontWeight: state.fontWeight.cardTitle
		},
		LoadingBar: {
			colorLoading: primary
		},
		Tag: {
			colorBordered: "rgba(0, 0, 0, 0.1)"
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
}

export function getCssVars(state: ThemeState, getters: ThemeGetters): { [key: string]: string } {
	const naive = getters.naiveCommon

	const bgColor = naive.baseColor
	const bgSecondaryColor = state.colors[state.themeName].backgroundSecondary
	const fgColor = state.colors[state.themeName].text
	const fgSecondaryColor = state.colors[state.themeName].textSecondary
	const fgTertiaryColor = state.colors[state.themeName].textTertiary

	const bgSidebar = state.colors[state.themeName].sidebarBackground
	const bgBody = state.colors[state.themeName].bodyBackground

	const boxedWidth = state.boxed.width
	const routerTransitionDuration = state.routerTransitionDuration
	const sidebarAnimEase = state.sidebar.animEase
	const sidebarAnimDuration = state.sidebar.animDuration
	const sidebarOpenWidth = state.sidebar.openWidth
	const sidebarCloseWidth = state.sidebar.closeWidth
	const toolbarHeight = state.toolbarHeight
	const viewPadding = state.viewPadding
	const headerBarHeight = state.headerBarHeight
	const fontFamily = state.fontFamily.default
	const fontFamilyDisplay = state.fontFamily.display
	const fontFamilyMono = state.fontFamily.mono
	const fontSize = state.fontSize.default

	const borderRadius = state.borderRadius.default
	const borderRadiusSmall = state.borderRadius.small

	const bezierEase = naive.cubicBezierEaseInOut

	// This style object, imported via the themeStore, will be available application-wide and is exposed in the HTML tag as a list of CSS variables, which you can use in your CSS/SCSS code like: var(--bg-default-color)
	const styleObject: Record<string, string> = {
		"bg-body-color": `${bgBody}`,
		"bg-sidebar-color": `${bgSidebar}`,

		"fg-default-color": `${fgColor}`,
		"fg-secondary-color": `${fgSecondaryColor}`,
		"fg-tertiary-color": `${fgTertiaryColor}`,
		"bg-default-color": `${bgColor}`,
		"bg-secondary-color": `${bgSecondaryColor}`,

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
		"font-size": `${fontSize}`
	}

	// import colors by patterns
	for (const pattern of ["extra(1|2|3|4)", "primary", "success", "warning", "error", "info", "border", "hover"]) {
		const keys = expandPattern(pattern)

		for (const key of keys) {
			styleObject[`${key}-color`] = (state.colors[state.themeName] as Record<string, string>)[key]
		}
	}

	// add RGB values variant
	for (const [key, value] of Object.entries(styleObject)) {
		if (key.endsWith("-color")) {
			styleObject[`${key}-rgb`] = colorToArray(value, "rgb").join(" ")
		}
	}

	return styleObject
}
