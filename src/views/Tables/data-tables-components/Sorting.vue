<template>
	<CardCodeExample title="Multiple column sorting">
		<template #description>
			Set
			<n-text code>multiple</n-text>
			and
			<n-text code>compare</n-text>
			on
			<n-text code>sorter</n-text>
			to enable multiple column sorting.
			<n-text code>multiple</n-text>
			is the priority of sorting (larger value means higher priority).
		</template>

		<n-space vertical :size="12">
			<n-space>
				<n-button @click="filterAddress">Filter Address (London)</n-button>
				<n-button @click="clearFilters">Clear Filters</n-button>
				<n-button @click="clearSorter">Clear Sorter</n-button>
			</n-space>
			<n-data-table ref="dataTableInst" :columns="columns" :data="data" :pagination="pagination" />
		</n-space>
	</CardCodeExample>
</template>

<script>
import { defineComponent, ref } from "vue"
import { NSpace, NButton, NDataTable, NText } from "naive-ui"

const columns = [
	{
		title: "Name",
		key: "name",
		minWidth: 100
	},
	{
		title: "Age",
		key: "age",
		minWidth: 80,
		sorter: (row1, row2) => row1.age - row2.age
	},
	{
		title: "Chinese Score",
		key: "chinese",
		defaultSortOrder: false,
		minWidth: 150,
		sorter: {
			compare: (a, b) => a.chinese - b.chinese,
			multiple: 3
		}
	},
	{
		title: "Math Score",
		defaultSortOrder: false,
		key: "math",
		minWidth: 150,
		sorter: {
			compare: (a, b) => a.math - b.math,
			multiple: 2
		}
	},
	{
		title: "English Score",
		defaultSortOrder: false,
		key: "english",
		minWidth: 150,
		sorter: {
			compare: (a, b) => a.english - b.english,
			multiple: 1
		}
	},
	{
		title: "Address",
		key: "address",
		minWidth: 250,
		filterOptions: [
			{
				label: "London",
				value: "London"
			},
			{
				label: "New York",
				value: "New York"
			}
		],
		filter(value, row) {
			return ~row.address.indexOf(value)
		}
	}
]

const data = [
	{
		key: 0,
		name: "John Brown",
		age: 32,
		address: "New York No. 1 Lake Park",
		chinese: 98,
		math: 60,
		english: 70
	},
	{
		key: 1,
		name: "Jim Green",
		age: 42,
		address: "London No. 1 Lake Park",
		chinese: 98,
		math: 66,
		english: 89
	},
	{
		key: 2,
		name: "Joe Black",
		age: 32,
		address: "Sidney No. 1 Lake Park",
		chinese: 98,
		math: 66,
		english: 89
	},
	{
		key: 3,
		name: "Jim Red",
		age: 32,
		address: "London No. 2 Lake Park",
		chinese: 88,
		math: 99,
		english: 89
	}
]

export default defineComponent({
	setup() {
		const dataTableInstRef = ref(null)
		return {
			data,
			columns,
			dataTableInst: dataTableInstRef,
			pagination: ref({ pageSize: 5 }),
			filterAddress() {
				dataTableInstRef.value.filter({
					address: ["London"]
				})
			},
			clearFilters() {
				dataTableInstRef.value.filter(null)
			},
			clearSorter() {
				dataTableInstRef.value.sort(null)
			}
		}
	},
	components: { NSpace, NButton, NDataTable, NText }
})
</script>
