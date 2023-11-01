<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Time Picker</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/time-picker"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic">
				<n-space>
					<n-time-picker default-formatted-value="00:12:13" />
					<n-time-picker use-12-hours :default-value="1183135260000" />
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space>
						<n-time-picker default-formatted-value="00:12:13" />
						<n-time-picker use-12-hours :default-value="1183135260000" />
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
			<CardCodeExample title="Disable time">
				<n-time-picker
					v-model:value="time0"
					:is-hour-disabled="isHourDisabled"
					:is-minute-disabled="isMinuteDisabled"
					:is-second-disabled="isSecondDisabled"
				/>
				<template #code="{ html, js }">
					{{ html(`
					<n-time-picker
						v-model:value="time0"
						:is-hour-disabled="isHourDisabled"
						:is-minute-disabled="isMinuteDisabled"
						:is-second-disabled="isSecondDisabled"
					/>
					`) }}

					{{
						js(`
						const time0 = ref(null)
						function isHourDisabled(hour: number) {
							return hour % 2 === 0
						}
						function isMinuteDisabled(minute: number, selectedHour: number | null) {
							if (selectedHour === null) return false
							if (Number(selectedHour) < 12) {
								return minute < 30
							} else {
								return false
							}
						}
						function isSecondDisabled(second: number, selectedMinute: number | null, selectedHour: number | null) {
							if (selectedHour === null || selectedMinute === null) return false
							if (Number(selectedHour) > 20 && Number(selectedMinute) < 30) {
								return second < 40
							} else {
								return false
							}
						}
`)
					}}
				</template>
			</CardCodeExample>
			<CardCodeExample title="Step time">
				<n-time-picker :hours="[8, 18]" :minutes="8" :seconds="[0]" />
				<template #code="{ html }">
					{{ html(`
					<n-time-picker :hours="[8, 18]" :minutes="8" :seconds="[0]" />
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NTimePicker, NSpace } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const time0 = ref(null)
function isHourDisabled(hour: number) {
	return hour % 2 === 0
}
function isMinuteDisabled(minute: number, selectedHour: number | null) {
	if (selectedHour === null) return false
	if (Number(selectedHour) < 12) {
		return minute < 30
	} else {
		return false
	}
}
function isSecondDisabled(second: number, selectedMinute: number | null, selectedHour: number | null) {
	if (selectedHour === null || selectedMinute === null) return false
	if (Number(selectedHour) > 20 && Number(selectedMinute) < 30) {
		return second < 40
	} else {
		return false
	}
}
</script>
