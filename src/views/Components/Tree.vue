<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Tree</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/tree"
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
				<n-tree block-line :data="data" :default-expanded-keys="defaultExpandedKeys" selectable />
				<template #code="{ html, js }">
					{{ html(`
					<n-tree block-line :data="data" :default-expanded-keys="defaultExpandedKeys" selectable />
					`) }}

					{{
						js(`
						function createData(level = 4, baseKey = ""): TreeOption[] | undefined {
							if (!level) return undefined
							return new Array(6 - level, undefined).map((_, index) => {
								const key = "" + baseKey + level + index
								return {
									label: createLabel(level),
									key,
									children: createData(level - 1, key)
								}
							})
						}

						function createLabel(level: number): string {
							if (level === 4) return "Out of Tao, One is born"
							if (level === 3) return "Out of One, Two"
							if (level === 2) return "Out of Two, Three"
							if (level === 1) return "Out of Three, the created universe"
							return ""
						}

						const data = createData()
						const defaultExpandedKeys = ref(["40", "41"])
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Checking">
				<n-tree
					block-line
					cascade
					checkable
					:data="data"
					:default-expanded-keys="defaultExpandedKeys"
					:default-checked-keys="defaultCheckedKeys"
					@update:checked-keys="updateCheckedKeys"
				/>
				<template #code="{ html, js }">
					{{ html(`
					<n-tree
						block-line
						cascade
						checkable
						:data="data"
						:default-expanded-keys="defaultExpandedKeys"
						:default-checked-keys="defaultCheckedKeys"
						@update:checked-keys="updateCheckedKeys"
					/>
					`) }}

					{{
						js(`
						function createData(level = 4, baseKey = ""): TreeOption[] | undefined {
							if (!level) return undefined
							return new Array(6 - level, undefined).map((_, index) => {
								const key = "" + baseKey + level + index
								return {
									label: createLabel(level),
									key,
									children: createData(level - 1, key)
								}
							})
						}

						function createLabel(level: number): string {
							if (level === 4) return "Out of Tao, One is born"
							if (level === 3) return "Out of One, Two"
							if (level === 2) return "Out of Two, Three"
							if (level === 1) return "Out of Three, the created universe"
							return ""
						}

						const data = createData()

						const defaultExpandedKeys = ref(["40", "4030", "403020"])
						const defaultCheckedKeys = ref(["40302010"])
						const updateCheckedKeys = (
							keys: Array\<\string | number\>\,
							options: Array\<\TreeOption | null\>\,
							meta: {
								node: TreeOption | null
								action: "check" | "uncheck"
							}
						) => {
							console.log("updateCheckedKeys", keys, options, meta)
						}
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Search">
				<n-space vertical :size="12">
					<n-input v-model:value="pattern" placeholder="Search" clearable />
					<n-switch v-model:value="showIrrelevantNodes">
						<template #checked>Show irrelevant nodes</template>
						<template #unchecked>Hide irrelevant nodes</template>
					</n-switch>
					<n-tree :show-irrelevant-nodes="showIrrelevantNodes" :pattern="pattern" :data="data1" block-line />
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical :size="12">
						<n-input v-model:value="pattern" placeholder="Search" clearable />
						<n-switch v-model:value="showIrrelevantNodes">
							<template #checked>Show irrelevant nodes</template>
							<template #unchecked>Hide irrelevant nodes</template>
						</n-switch>
						<n-tree
							:show-irrelevant-nodes="showIrrelevantNodes"
							:pattern="pattern"
							:data="data1"
							block-line
						/>
					</n-space>
					`) }}

					{{
						js(`
						const data1: TreeOption[] = [
							{
								label: "0",
								key: "0",
								children: [
									{
										label: "0-0",
										key: "0-0",
										children: [
											{ label: "0-0-0", key: "0-0-0" },
											{ label: "0-0-1", key: "0-0-1" }
										]
									},
									{
										label: "0-1",
										key: "0-1",
										children: [
											{ label: "0-1-0", key: "0-1-0" },
											{ label: "0-1-1", key: "0-1-1" }
										]
									}
								]
							},
							{
								label: "1",
								key: "1",
								children: [
									{
										label: "1-0",
										key: "1-0",
										children: [
											{ label: "1-0-0", key: "1-0-0" },
											{ label: "1-0-1", key: "1-0-1" }
										]
									},
									{
										label: "1-1",
										key: "1-1",
										children: [
											{ label: "1-1-0", key: "1-1-0" },
											{ label: "1-1-1", key: "1-1-1" }
										]
									}
								]
							}
						]
						const pattern = ref("")
						const showIrrelevantNodes = ref(false)
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NTree, type TreeOption, NSpace, NInput, NSwitch } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

function createData(level = 4, baseKey = ""): TreeOption[] | undefined {
	if (!level) return undefined
	return new Array(6 - level, undefined).map((_, index) => {
		const key = "" + baseKey + level + index
		return {
			label: createLabel(level),
			key,
			children: createData(level - 1, key)
		}
	})
}

function createLabel(level: number): string {
	if (level === 4) return "Out of Tao, One is born"
	if (level === 3) return "Out of One, Two"
	if (level === 2) return "Out of Two, Three"
	if (level === 1) return "Out of Three, the created universe"
	return ""
}

const data = createData()

const defaultExpandedKeys = ref(["40", "4030", "403020"])
const defaultCheckedKeys = ref(["40302010"])
const updateCheckedKeys = (
	keys: Array<string | number>,
	options: Array<TreeOption | null>,
	meta: {
		node: TreeOption | null
		action: "check" | "uncheck"
	}
) => {
	console.log("updateCheckedKeys", keys, options, meta)
}

const data1: TreeOption[] = [
	{
		label: "0",
		key: "0",
		children: [
			{
				label: "0-0",
				key: "0-0",
				children: [
					{ label: "0-0-0", key: "0-0-0" },
					{ label: "0-0-1", key: "0-0-1" }
				]
			},
			{
				label: "0-1",
				key: "0-1",
				children: [
					{ label: "0-1-0", key: "0-1-0" },
					{ label: "0-1-1", key: "0-1-1" }
				]
			}
		]
	},
	{
		label: "1",
		key: "1",
		children: [
			{
				label: "1-0",
				key: "1-0",
				children: [
					{ label: "1-0-0", key: "1-0-0" },
					{ label: "1-0-1", key: "1-0-1" }
				]
			},
			{
				label: "1-1",
				key: "1-1",
				children: [
					{ label: "1-1-0", key: "1-1-0" },
					{ label: "1-1-1", key: "1-1-1" }
				]
			}
		]
	}
]
const pattern = ref("")
const showIrrelevantNodes = ref(false)
</script>
