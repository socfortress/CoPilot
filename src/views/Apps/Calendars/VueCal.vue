<template>
	<div class="page page-wrapped flex flex-col">
		<div class="flex justify-between flex-col lg:flex-row">
			<div class="page-header grow lg:mr-6">
				<div class="title">Vue Cal</div>
				<div class="links">
					<a
						href="https://antoniandre.github.io/vue-cal/"
						target="_blank"
						alt="docs"
						rel="nofollow noopener noreferrer"
					>
						<Icon :name="ExternalIcon" :size="20" />
						docs
					</a>
					<a
						href="https://codepen.io/collection/AMvOgd"
						target="_blank"
						alt="docs"
						rel="nofollow noopener noreferrer"
					>
						<Icon :name="ExternalIcon" :size="20" />
						examples
					</a>
				</div>
			</div>
			<div class="mb-4 flex gap-4">
				<div class="mini-card flex gap-4">
					<span>Options:</span>
					<n-checkbox v-model:checked="split" label="Split by users" />
					<n-checkbox v-model:checked="monthEvents" label="Events on month view" />
				</div>
			</div>
		</div>

		<vue-cal
			:selected-date="selectedDate"
			:time-from="8 * 60"
			:time-to="19 * 60"
			:split-days="split ? demoExample.splits : []"
			sticky-split-labels="sticky-split-labels"
			:editable-events="demoExample.editable"
			:events="demoExample.events"
			:events-on-month-view="monthEvents ? 'short' : null"
			active-view="month"
			@cell-focus="selectedDate = $event.date || $event"
			style="height: 100%"
		>
			<template #split-label="{ split }">
				<strong :style="`color: ${split.color}`">{{ split.label }}</strong>
			</template>
		</vue-cal>
	</div>
</template>

<script lang="ts">
import { defineComponent } from "vue"
import { NCheckbox } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
// @ts-ignore
import VueCal from "vue-cal"
import "vue-cal/dist/vuecal.css"
import dayjs from "@/utils/dayjs"

interface CalEvent {
	start: string
	end: string
	title: string
	class: string
	background: boolean
	deletable: boolean
	resizable: boolean
	split: number
	content: string
}

const demoExample = {
	splits: [
		{ label: "John", class: "john" },
		{ label: "Kate", class: "kate" }
	],
	editable: { title: true, drag: true, resize: true, create: true, delete: true },
	events: [] as Partial<CalEvent>[]
}

export default defineComponent({
	name: "Calendar",
	data: () => ({
		demoExample,
		split: false,
		monthEvents: false,
		ExternalIcon: "tabler:external-link",
		selectedDate: new Date(),
		previousFirstDayOfWeek: dayjs(new Date().setDate(new Date().getDate() - ((new Date().getDay() + 6) % 7)))
	}),
	methods: {
		addEvents() {
			// Place all the events in the real time current week.
			for (let i = 0; i < 5; i++) {
				const day = this.previousFirstDayOfWeek.add(i, "d").format("YYYY-MM-DD")
				this.demoExample.events.push(
					{
						start: `${day} 12:00`,
						end: `${day} 13:00`,
						title: "LUNCH",
						class: "lunch",
						background: true,
						deletable: false,
						resizable: false,
						split: 1
					},
					{
						start: `${day} 12:00`,
						end: `${day} 13:00`,
						title: "LUNCH",
						class: "lunch",
						background: true,
						deletable: false,
						resizable: false,
						split: 2
					}
				)
			}

			const monday = this.previousFirstDayOfWeek.format("YYYY-MM-DD")
			const tuesday = this.previousFirstDayOfWeek.add(1, "d").format("YYYY-MM-DD")
			const thursday = this.previousFirstDayOfWeek.add(3, "d").format("YYYY-MM-DD")
			const friday = this.previousFirstDayOfWeek.add(4, "d").format("YYYY-MM-DD")
			this.demoExample.events.push(
				{
					start: `${monday} 15:30`,
					end: `${monday} 17:30`,
					title: "Tennis",
					content: "The Championships",
					resizable: false,
					split: 1
				},
				{
					start: `${tuesday} 08:00`,
					end: `${tuesday} 10:00`,
					title: "Volleyball",
					content: "World Cup",
					resizable: false,
					split: 2
				},
				{
					start: `${thursday} 09:00`,
					end: `${thursday} 11:30`,
					title: "Golf",
					content: "Ryder Cup",
					resizable: false,
					split: 1
				},
				{
					start: `${friday} 16:45`,
					end: `${friday} 18:45`,
					title: "Movie",
					content: "The Whale",
					resizable: false,
					split: 2
				}
			)
		}
	},
	created() {
		if (!this.demoExample.events.length) {
			this.addEvents()
		}
	},
	components: { VueCal, NCheckbox, Icon }
})
</script>

<style lang="scss" scoped>
.mini-card {
	background: var(--bg-secondary-color);
	border-radius: var(--border-radius);
	padding: 10px 20px;

	a {
		text-decoration: underline;
		text-decoration-color: var(--primary-060-color);
	}
}
.vuecal {
	box-shadow: none;

	:deep() {
		.vuecal__header {
			.vuecal__menu {
				background-color: transparent;

				padding: 3px;
				border-radius: var(--border-radius-small);
				width: fit-content;
				background-color: var(--tab-color);
				transition: background-color 0.3s var(--bezier-ease);
				display: flex;
				align-items: center;
				margin: 0 auto;
				margin-bottom: 10px;

				.vuecal__view-btn {
					font-size: 14px;
					border-radius: var(--border-radius-small);
					transition: all 0.3s var(--bezier-ease);

					&.vuecal__view-btn--active {
						border-bottom-width: 0px;
						font-weight: 500;
						color: var(--tab-fg-color-active);
						background-color: var(--tab-color-active);
						box-shadow: 0 1px 3px 0 rgb(0 0 0 / 8%);
					}
				}
			}

			.vuecal__title-bar {
				min-height: 2.5em;
				border-top-right-radius: var(--border-radius);
				border-top-left-radius: var(--border-radius);
				background-color: var(--bg-color);
			}
			.vuecal__weekdays-headings {
				background-color: var(--bg-color);
				margin-bottom: 0;
				border-bottom: none;

				.vuecal__heading {
					height: 4.4em;
				}
			}

			& > .vuecal__split-days-headers {
				background-color: var(--bg-color);
				margin-left: 0;
				padding-left: 4em;
			}
		}

		.vuecal__body {
			.vuecal__cells {
				.vuecal__cell {
					&:before {
						border: 2px solid var(--bg-color);
					}

					&.vuecal__cell--today,
					&.vuecal__cell--current {
						background: var(--bg-secondary-color);
						background: repeating-linear-gradient(
							45deg,
							var(--bg-secondary-color),
							var(--bg-secondary-color) 10px,
							var(--primary-005-color) 10px,
							var(--primary-005-color) 20px
						);
					}

					&.vuecal__cell--selected {
						background: var(--primary-005-color);
					}
				}

				&.years-view {
					.vuecal__cell {
						.vuecal__cell-content {
							.vuecal__cell-date {
								font-size: 20px;
							}
						}
					}
				}
				&.year-view {
					.vuecal__cell {
						.vuecal__cell-content {
							.vuecal__cell-date {
								font-size: 16px;
							}
						}
					}
				}

				&.month-view {
					.vuecal__cell {
						.vuecal__cell-content {
							justify-content: start;
							padding-top: 30px;

							.vuecal__cell-date {
								color: var(--fg-color);
							}

							.vuecal__cell-events-count {
								font-size: 14px;
								position: relative;
								top: initial;
								left: initial;
								transform: none;
								width: 24px;
								height: 24px;
								line-height: 23px;
								border-radius: 24px;
								margin: 0 auto;
								margin-top: 20px;
								margin-bottom: -44px;

								color: var(--primary-color);
								border: 1px solid var(--primary-color);
								background: var(--primary-010-color);

								@media (max-height: 1000px) {
									margin-bottom: 10px;
								}
							}

							.vuecal__cell-events {
								padding: 0 5px;
								padding-top: 20px;
								margin-bottom: -64px;

								@media (max-height: 1200px) {
									margin-bottom: 0px;
								}

								.vuecal__event {
									margin-bottom: 5px;
									padding: 1px 3px;
									color: var(--bg-color);
									background-color: var(--primary-color);
								}
							}
						}

						&.vuecal__cell--out-of-scope {
							.vuecal__cell-content {
								.vuecal__cell-date {
									opacity: 0.4;
								}
							}
						}
					}
				}

				&.week-view,
				&.day-view {
					.vuecal__cell {
						&:before {
							border-top: 0px;
						}

						.vuecal__cell-content {
							.vuecal__no-event {
								line-height: 1.2;
							}
							.vuecal__cell-events {
								.vuecal__event {
									transform: translateY(1px) translateX(3px);
									width: calc(100% - 6px) !important;
									padding-top: 3px;
									line-height: 1.2;

									color: var(--bg-color);
									background-color: var(--primary-color);

									.vuecal__event-time {
										font-size: 12px;
										font-weight: bold;
									}
								}
							}
						}
					}
				}
			}

			.vuecal__time-column {
				width: 4em;
				border-left: 2px solid var(--bg-color);
				border-bottom: 2px solid var(--bg-color);

				.vuecal__time-cell {
					text-align: center;
					padding: 0;
				}
			}
		}
	}
}
</style>
