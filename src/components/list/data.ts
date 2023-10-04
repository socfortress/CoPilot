import { faker } from "@faker-js/faker"
import { type ColorOption, getRandomColor } from "./utils"

type PercentageDirection = "up" | "down"

interface Item {
	id: string
	code: string
	fgcolor: string
	bgcolor: string
	image?: string
	name: string
	adjective?: string
	amount: string
	percentage: number
	direction: PercentageDirection
}

export function getCompany(count: number, colorOption: ColorOption): Item[] {
	return new Array(count || 8).fill(undefined).map(() => {
		const { fgcolor, bgcolor } = getRandomColor(colorOption)

		return {
			id: faker.string.nanoid(),
			code: faker.string.alpha(3).toUpperCase(),
			fgcolor,
			bgcolor,
			image: faker.image.urlPicsumPhotos({ width: 80, height: 80 }),
			name: faker.company.name(),
			adjective: faker.company.catchPhraseAdjective(),
			amount: faker.finance.amount({ min: 200, max: 3000, dec: 2, symbol: "$", autoFormat: true }),
			percentage: faker.number.int({ min: 5, max: 100 }),
			direction: faker.datatype.boolean() ? "up" : "down"
		}
	})
}

export function getAirline(count: number, colorOption: ColorOption): Item[] {
	return new Array(count || 8).fill(undefined).map(() => {
		const { fgcolor, bgcolor } = getRandomColor(colorOption)

		const { name, iataCode } = faker.airline.airline()
		const airplane = faker.airline.airplane().name

		return {
			id: faker.string.nanoid(),
			code: iataCode,
			fgcolor,
			bgcolor,
			image: faker.image.urlLoremFlickr({ width: 80, height: 80, category: "airplane" }),
			name,
			adjective: airplane,
			amount: faker.finance.amount({ min: 200, max: 3000, dec: 0, symbol: "", autoFormat: true }),
			percentage: faker.number.int({ min: 5, max: 100 }),
			direction: faker.datatype.boolean() ? "up" : "down"
		}
	})
}

export function getColors(count: number): Item[] {
	const colors = [
		{
			name: "Pink",
			value: "#FF61C9"
		},
		{
			name: "Blue",
			value: "#6267FF"
		},
		{
			name: "Yellow",
			value: "#FFB600"
		},
		{
			name: "Red",
			value: "#FF0156"
		},
		{
			name: "Black",
			value: "#000"
		},
		{
			name: "Latte",
			value: "#f5f5f5"
		}
	]
	return new Array(count || 6).fill(undefined).map((_: any, i: number) => {
		const color = colors[i % colors.length]

		return {
			id: faker.string.nanoid(),
			code: "",
			fgcolor: color.value,
			bgcolor: color.value,
			name: color.name,
			amount:
				i === 0 ? "4.303" : faker.finance.amount({ min: 200, max: 3000, dec: 0, symbol: "", autoFormat: true }),
			percentage: faker.number.int({ min: 5, max: 100 }),
			direction: faker.datatype.boolean() ? "up" : "down"
		}
	})
}
