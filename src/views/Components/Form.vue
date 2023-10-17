<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Form</div>
			<div class="links">

				<a
				href="https://www.naiveui.com/en-US/light/components/form"
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
			<CardCodeExample title="Label placement">
				<n-space class="mb-4" align="center">
					<n-radio-group v-model:value="placement" name="placement">
						<n-radio-button value="left"> Left </n-radio-button>
						<n-radio-button value="top"> Top </n-radio-button>
					</n-radio-group>

					<n-radio-group v-model:value="size" name="size">
						<n-radio-button value="small"> Small </n-radio-button>
						<n-radio-button value="medium"> Medium </n-radio-button>
						<n-radio-button value="large"> Large </n-radio-button>
					</n-radio-group>

					<n-checkbox v-model:checked="inline">Inline</n-checkbox>
					<n-checkbox v-model:checked="showLabel">Show Label</n-checkbox>
				</n-space>

				<n-form
					:model="model"
					:label-placement="placement"
					require-mark-placement="right-hanging"
					:size="size"
					:inline="inline"
					:show-label="showLabel"
					label-width="auto"
					:style="{
						maxWidth: '640px'
					}"
				>
					<n-form-item label="Brand" path="brandValue">
						<n-input v-model:value="model.brandValue" placeholder="Brand" />
					</n-form-item>
					<n-form-item label="Model" path="modelValue">
						<n-input v-model:value="model.modelValue" placeholder="Model" />
					</n-form-item>
					<n-form-item>
						<n-button> Validate </n-button>
					</n-form-item>
				</n-form>

				<template #code="{ html, js }">
					{{ html(`
					<n-space class="mb-4" align="center">
						<n-radio-group v-model:value="placement" name="placement">
							<n-radio-button value="left"> Left </n-radio-button>
							<n-radio-button value="top"> Top </n-radio-button>
						</n-radio-group>

						<n-radio-group v-model:value="size" name="size">
							<n-radio-button value="small"> Small </n-radio-button>
							<n-radio-button value="medium"> Medium </n-radio-button>
							<n-radio-button value="large"> Large </n-radio-button>
						</n-radio-group>

						<n-checkbox v-model:checked="inline">Inline</n-checkbox>
						<n-checkbox v-model:checked="showLabel">Show Label</n-checkbox>
					</n-space>

					<n-form
						:model="model"
						:label-placement="placement"
						require-mark-placement="right-hanging"
						:size="size"
						:inline="inline"
						:show-label="showLabel"
						label-width="auto"
						:style="{
							maxWidth: '640px'
						}"
					>
						<n-form-item label="Brand" path="brandValue">
							<n-input v-model:value="model.brandValue" placeholder="Brand" />
						</n-form-item>
						<n-form-item label="Model" path="modelValue">
							<n-input v-model:value="model.modelValue" placeholder="Model" />
						</n-form-item>
						<n-form-item>
							<n-button> Validate </n-button>
						</n-form-item>
					</n-form>
					`) }}

					{{
						js(`
						const size = ref\<\Size | undefined\>\("medium")
						const inline = ref(false)
						const showLabel = ref(true)
						const placement = ref\<\Label\Placement | undefined\>\("left")
						const model = ref({
							brandValue: null,
							modelValue: null
						})
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Rules">
				<n-form ref="formRef" inline :label-width="80" :model="formValue" :rules="rules">
					<n-form-item label="Name" path="user.name">
						<n-input v-model:value="formValue.user.name" placeholder="Input Name" />
					</n-form-item>
					<n-form-item label="Age" path="user.age">
						<n-input v-model:value="formValue.user.age" placeholder="Input Age" />
					</n-form-item>
					<n-form-item label="Phone" path="phone">
						<n-input v-model:value="formValue.phone" placeholder="Phone Number" />
					</n-form-item>
					<n-form-item>
						<n-button @click="handleValidateClick"> Validate </n-button>
					</n-form-item>
				</n-form>
				<pre> {{ JSON.stringify(formValue, null, 2) }} </pre>

				<template #code="{ html, js }">
					{{ html(`
					<n-form ref="formRef" inline :label-width="80" :model="formValue" :rules="rules" :size="size">
						<n-form-item label="Name" path="user.name">
							<n-input v-model:value="formValue.user.name" placeholder="Input Name" />
						</n-form-item>
						<n-form-item label="Age" path="user.age">
							<n-input v-model:value="formValue.user.age" placeholder="Input Age" />
						</n-form-item>
						<n-form-item label="Phone" path="phone">
							<n-input v-model:value="formValue.phone" placeholder="Phone Number" />
						</n-form-item>
						<n-form-item>
							<n-button @click="handleValidateClick"> Validate </n-button>
						</n-form-item>
					</n-form>

					<pre> \{\{ JSON.stringify(formValue, null, 2) \}\} </pre>
					`) }}

					{{
						js(`
						const formRef = ref<FormInst | null>(null)
						const message = useMessage()
						
						const formValue = ref({
							user: {
								name: "",
								age: ""
							},
							phone: ""
						})
						const rules = {
							user: {
								name: {
									required: true,
									message: "Please input your name",
									trigger: "blur"
								},
								age: {
									required: true,
									message: "Please input your age",
									trigger: ["input", "blur"]
								}
							},
							phone: {
								required: true,
								message: "Please input your number",
								trigger: ["input"]
							}
						}
						function handleValidateClick(e: MouseEvent) {
							e.preventDefault()
							formRef.value?.validate(errors => {
								if (!errors) {
									message.success("Valid")
								} else {
									console.log(errors)
									message.error("Invalid")
								}
							})
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import {
	NRadioGroup,
	NRadioButton,
	NForm,
	NFormItem,
	NInput,
	NSpace,
	NButton,
	NCheckbox,
	type FormInst,
	useMessage
} from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"
import { type LabelPlacement, type Size } from "naive-ui/es/form/src/interface"

const size = ref<Size | undefined>("medium")
const inline = ref(false)
const showLabel = ref(true)
const placement = ref<LabelPlacement | undefined>("left")
const model = ref({
	brandValue: null,
	modelValue: null
})

const formRef = ref<FormInst | null>(null)
const message = useMessage()

const formValue = ref({
	user: {
		name: "",
		age: ""
	},
	phone: ""
})
const rules = {
	user: {
		name: {
			required: true,
			message: "Please input your name",
			trigger: "blur"
		},
		age: {
			required: true,
			message: "Please input your age",
			trigger: ["input", "blur"]
		}
	},
	phone: {
		required: true,
		message: "Please input your number",
		trigger: ["input"]
	}
}
function handleValidateClick(e: MouseEvent) {
	e.preventDefault()
	formRef.value?.validate(errors => {
		if (!errors) {
			message.success("Valid")
		} else {
			console.log(errors)
			message.error("Invalid")
		}
	})
}
</script>

 
