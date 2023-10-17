<template>
	<CardCodeExample title="Large Data">
		<n-data-table :columns="columns" :data="data" :max-height="250" :scroll-x="1800" virtual-scroll />
	</CardCodeExample>
</template>

<script lang="ts">
import { h, defineComponent } from "vue"
import { NDataTable, type DataTableColumns } from "naive-ui"

type RowData = {
	key: number
	name: string
	age: number
	address: string
}

const columns: DataTableColumns<RowData> = [
	{
		type: "selection",
		fixed: "left"
	},
	{
		title: "Name",
		key: "name"
	},
	{
		title: "Age",
		key: "age"
	},
	{
		title: "Row",
		key: "row",
		render(row, index) {
			return h("span", ["row ", index])
		}
	},
	{
		title: "Row1",
		key: "row1",
		render(row, index) {
			return h("span", ["row ", index])
		}
	},
	{
		title: "Row2",
		key: "row2",
		render(row, index) {
			return h("span", ["row ", index])
		}
	},
	{
		title: "Address",
		key: "address"
	}
]

export default defineComponent({
	setup() {
		const data: RowData[] = Array.from({ length: 5000 }).map((_, index) => ({
			key: index,
			name: `Edward King ${index}`,
			age: 32,
			address: `London, Park Lane no. ${index}`
		}))
		return {
			data,
			columns
		}
	},
	components: { NDataTable }
})
</script>
