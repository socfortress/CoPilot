export enum Layout {
	VerticalNav = "VerticalNav",
	Blank = "Blank"
}

export enum RouterTransition {
	Fade = "fade",
	FadeUp = "fade-up",
	FadeBottom = "fade-bottom",
	FadeLeft = "fade-left",
	FadeRight = "fade-right"
}

export enum ThemeNameEnum {
	Dark = "dark",
	Light = "light"
}

export type ColorScene = "" | "Suppl" | "Hover" | "Pressed"
export type ColorType = "primary" | "success" | "warning" | "error" | "info"
export type ColorKey = `${ColorType}Color${ColorScene}`
export type ThemeColor = Partial<Record<ColorKey, string>>

export interface ColorAction {
	scene: ColorScene
	handler: (color: string) => string
}
