<template>
	<CardCodeExample title="Column draggable" ref="card">
		<template #description>Only support leaf nodes.</template>
		<n-data-table :columns="columns" :data="data" :pagination="pagination" />
	</CardCodeExample>
</template>

<script lang="tsx" setup>
import { type VNodeChild, reactive, ref } from "vue"
import { NButton, useMessage, NDataTable } from "naive-ui"
import type { DataTableColumns } from "naive-ui"
import { faker } from "@faker-js/faker"
import { useResizeObserver } from "@vueuse/core"

type Song = {
	no: number
	title: string
	length: string
}

const createColumns = ({ play }: { play: (row: Song) => void }): DataTableColumns<Song> => {
	return [
		{
			title: "No",
			key: "no",
			width: 50
		},
		{
			title: "Title",
			key: "title",
			resizable: true,
			minWidth: 200
		},
		{
			title: "Length",
			key: "length",
			resizable: true,
			minWidth: 100
		},
		{
			title: "Action",
			key: "actions",
			minWidth: 100,
			render: row =>
				(
					// @ts-ignore
					<NButton onClick={() => play(row)} strong tertiary size="small">
						Play
					</NButton>
				) as VNodeChild
		}
	]
}

const data: Song[] = new Array(50).fill(undefined).map((_, i) => ({
	no: i + 1,
	title: faker.music.songName(),
	length: faker.number.int({ min: 1, max: 8 }) + ":" + faker.number.int({ min: 10, max: 59 })
}))

const message = useMessage()

const columns = ref(
	createColumns({
		play(row: Song) {
			message.info(`Play ${row.title}`)
		}
	})
)

const pagination = reactive({
	page: 1,
	pageSize: 5,
	showSizePicker: true,
	simple: false,
	pageSizes: [3, 5, 7],
	onChange: (page: number) => {
		pagination.page = page
	},
	onUpdatePageSize: (pageSize: number) => {
		pagination.pageSize = pageSize
		pagination.page = 1
	}
})

const card = ref(null)

useResizeObserver(card, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pagination.simple = width < 600
})
</script>
