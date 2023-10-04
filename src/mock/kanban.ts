import dayjs from "@/utils/dayjs"
import { faker } from "@faker-js/faker"

export const labels: Label[] = [
	{
		id: "design",
		title: "Design"
	},
	{
		id: "feature-request",
		title: "Feature Request"
	},
	{
		id: "backend",
		title: "Backend"
	},
	{
		id: "qa",
		title: "QA"
	}
]

export interface Label {
	id: string
	title: string
}

export interface Task {
	id: string
	title: string
	date: Date
	dateText: string
	label?: Label
}
export interface Column {
	id: string
	title: string
	tasks: Task[]
}

export const getTask = (): Column[] => {
	const columns = ["Backlog", "In Progress", "Review", "Done"].map(o => ({
		id: faker.string.nanoid(),
		title: o,
		tasks: [] as Task[]
	}))

	for (const column of columns) {
		const nTask = faker.number.int({ min: 2, max: 8 })

		for (let i = 0; i < nTask; i++) {
			const date = faker.date.between({ from: dayjs().subtract(2, "w").toDate(), to: dayjs().toDate() })

			column.tasks.push({
				id: faker.string.nanoid(),
				title: faker.lorem.sentence(faker.number.int({ min: 3, max: 7 })).slice(0, -1),
				date,
				dateText:
					dayjs(date).format("YYYY-MM-DD") === dayjs().format("YYYY-MM-DD")
						? dayjs(date).format("HH:mm")
						: dayjs(date).format("D MMM"),
				label: faker.datatype.boolean() ? faker.helpers.arrayElement(labels) : undefined
			})
		}
	}
	return columns
}
