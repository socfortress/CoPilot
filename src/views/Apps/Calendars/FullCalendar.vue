<template>
	<div class="page page-wrapped flex flex-col page-without-footer">
		<div class="wrapper flex grow">
			<n-scrollbar class="sidebar-scroll">
				<div class="sidebar">
					<div class="section">
						<DatePicker
							expanded
							borderless
							transparent
							locale="en"
							:first-day-of-week="2"
							:is-dark="isThemeDark"
							v-model="selectedDate"
						></DatePicker>
					</div>
					<div class="fullcalendar-actions-box section p-4">
						<p class="mb-3 opacity-50">Calendars:</p>
						<div class="calendars-list">
							<n-checkbox v-model:checked="checkAll" label="View all" />
							<n-checkbox-group v-model:value="store.selectedCalendars" class="flex flex-col">
								<n-checkbox
									v-for="calendar in store.availableCalendars"
									:key="calendar.label"
									:value="calendar.label"
									class="styled"
									:class="calendar.label"
									:label="calendar.label"
								/>
							</n-checkbox-group>
						</div>
					</div>

					<div class="section p-4 mt-7">
						<div class="links flex flex-col gap-3">
							<a
								href="https://fullcalendar.io/docs/vue"
								target="_blank"
								alt="docs"
								class="flex items-center"
								rel="nofollow noopener noreferrer"
							>
								<Icon :name="ExternalIcon" :size="16" />
								<span class="ml-2">docs</span>
							</a>
							<a
								href="https://vcalendar.io/"
								target="_blank"
								alt="docs"
								class="flex items-center"
								rel="nofollow noopener noreferrer"
							>
								<Icon :name="ExternalIcon" :size="16" />
								<span class="ml-2">VCalendar</span>
							</a>
						</div>
					</div>
				</div>
			</n-scrollbar>
			<div class="main flex-grow scrollbar-styled">
				<FullCalendar ref="refCalendar" :options="calendarOptions" v-if="ready" />
				<n-spin v-else class="w-full h-full"></n-spin>
			</div>
		</div>

		<n-modal v-model:show="showLabelsModal" preset="card" style="max-width: 260px" class="fullcalendar-actions-box">
			<template #header>
				<span class="label">Actions</span>
			</template>
			<div class="mb-6 flex flex-col gap-3">
				<n-button secondary type="primary" @click="createNewEvent({})" class="grow">Add event</n-button>
				<n-button secondary @click="goToday()" class="grow">Today</n-button>
			</div>
			<div class="labels-sections">
				<div class="label">Filters</div>
				<n-checkbox v-model:checked="checkAll" label="View all" />
				<n-checkbox-group v-model:value="store.selectedCalendars" class="flex flex-col">
					<n-checkbox
						v-for="calendar in store.availableCalendars"
						:key="calendar.label"
						:value="calendar.label"
						class="styled"
						:class="calendar.label"
						:label="calendar.label"
					/>
				</n-checkbox-group>
			</div>
		</n-modal>

		<EventEditor
			v-model:show="modalShow"
			v-model:event="currentEvent"
			@submitEvent="submitEvent"
			@deleteEvent="deleteEvent"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, nextTick } from "vue"
import { NCheckbox, NCheckboxGroup, NScrollbar, NModal, NButton, NSpin } from "naive-ui"

import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

import FullCalendar from "@fullcalendar/vue3"
import type { CalendarApi, EventInput, CalendarOptions } from "@fullcalendar/core"
import type { DateMarker, EventImpl } from "@fullcalendar/core/internal"
import dayGridPlugin from "@fullcalendar/daygrid"
import interactionPlugin from "@fullcalendar/interaction"
import listPlugin from "@fullcalendar/list"
import timeGridPlugin from "@fullcalendar/timegrid"
import type { CalendarEvent, CalendarEditEvent } from "@/mock/fullcalendar"
import { useFullCalendarStore } from "@/stores/apps/useFullCalendarStore"
import { DatePicker } from "v-calendar"
import "v-calendar/style.css"
import "@/assets/scss/vcalendar-override.scss"
import { useThemeStore } from "@/stores/theme"
import EventEditor from "@/components/apps/FullCalendar/EventEditor.vue"
import { useHideLayoutFooter } from "@/composables/useHideLayoutFooter"

const store = useFullCalendarStore()
const themeStore = useThemeStore()

const ready = ref(false)
const refCalendar = ref()
const calendarApi = ref<null | CalendarApi>(null)

onMounted(() => {
	nextTick(() => {
		const duration = 1000 * themeStore.routerTransitionDuration
		const gap = 500

		// TIMEOUT REQUIRED BY PAGE ANIMATION
		setTimeout(() => {
			ready.value = true
			nextTick(() => {
				calendarApi.value = refCalendar.value?.getApi()
			})
		}, duration + gap)
	})
})

const newEvent: CalendarEditEvent = {
	title: "",
	start: new Date().getTime(),
	end: new Date().getTime(),
	allDay: false,
	extendedProps: {
		calendar: "Personal",
		location: "",
		description: ""
	}
}

const currentEvent = ref<CalendarEditEvent | null>(null)

const selectedDate = ref(new Date())
const showLabelsModal = ref(false)

function eventSanitizer(event: EventImpl): CalendarEvent {
	const {
		publicId,
		title,
		extendedProps: { calendar, location, description },
		allDay
	} = event._def

	const start = event._instance?.range.start || new Date()
	const end = event._instance?.range.end || new Date()

	return {
		id: publicId,
		title,
		start,
		end,
		extendedProps: {
			calendar,
			location,
			description
		},
		allDay
	}
}

function eventToEdit(event: EventImpl): CalendarEditEvent {
	const {
		publicId,
		title,
		extendedProps: { calendar, location, description },
		allDay
	} = event._def

	const start = event._instance?.range.start.getTime() || new Date().getTime()
	const end = event._instance?.range.end.getTime() || new Date().getTime()

	return {
		id: publicId,
		title,
		start,
		end,
		extendedProps: {
			calendar,
			location,
			description
		},
		allDay
	}
}

const checkAll = computed({
	get: () => store.selectedCalendars.length === store.availableCalendars.length,
	set: val => {
		if (val) store.selectedCalendars = store.availableCalendars.map((i: { label: string }) => i.label)
		else if (store.selectedCalendars.length === store.availableCalendars.length) store.selectedCalendars = []
	}
})

const isThemeDark = computed(() => useThemeStore().isThemeDark)

const modalShow = computed({
	get: () => currentEvent.value !== null,
	set: () => (currentEvent.value = null)
})

const submitEvent = () => {
	if (currentEvent.value) {
		if (currentEvent.value.id) {
			store.updateEvent(currentEvent.value)
		} else {
			store.addEvent(currentEvent.value)
		}
		currentEvent.value = null
		refetchEvents()
	}
}

const deleteEvent = () => {
	if (currentEvent.value) {
		if (currentEvent.value.id) {
			store.removeEvent(currentEvent.value.id)
		}
		currentEvent.value = null
		refetchEvents()
	}
}

const createNewEvent = ({ start, end }: { start?: number; end?: number }) => {
	showLabelsModal.value = false
	currentEvent.value = {
		...structuredClone(newEvent),
		start: start || new Date().getTime(),
		end: end || new Date().getTime(),
		allDay: true
	}
}

const refetchEvents = () => {
	calendarApi.value?.refetchEvents()
}

const goToday = () => {
	showLabelsModal.value = false
	goToDate(new Date(), false)
}

const goToDate = (date: Date, newEvent: boolean) => {
	calendarApi.value?.gotoDate(date)
	if (newEvent) {
		createNewEvent({ start: date.getTime(), end: date.getTime() })
	}
}

const calendarOptions: CalendarOptions = {
	plugins: [dayGridPlugin, interactionPlugin, timeGridPlugin, listPlugin],
	initialView: "dayGridMonth",
	headerToolbar: {
		start: "drawerToggler actionsToggler today",
		center: "prev,title,next",
		end: "dayGridMonth,timeGridWeek,timeGridDay,listMonth"
	},
	firstDay: 1,
	forceEventDuration: true,
	editable: true,
	eventResizableFromStart: true,
	dragScroll: true,
	dayMaxEvents: 2,
	navLinks: true,
	events: (info, successCallback) => {
		if (!info) return
		const events: EventInput[] = store.fetchEvents()
		successCallback(events)
	},
	eventClassNames({ event }) {
		return [`c-${event._def.extendedProps.calendar} styled`]
	},
	eventClick({ event }) {
		currentEvent.value = eventToEdit(event)
	},
	dateClick(info) {
		createNewEvent({ start: info.date.getTime(), end: info.date.getTime() })
	},
	eventDrop: ({ event }) => {
		if (event._instance) {
			event._instance.range.start = event.start as DateMarker
			event._instance.range.end = event.end as DateMarker
		}
		const updated = eventSanitizer(event)
		store.updateEvent(updated)
		refetchEvents()
	},
	customButtons: {
		drawerToggler: {
			text: "",
			click() {
				createNewEvent({})
			}
		},
		actionsToggler: {
			text: "Actions",
			click() {
				showLabelsModal.value = !showLabelsModal.value
			}
		}
	}
}

watch(() => store.selectedCalendars, refetchEvents)
watch(selectedDate, val => goToDate(val, true))

// :has() CSS relational pseudo-class not yet supported by Firefox
// (https://caniuse.com/css-has)
// at the moment this worker around permit to hide Layout Footer
useHideLayoutFooter()
</script>

<style lang="scss" scoped>
.page {
	min-height: 800px;
	.wrapper {
		overflow: hidden;
		background-color: var(--bg-color);
		border-radius: var(--border-radius);
		border: 1px solid var(--border-color);

		:deep() {
			.sidebar-scroll {
				width: 310px;
				min-width: 290px;
				background-color: var(--bg-secondary-color);

				@media (max-width: 1200px) {
					display: none;
				}
			}
		}
		.sidebar {
			padding: 36px 20px;
			min-width: 290px;
		}

		.main {
			overflow: hidden;
			padding: 20px;
			padding-top: 40px;

			.fc {
				height: 100%;

				:deep() {
					--fc-today-bg-color: var(--primary-005-color);
					--fc-border-color: var(--border-color);
					--fc-button-bg-color: var(--bg-secondary-color);

					--fc-button-border-color: var(--primary-005-color);
					--fc-button-text-color: var(--primary-color);
					--fc-button-active-bg-color: var(--primary-010-color);
					--fc-button-active-border-color: var(--primary-005-color);
					--fc-button-hover-bg-color: var(--primary-005-color);
					--fc-button-hover-border-color: var(--primary-005-color);
					.fc-header-toolbar {
						flex-wrap: wrap;
						gap: 10px;

						.fc-toolbar-title {
							text-align: center;
							line-height: 1.2;
							font-size: 18px;
						}
						.fc-toolbar-chunk {
							&:nth-child(2) {
								& > div {
									display: flex;
									align-items: center;
									gap: 20px;
								}
							}
						}
						.fc-button-group {
							border-radius: var(--border-radius);

							button {
								text-transform: capitalize;
								outline: none;
								border-radius: var(--border-radius);

								&.fc-prev-button,
								&.fc-next-button {
									line-height: 1;
								}

								&:focus {
									box-shadow: none;
								}
							}

							.fc-button:not(:last-child) {
								border-bottom-right-radius: 0px;
								border-top-right-radius: 0px;
							}
							.fc-button:not(:first-child) {
								border-bottom-left-radius: 0px;
								border-top-left-radius: 0px;
								margin-left: -1px;
							}
						}

						.fc-drawerToggler-button {
							background-color: var(--primary-010-color);
							border-radius: var(--border-radius);
							border: none;
							padding: 7px 18px;

							&::after {
								content: "Add event";
							}
						}

						.fc-today-button,
						.fc-actionsToggler-button {
							background-color: var(--button-color-secondary);
							padding: 7px 18px;
							border-radius: var(--border-radius);
							color: var(--fg-color);
							border: none;
							text-transform: capitalize;
						}

						.fc-actionsToggler-button {
							display: none;
						}

						.fc-next-button,
						.fc-prev-button {
							background-color: transparent;
							border: none;
							color: var(--fg-color);

							.fc-icon {
								font-size: 24px;
							}

							&:hover {
								color: var(--primary-color);
							}
						}

						button {
							font-weight: 500;
							outline: none;
							box-shadow: none !important;
						}
					}

					.fc-col-header-cell-cushion {
						text-decoration: none;
					}

					.fc-list-sticky {
						.fc-list-day > * {
							background-color: var(--bg-color);
						}
					}

					.fc-list-event:hover {
						td {
							background-color: var(--primary-005-color);
						}
					}
					.fc-timegrid-event-harness-inset .fc-timegrid-event,
					.fc-timegrid-event.fc-event-mirror,
					.fc-timegrid-more-link {
						box-shadow: none;
					}

					.fc-event {
						.fc-event-title {
							margin-left: 3px;
						}

						.fc-event-time {
							color: var(--fg-secondary-color);
							margin-left: 5px;
						}

						&.c-Personal {
							background-color: var(--secondary1-opacity-005-color);
							border-color: var(--secondary1-opacity-010-color);
							.fc-event-title {
								color: var(--secondary1-color);
							}
						}
						&.c-Business {
							background-color: var(--secondary2-opacity-005-color);
							border-color: var(--secondary2-opacity-010-color);
							.fc-event-title {
								color: var(--secondary2-color);
							}
						}
						&.c-Family {
							background-color: var(--secondary3-opacity-005-color);
							border-color: var(--secondary3-opacity-010-color);
							.fc-event-title {
								color: var(--secondary3-color);
							}
						}
						&.c-Holiday {
							background-color: var(--secondary4-opacity-005-color);
							border-color: var(--secondary4-opacity-010-color);
							.fc-event-title {
								color: var(--secondary4-color);
							}
						}
						&.c-Other {
							background-color: var(--primary-005-color);
							border-color: var(--primary-005-color);
							.fc-event-title {
								color: var(--primary-color);
							}
						}
					}

					.fc-popover {
						border-color: var(--primary-020-color);
						border: none;
						.fc-popover-header {
							color: var(--fg-color);
							background-color: var(--bg-secondary-color);
						}

						.fc-event-time {
							color: rgba(0, 0, 0, 0.5);
						}
					}
				}
			}
		}
	}
	@media (max-width: 1200px) {
		.wrapper {
			.main {
				padding-top: 20px;
				.fc {
					:deep() {
						.fc-header-toolbar {
							.fc-actionsToggler-button {
								display: initial;
							}

							.fc-today-button {
								display: none;
							}
						}
					}
				}
			}
		}
	}
	@media (max-width: 900px) {
		.wrapper {
			.main {
				.fc {
					:deep() {
						.fc-header-toolbar {
							.fc-drawerToggler-button {
								padding: 4px 18px;
								line-height: 1.19;
								&::after {
									content: "+";
									font-size: 24px;
								}
							}
						}
					}
				}
			}
		}
	}
	@media (max-width: 840px) {
		.wrapper {
			.main {
				.fc {
					:deep() {
						.fc-header-toolbar {
							.fc-toolbar-chunk {
								&:nth-child(2) {
									order: -1;
									width: 100%;
									display: flex;
									align-items: center;
									justify-content: center;

									& > div {
										width: 100%;
										justify-content: space-between;
									}
								}
							}
						}
					}
				}
			}
		}
	}
	@media (max-width: 700px) {
		min-height: initial;
		.wrapper {
			height: 100%;
			margin-left: calc(var(--view-padding) * -1);
			margin-right: calc(var(--view-padding) * -1);
			margin-bottom: calc(var(--view-padding) * -1);
			border-radius: 0;
			border: none;
			.main {
				padding: 10px;

				.fc {
					height: 100%;
				}
			}
		}
	}
	@media (max-width: 395px) {
		.wrapper {
			.main {
				.fc {
					:deep() {
						.fc-header-toolbar {
							.fc-actionsToggler-button {
								margin-left: 0;
							}
							.fc-drawerToggler-button {
								display: none;
							}
						}
					}
				}
			}
		}
	}
}
</style>

<style lang="scss">
.fullcalendar-actions-box {
	border-radius: var(--border-radius);
	overflow: hidden;

	.n-card-header,
	.n-card__content {
		background-color: var(--bg-color);
	}

	.labels-sections {
		border-top: var(--border-small-050);
		margin-left: -24px;
		margin-right: -24px;
		padding: 0 24px;
		padding-top: 16px;

		.label {
			margin-bottom: 16px;
		}
	}
	.label {
		font-family: var(--font-family);
		font-size: 12px;
		margin-bottom: 8px;
		font-weight: 600;
		color: var(--fg-secondary-color);
	}

	.n-checkbox {
		&.styled {
			margin-top: 8px;

			.n-checkbox__label {
				display: flex;
				align-items: center;
				gap: 8px;

				&::after {
					content: "";
					display: block;
					width: 8px;
					height: 8px;
					border-radius: 50%;
				}
			}
		}
		&.Personal {
			.n-checkbox__label::after {
				background-color: var(--secondary1-color);
			}
		}
		&.Business {
			.n-checkbox__label::after {
				background-color: var(--secondary2-color);
			}
		}
		&.Family {
			.n-checkbox__label::after {
				background-color: var(--secondary3-color);
			}
		}
		&.Holiday {
			.n-checkbox__label::after {
				background-color: var(--secondary4-color);
			}
		}
		&.Other {
			.n-checkbox__label::after {
				background-color: var(--primary-color);
			}
		}
	}
}
</style>
