import dayjs from "@/utils/dayjs"
import { faker } from "@faker-js/faker"

export const labels = [
	{
		id: "personal",
		title: "Personal"
	},
	{
		id: "office",
		title: "Office"
	},
	{
		id: "important",
		title: "Important"
	},
	{
		id: "shop",
		title: "Shop"
	}
]

export interface Note {
	id: string
	date: Date
	dateText: string
	title: string
	body: string
	image: string
	labels: {
		id: string
		title: string
	}[]
}

export const getNotes = (): Note[] => {
	const notes = []

	for (let i = 0; i < 30; i++) {
		const body = []
		const bodyParagraphs = faker.number.int({ min: 1, max: 3 })
		for (let i = 0; i < bodyParagraphs; i++) {
			body.push(faker.lorem.sentence(faker.number.int({ min: 8, max: 30 })))
		}
		const date = faker.date.between({ from: dayjs().subtract(2, "w").toDate(), to: dayjs().toDate() })

		notes.push({
			id: faker.string.nanoid(),
			date,
			dateText:
				dayjs(date).format("YYYY-MM-DD") === dayjs().format("YYYY-MM-DD")
					? dayjs(date).format("HH:mm")
					: dayjs(date).format("D MMM"),
			title: faker.lorem.sentence(faker.number.int({ min: 3, max: 7 })).slice(0, -1),
			body: body.join("<br/><br/>"),
			image: faker.datatype.boolean() ? faker.image.urlPicsumPhotos({ width: 640, height: 400 }) : "",
			labels: faker.helpers.arrayElements(labels, { min: 0, max: 2 })
		})
	}

	return notes.sort((a, b) => b.date.getTime() - a.date.getTime())
}
