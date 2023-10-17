<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Input</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/input"
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
				<template #description>
					Basic use of
					<n-text code>n-input</n-text>
					.
				</template>
				<n-space vertical>
					<n-input v-model:value="value" type="text" placeholder="Basic Input" />
					<n-input v-model:value="value" type="textarea" placeholder="Basic Textarea" />
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-input v-model:value="value" type="text" placeholder="Basic Input" />
						<n-input v-model:value="value" type="textarea" placeholder="Basic Textarea" />
					</n-space>
					`) }}

					{{
						js(`
						const value = ref(null)
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Size">
				<n-space vertical>
					<n-input type="text" size="tiny" placeholder="Tiny Input" />
					<n-input type="text" size="small" placeholder="Small Input" />
					<n-input type="text" placeholder="Medium Input" />
					<n-input type="text" size="large" placeholder="Large Input" />
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space vertical>
						<n-input type="text" size="tiny" placeholder="Tiny Input" />
						<n-input type="text" size="small" placeholder="Small Input" />
						<n-input type="text" placeholder="Medium Input" />
						<n-input type="text" size="large" placeholder="Large Input" />
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Prefix & suffix">
				<n-space vertical>
					<n-input placeholder="Flash">
						<template #prefix>
							<Icon :name="FlashOutline" />
						</template>
					</n-input>
					<n-input round placeholder="1,400,000">
						<template #suffix>$</template>
					</n-input>
					<n-input round placeholder="Flash">
						<template #suffix>
							<Icon :name="FlashOutline" />
						</template>
					</n-input>
					<n-input type="text" placeholder="Basic Input" loading />
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-input placeholder="Flash">
							<template #prefix>
								<n-icon :component="FlashOutline" />
							</template>
						</n-input>
						<n-input round placeholder="1,400,000">
							<template #suffix>$</template>
						</n-input>
						<n-input round placeholder="Flash">
							<template #suffix>
								<n-icon :component="FlashOutline" />
							</template>
						</n-input>
						<n-input type="text" placeholder="Basic Input" loading />
					</n-space>
					`) }}
					{{
						js(`
						import { FlashOutline } from '@vicons/ionicons5'
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Password & Clearable">
				<n-space vertical>
					<n-input type="password" show-password-on="mousedown" placeholder="Password" :maxlength="8" />
					<n-input
						type="password"
						show-password-on="click"
						placeholder="Custom Password Toggle Icon"
						:maxlength="8"
					>
						<template #password-visible-icon>
							<Icon :size="16" :name="GlassesOutline" />
						</template>
						<template #password-invisible-icon>
							<Icon :size="16" :name="Glasses" />
						</template>
					</n-input>
					<n-input type="text" placeholder="Content is clearable" clearable />
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-input type="password" show-password-on="mousedown" placeholder="Password" :maxlength="8" />
						<n-input
							type="password"
							show-password-on="click"
							placeholder="Custom Password Toggle Icon"
							:maxlength="8"
						>
							<template #password-visible-icon>
								<n-icon :size="16" :component="GlassesOutline" />
							</template>
							<template #password-invisible-icon>
								<n-icon :size="16" :component="Glasses" />
							</template>
						</n-input>
						<n-input type="text" placeholder="Content is clearable" clearable />
					</n-space>
					`) }}

					{{
						js(`
						import { GlassesOutline, Glasses } from '@vicons/ionicons5'
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Autosize">
				<n-space vertical>
					<n-input placeholder="Autosizable" autosize style="min-width: 50%" />
					<n-input
						placeholder="Autosizable"
						type="textarea"
						size="small"
						:autosize="{
							minRows: 3,
							maxRows: 5
						}"
					/>
					<n-input
						type="textarea"
						placeholder="Autosizable"
						:autosize="{
							minRows: 3
						}"
					/>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space vertical>
						<n-input placeholder="Autosizable" autosize style="min-width: 50%" />
						<n-input
							placeholder="Autosizable"
							type="textarea"
							size="small"
							:autosize="{
								minRows: 3,
								maxRows: 5
							}"
						/>
						<n-input
							type="textarea"
							placeholder="Autosizable"
							:autosize="{
								minRows: 3
							}"
						/>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Input group">
				<n-space vertical>
					<n-input-group>
						<n-input :style="{ width: '33%' }" />
						<n-input-number :style="{ width: '33%' }" />
						<n-input :style="{ width: '33%' }" />
					</n-input-group>
					<n-input-group>
						<n-input-group-label>https://www.</n-input-group-label>
						<n-input :style="{ width: '33%' }" />
						<n-input-group-label>.com</n-input-group-label>
					</n-input-group>
					<n-input-group>
						<n-select :style="{ width: '33%' }" :options="selectOptions" />
						<n-cascader :style="{ width: '33%' }" :options="cascaderOptions" />
						<n-select :style="{ width: '33%' }" multiple :options="selectOptions" />
					</n-input-group>
					<n-input-group>
						<n-button type="primary">Search</n-button>
						<n-input :style="{ width: '50%' }" />
						<n-button type="primary" ghost>Search</n-button>
					</n-input-group>
					<n-input-group>
						<n-date-picker />
						<n-time-picker />
					</n-input-group>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-input-group>
							<n-input :style="{ width: '33%' }" />
							<n-input-number :style="{ width: '33%' }" />
							<n-input :style="{ width: '33%' }" />
						</n-input-group>
						<n-input-group>
							<n-input-group-label>https://www.</n-input-group-label>
							<n-input :style="{ width: '33%' }" />
							<n-input-group-label>.com</n-input-group-label>
						</n-input-group>
						<n-input-group>
							<n-select :style="{ width: '33%' }" :options="selectOptions" />
							<n-cascader :style="{ width: '33%' }" :options="cascaderOptions" />
							<n-select :style="{ width: '33%' }" multiple :options="selectOptions" />
						</n-input-group>
						<n-input-group>
							<n-button type="primary">Search</n-button>
							<n-input :style="{ width: '50%' }" />
							<n-button type="primary" ghost>Search</n-button>
						</n-input-group>
						<n-input-group>
							<n-date-picker />
							<n-time-picker />
						</n-input-group>
					</n-space>
					`) }}

					{{
						js(`
						const selectOptions = ref([
							{
								label: "option",
								value: "option"
							}
						])
						const cascaderOptions = ref([
							{
								label: "option-1",
								value: "option-1",
								children: [
									{
										label: "option-1-1",
										value: "option-1-1"
									}
								]
							}
						])`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Pairwise value">
				<n-input pair separator="-" :placeholder="['From', 'To']" clearable />
				<template #code="{ html }">
					{{ html(`
					<n-input pair separator="-" :placeholder="['From', 'To']" clearable />
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Word limit">
				<n-space vertical>
					<n-input maxlength="30" show-count clearable />
					<n-input default-value="Yes" show-count clearable>
						<template #count="{ value }">
							{{ value.includes("Yes") ? "99+" : value.length }}
						</template>
					</n-input>
					<n-input type="textarea" maxlength="30" show-count />
					<n-input type="textarea" default-value="What?" show-count>
						<template #count="{ value }">
							{{ value.includes("What?") ? "99+" : value.length }}
						</template>
					</n-input>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space vertical>
						<n-input maxlength="30" show-count clearable />
						<n-input default-value="Yes" show-count clearable>
							<template #count="{ value }">
								\{\{ value.includes("Yes") ? "99+" : value.length \}\}
							</template>
						</n-input>
						<n-input type="textarea" maxlength="30" show-count />
						<n-input type="textarea" default-value="What?" show-count>
							<template #count="{ value }">
								\{\{ value.includes("What?") ? "99+" : value.length \}\}
							</template>
						</n-input>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import {
	NInput,
	NSpace,
	NText,
	NInputGroup,
	NInputGroupLabel,
	NInputNumber,
	NSelect,
	NCascader,
	NButton,
	NDatePicker,
	NTimePicker
} from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { ref } from "vue"

const ExternalIcon = "tabler:external-link"
const FlashOutline = "ion:flash-outline"
const GlassesOutline = "ion:glasses-outline"
const Glasses = "ion:glasses"

const value = ref(null)

const selectOptions = ref([
	{
		label: "option",
		value: "option"
	}
])
const cascaderOptions = ref([
	{
		label: "option-1",
		value: "option-1",
		children: [
			{
				label: "option-1-1",
				value: "option-1-1"
			}
		]
	}
])
</script>
