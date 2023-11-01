import dayjs from "@/utils/dayjs"
import { faker } from "@faker-js/faker"

export interface CalendarEvent {
	id?: string
	title: string
	start: Date | number
	end: Date | number
	allDay: boolean
	extendedProps: {
		calendar: string
		location?: string
		description?: string
	}
}

export interface CalendarEditEvent extends Omit<CalendarEvent, "start" | "end"> {
	start: number
	end: number
}

export const availableCalendars = [
	{
		label: "Personal"
	},
	{
		label: "Business"
	},
	{
		label: "Family"
	},
	{
		label: "Holiday"
	},
	{
		label: "Other"
	}
]

export const getEvents = (): CalendarEvent[] => {
	const events = []

	for (let i = 0; i < 30; i++) {
		const allDay = faker.datatype.boolean()
		const start = faker.date.between({
			from: dayjs().subtract(1, "month").toDate(),
			to: dayjs().add(1, "month").toDate()
		})
		const end = faker.date.between({ from: start, to: dayjs(start).add(2, "d").toDate() })

		events.push({
			id: faker.string.nanoid(),
			title: faker.lorem.sentence(faker.number.int({ min: 1, max: 3 })).slice(0, -1),
			start,
			end,
			allDay,
			extendedProps: {
				calendar: faker.helpers.arrayElements(availableCalendars, 1)[0].label,
				location: faker.datatype.boolean() ? faker.location.streetAddress(true) : "",
				description: faker.datatype.boolean() ? faker.lorem.sentence(faker.number.int({ min: 7, max: 20 })) : ""
			}
		})
	}
	return events
}
