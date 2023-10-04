import { faker } from "@faker-js/faker"
import { colord } from "colord"

export interface ColorOption {
	palette: string[]
	alphaFG?: number
	alphaBG?: number
}

export function getRandomColor({ palette, alphaFG, alphaBG }: ColorOption): {
	color: string
	fgcolor: string
	bgcolor: string
} {
	const color = faker.helpers.arrayElement(palette)
	const fgcolor = colord(color)
		.alpha(alphaFG ?? 0.5)
		.toHex()
	const bgcolor = colord(color)
		.alpha(alphaBG ?? 0.1)
		.toHex()

	return {
		color,
		fgcolor,
		bgcolor
	}
}
