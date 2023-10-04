<template>
	<CardCodeExample title="Selection">
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
			:max-height="200"
			:scroll-x="1800"
			@update:checked-row-keys="handleCheck"
		/>
		<template #code="{ html, js }">
			{{ html(`
			<n-p>
				You have selected \{\{ checkedRowKeys.length \}\} row\{\{ checkedRowKeys.length < 2 ? "" : "s" \}\}.
			</n-p>

			<n-data-table
				:columns="columns"
				:data="data"
				:pagination="pagination"
				:row-key="rowKey"
				:max-height="200"
				:scroll-x="1800"
				@update:checked-row-keys="handleCheck"
			/>
			`) }}

			{{
				js(`
				type RowData = {
					key: number
					name: string
					age: string
					address: string
				}

				const createColumns = (): DataTableColumns\<\RowData\>\ => [
					{
						type: "selection",
						fixed: "left",
						disabled(row: RowData) {
							return row.name === "Edward King 3"
						}
					},
					{
						title: "Name",
						key: "name",
						fixed: "left"
					},
					{
						title: "Age",
						key: "age"
					},
					{
						title: "Address",
						key: "address"
					}
				]

				const data = Array.from({ length: 46 }).map((_, index) => ({
					key: index,
					name: \`Edward King \$\{index\}\`,
					age: 32,
					address: \`London, Park Lane no. \$\{index\}\`
				}))

				export default defineComponent({
					setup() {
						const checkedRowKeysRef = ref\<\DataTableRowKey[]\>([])
						const paginationReactive = reactive({
							page: 2,
							pageSize: 5,
							showSizePicker: true,
							pageSizes: [3, 5, 7],
							onChange: (page: number) => {
								paginationReactive.page = page
							},
							onUpdatePageSize: (pageSize: number) => {
								paginationReactive.pageSize = pageSize
								paginationReactive.page = 1
							}
						})

						return {
							data,
							columns: createColumns(),
							checkedRowKeys: checkedRowKeysRef,
							pagination: paginationReactive,
							rowKey: (row: RowData) => row.address,
							handleCheck(rowKeys: DataTableRowKey[]) {
								checkedRowKeysRef.value = rowKeys
							}
						}
					},
					components: { NP, NDataTable }
				})
				`)
			}}
		</template>
	</CardCodeExample>
</template>

<script lang="ts">
import { defineComponent, reactive, ref } from "vue"
import type { DataTableColumns, DataTableRowKey } from "naive-ui"
import { NP, NDataTable, NText } from "naive-ui"

type RowData = {
	key: number
	name: string
	age: string
	address: string
}

const createColumns = (): DataTableColumns<RowData> => [
	{
		type: "selection",
		fixed: "left",
		disabled(row: RowData) {
			return row.name === "Edward King 3"
		}
	},
	{
		title: "Name",
		key: "name",
		fixed: "left"
	},
	{
		title: "Age",
		key: "age"
	},
	{
		title: "Address",
		key: "address"
	}
]

const data = Array.from({ length: 46 }).map((_, index) => ({
	key: index,
	name: `Edward King ${index}`,
	age: 32,
	address: `London, Park Lane no. ${index}`
}))

export default defineComponent({
	setup() {
		const checkedRowKeysRef = ref<DataTableRowKey[]>([])
		const paginationReactive = reactive({
			page: 2,
			pageSize: 5,
			showSizePicker: true,
			pageSizes: [3, 5, 7],
			onChange: (page: number) => {
				paginationReactive.page = page
			},
			onUpdatePageSize: (pageSize: number) => {
				paginationReactive.pageSize = pageSize
				paginationReactive.page = 1
			}
		})

		return {
			data,
			columns: createColumns(),
			checkedRowKeys: checkedRowKeysRef,
			pagination: paginationReactive,
			rowKey: (row: RowData) => row.address,
			handleCheck(rowKeys: DataTableRowKey[]) {
				checkedRowKeysRef.value = rowKeys
			}
		}
	},
	components: { NP, NDataTable, NText }
})
</script>
