<template>
	<CardCodeExample title="Selection" ref="card">
		<template #description>
			Rows can be selectable by making first column's type as
			<n-text code>selection</n-text>
			.
		</template>

		<n-p>You have selected {{ checkedRowKeys.length }} row{{ checkedRowKeys.length < 2 ? "" : "s" }}.</n-p>

		<n-data-table
			:columns="columns"
			:data="data"
			:pagination="pagination"
			:row-key="rowKey"
			:max-height="400"
			:scroll-x="3200"
			@update:checked-row-keys="handleCheck"
		/>
	</CardCodeExample>
</template>

<script lang="tsx" setup>
import { computed, reactive, ref } from "vue"
import { NP, NDataTable, NText, NButton, type DataTableColumns, type DataTableRowKey } from "naive-ui"
import { useResizeObserver } from "@vueuse/core"
import { faker } from "@faker-js/faker"

type RowData = {
	key: number
	name: string
	age: string
	address: string
	city: string
	country: string
	budget: string
	email: string
	jobTitle: string
	number: string
	vehicle: string
}

const data = ref(
	Array.from({ length: 60 }).map((_, index) => {
		const firstName = faker.person.firstName()
		const lastName = faker.person.lastName()
		return {
			key: index,
			name: firstName + " " + lastName,
			age: faker.number.int({ min: 18, max: 65 }),
			address: faker.location.streetAddress(),
			city: faker.location.city(),
			country: faker.location.country(),
			budget: faker.finance.amount(500, 10000, 2, "$"),
			email: faker.internet.exampleEmail({ firstName, lastName }),
			jobTitle: faker.person.jobTitle(),
			number: faker.phone.number(),
			vehicle: faker.vehicle.vehicle()
		}
	})
)

const checkedRowKeys = ref<DataTableRowKey[]>([])

const pagination = reactive({
	page: 1,
	pageSize: 15,
	showSizePicker: true,
	simple: false,
	pageSizes: [5, 10, 15],
	onChange: (page: number) => {
		pagination.page = page
	},
	onUpdatePageSize: (pageSize: number) => {
		pagination.pageSize = pageSize
		pagination.page = 1
	}
})

const card = ref(null)

const columnFixed = ref(true)

useResizeObserver(card, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pagination.simple = width < 600
	columnFixed.value = width > 600
})

const columns = computed<DataTableColumns<RowData>>(
	() =>
		[
			{
				type: "selection",
				fixed: "left",
				options: ["all", "none"],
				disabled(row: RowData) {
					return row.key === 2
				}
			},
			{
				title: "Name",
				key: "name",
				fixed: columnFixed.value ? "left" : undefined,
				width: 180
			},
			{
				title: "Age",
				key: "age",
				width: 100
			},
			{
				title: "Address",
				key: "address",
				minWidth: 300
			},
			{
				title: "City",
				key: "city",
				minWidth: 300
			},
			{
				title: "Country",
				key: "country",
				minWidth: 300
			},
			{
				title: "Budget",
				key: "budget",
				minWidth: 300
			},
			{
				title: "Email",
				key: "email",
				minWidth: 400
			},
			{
				title: "Job Title",
				key: "jobTitle",
				minWidth: 400
			},
			{
				title: "Phone number",
				key: "number",
				minWidth: 400
			},
			{
				title: "Vehicle",
				key: "vehicle",
				minWidth: 400
			},
			{
				title: "Actions",
				key: "actions",
				fixed: columnFixed.value ? "right" : undefined,
				width: 100,
				render: () => (
					// @ts-ignore
					<NButton strong tertiary size="small">
						Action
					</NButton>
				)
			}
		] as DataTableColumns<RowData>
)

const rowKey = (row: RowData) => row.key

function handleCheck(rowKeys: DataTableRowKey[]) {
	checkedRowKeys.value = rowKeys
}
</script>
