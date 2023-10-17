<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Calendar</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/calendar"
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
				<n-calendar #="{ year, month, date }" @update:value="handleUpdateValue">
					{{ year }}-{{ month }}-{{ date }}
				</n-calendar>
				<template #code="{ html, js }">
					{{ html(`
					<n-calendar
						v-model:value="value"
						#="{ year, month, date }"
						:is-date-disabled="isDateDisabled"
						@update:value="handleUpdateValue"
					>
						\{\{ year \}\}-\{\{ month \}\}-\{\{ date \}\}
					</n-calendar>
					`) }}

					{{
						js(`
						const message = useMessage()

						function handleUpdateValue(_: number, { year, month, date }: { year: number; month: number; date: number }) {
							message.success(\`\$\{year}-\$\{month}-\$\{date}\`)
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NCalendar, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const message = useMessage()

function handleUpdateValue(_: number, { year, month, date }: { year: number; month: number; date: number }) {
	message.success(`${year}-${month}-${date}`)
}
</script>
