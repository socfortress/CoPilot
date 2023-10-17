<template>
	<n-card hoverable content-style="padding: 15px;">
		<Calendar
			expanded
			borderless
			transparent
			color="custom-color"
			:is-dark="isThemeDark"
			:attributes="attributes"
		/>
	</n-card>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { NCard } from "naive-ui"
import { Calendar } from "v-calendar"
import "v-calendar/style.css"
import "@/assets/scss/vcalendar-override.scss"
import { useThemeStore } from "@/stores/theme"
import { type AttributeConfig } from "v-calendar/dist/types/src/utils/attribute.d"
import dayjs from "@/utils/dayjs"
import { faker } from "@faker-js/faker"

const isThemeDark = computed(() => useThemeStore().isThemeDark)

const attributes = [
	{
		dot: "blue",
		dates: [
			dayjs().subtract(1, "d").toDate(),
			dayjs().subtract(5, "d").toDate(),
			dayjs().add(5, "d").toDate(),
			dayjs().add(10, "d").toDate()
		],
		popover: {
			label: faker.lorem.sentence({ min: 1, max: 3 })
		}
	},
	{
		dot: "red",
		dates: [
			dayjs().subtract(3, "d").toDate(),
			dayjs().subtract(5, "d").toDate(),
			dayjs().add(2, "d").toDate(),
			dayjs().add(12, "d").toDate()
		],
		popover: {
			label: faker.lorem.sentence({ min: 1, max: 3 })
		}
	},
	{
		dot: "green",
		dates: [
			dayjs().subtract(1, "d").toDate(),
			dayjs().subtract(8, "d").toDate(),
			dayjs().add(2, "d").toDate(),
			dayjs().add(10, "d").toDate()
		],
		popover: {
			label: faker.lorem.sentence({ min: 1, max: 3 })
		}
	}
] as AttributeConfig[]
</script>
