export enum Layout {
	VerticalNav = "VerticalNav",
	HorizontalNav = "HorizontalNav",
	Blank = "Blank"
}

export enum RouterTransition {
	Fade = "fade",
	FadeUp = "fade-up",
	FadeBottom = "fade-bottom",
	FadeLeft = "fade-left",
	FadeRight = "fade-right"
}

export enum ThemeEnum {
	Dark = "dark",
	Light = "light"
}

export type Theme = "light" | "dark"

export type ThemeName = ThemeEnum | Theme

export type ColorType = "primary" | "info" | "success" | "warning" | "error"
export type ColorScene = "" | "Suppl" | "Hover" | "Pressed"
export type ColorKey = `${ColorType}Color${ColorScene}`
export type ThemeColor = Partial<Record<ColorKey, string>>

export interface ColorAction {
	scene: ColorScene
	handler: (color: string) => string
}
