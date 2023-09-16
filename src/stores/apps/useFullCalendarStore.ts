import { type CalendarEvent, availableCalendars, getEvents } from "@/mock/fullcalendar"
import { faker } from "@faker-js/faker"
import { defineStore } from "pinia"

const events = getEvents()

export const useFullCalendarStore = defineStore("calendar", {
	state: () => ({
		events,
		availableCalendars: availableCalendars,
		selectedCalendars: ["Personal", "Business", "Family", "Holiday", "Other"]
	}),
	actions: {
		fetchEvents(): CalendarEvent[] {
			const calendars = this.selectedCalendars
			return this.events.filter(event => calendars.includes(event.extendedProps?.calendar || ""))
		},
		addEvent(event: CalendarEvent) {
			event.id = faker.string.nanoid()
			this.events.push(event)
		},
		updateEvent(event: CalendarEvent) {
			const eventBKP = this.events.find(e => e.id === event.id)
			if (eventBKP) {
				Object.assign(eventBKP, event)
			}
			return event
		},
		removeEvent(eventId: string) {
			const eventIndex = this.events.findIndex(e => e.id === eventId)
			this.events.splice(eventIndex, 1)
			return true
		}
	}
})
