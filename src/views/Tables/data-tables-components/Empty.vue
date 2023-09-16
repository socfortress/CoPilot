<template>
	<CardCodeExample title="Empty">
		<n-data-table :columns="columns" :data="data" />
	</CardCodeExample>
</template>
<script lang="tsx" setup>
import { type DataTableColumns, NDataTable } from "naive-ui"
import { ref } from "vue"

type Song = {
	no: number
	title: string
	length: string
}

const createColumns = (): DataTableColumns<Song> => {
	return [
		{
			title: "No",
			key: "no"
		},
		{
			title: "Title",
			key: "title"
		},
		{
			title: "Length",
			key: "length"
		},
		{
			title: "Action",
			key: "actions"
		}
	]
}

const data: Song[] = []

const columns = ref(createColumns())
</script>
