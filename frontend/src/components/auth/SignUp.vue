<template>
	<n-spin :show="loading">
		<n-form ref="formRef" :model="model" :rules="rules">
			<n-steps :current="wizardCurrent" vertical>
				<n-step title="Account">
					<div class="pt-3" v-show="wizardCurrent === 1">
						<n-form-item path="email" label="Email">
							<n-input
								v-model:value="model.email"
								@keydown.enter="signUp"
								size="large"
								placeholder="Email..."
							/>
						</n-form-item>
						<n-form-item path="password" label="Password">
							<n-input
								v-model:value="model.password"
								type="password"
								@keydown.enter="signUp"
								size="large"
								show-password-on="click"
								placeholder="At least 8 characters"
							/>
						</n-form-item>
						<n-form-item path="confirmPassword" label="Confirm Password" first>
							<n-input
								v-model:value="model.confirmPassword"
								type="password"
								:disabled="!model.password"
								@keydown.enter="signUp"
								size="large"
								show-password-on="click"
								placeholder="At least 8 characters"
							/>
						</n-form-item>
						<div class="flex items-center justify-end mt-3">
							<n-button
								type="primary"
								@click="wizardCurrent = 2"
								size="large"
								icon-placement="right"
								:disabled="!accountStepValid"
							>
								<template #icon>
									<Icon :name="ArrowRightIcon"></Icon>
								</template>
								Next
							</n-button>
						</div>
					</div>
				</n-step>
				<n-step title="Details">
					<div class="pt-3" v-show="wizardCurrent === 2">
						<n-form-item path="username" label="Username">
							<n-input
								v-model:value="model.username"
								@keydown.enter="signUp"
								size="large"
								placeholder="Username..."
							/>
						</n-form-item>

						<!--
						<div class="propic flex gap-5 mb-5">
							<div class="avatar">
								<n-avatar :size="80" :src="model.propic" round />
							</div>
							<div class="buttons flex flex-col gap-2 justify-center">
								<ImageCropper
									v-slot="{ openCropper }"
									@crop="setCroppedImage"
									shape="circle"
									:placeholder="'Select your profile picture'"
								>
									<n-button type="primary" @click="openCropper()" size="small">
										<template #icon>
											<Icon :name="ImageIcon"></Icon>
										</template>
										{{ model.propic ? "Edit" : "Add" }} Photo
									</n-button>
								</ImageCropper>
								<n-button @click="model.propic = ''" v-if="model.propic" size="small">
									<template #icon>
										<Icon :name="RemoveImageIcon"></Icon>
									</template>
									Remove Photo
								</n-button>
							</div>
						</div>
						<n-form-item path="firstName" label="First Name">
							<n-input
								v-model:value="model.firstName"
								@keydown.enter="signUp"
								size="large"
								placeholder="First Name..."
							/>
						</n-form-item>
						<n-form-item path="lastName" label="Last Name">
							<n-input
								v-model:value="model.lastName"
								@keydown.enter="signUp"
								size="large"
								placeholder="Last Name..."
							/>
						</n-form-item>
						<n-form-item path="customerCode" label="Customer Code">
							<n-input
								v-model:value="model.customerCode"
								@keydown.enter="signUp"
								size="large"
								placeholder="Customer Code..."
							/>
						</n-form-item>
						-->

						<div class="flex items-center justify-between mt-3 gap-3">
							<n-button @click="wizardCurrent = 1" size="large">
								<template #icon>
									<Icon :name="ArrowLeftIcon"></Icon>
								</template>
								Back
							</n-button>
							<n-button
								type="primary"
								@click="signUp"
								size="large"
								:loading="loading"
								:disabled="!accountStepValid || !detailsStepValid"
							>
								<template #icon>
									<Icon :name="UserAddIcon"></Icon>
								</template>
								Create account
							</n-button>
						</div>
					</div>
				</n-step>
			</n-steps>
		</n-form>
	</n-spin>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue"

import {
	type FormInst,
	type FormValidationError,
	type FormRules,
	useMessage,
	NForm,
	NFormItem,
	NInput,
	NButton,
	NSteps,
	NStep,
	NSpin,
	type FormItemRule
} from "naive-ui"
import isEmail from "validator/es/lib/isEmail"
// import ImageCropper, { type ImageCropperResult } from "@/components/common/ImageCropper.vue"
import passwordValidator from "password-validator"
import Api from "@/api"
import type { RegisterPayload } from "@/types/auth.d"
import Icon from "@/components/common/Icon.vue"

interface ModelType {
	email: string
	password: string
	username: string
	confirmPassword: string
	/*
	customerCode: string
	firstName: string
	lastName: string
	propic: string
	*/
}

const emit = defineEmits<{
	(e: "goto-signin"): void
}>()

const ArrowRightIcon = "carbon:arrow-right"
const ArrowLeftIcon = "carbon:arrow-left"
// const ImageIcon = "carbon:image"
// const RemoveImageIcon = "carbon:no-image"
const UserAddIcon = "carbon:user-admin"

const wizardCurrent = ref(1)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	email: "",
	password: "",
	confirmPassword: "",
	username: ""
	/*
	customerCode: "",
	firstName: "",
	lastName: "",
	propic: ""
	*/
})

const accountStepValid = computed(() => !!model.value.email && !!model.value.password && !!model.value.confirmPassword)
const detailsStepValid = computed(() => !!model.value.username)
//const detailsStepValid = computed(() => !!model.value.customerCode && !!model.value.firstName && !!model.value.lastName)

const passwordSchema = new passwordValidator()
passwordSchema
	.is()
	.min(8) // Minimum length 8
	.is()
	.max(100) // Maximum length 100
	.has()
	.uppercase() // Must have uppercase letters
	.has()
	.lowercase() // Must have lowercase letters
	.has()
	.digits(1) // Must have at least 1 digit
	.has()
	.symbols(1) // Must have at least 1 symbol

const rules: FormRules = {
	email: [
		{
			required: true,
			trigger: ["blur"],
			message: "Email is required"
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return isEmail(value)
			},
			message: "The email is not formatted correctly",
			trigger: ["blur"]
		}
	],
	password: [
		{
			required: true,
			trigger: ["blur"],
			message: "Password is required"
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return !!passwordSchema.validate(value, { details: false })
			},
			message:
				"The string should have a minimum length of 8 characters, minimum of 1 uppercase and lowercase letter, minimum of 1 digit and 1 symbol",
			trigger: ["blur"]
		}
	],
	confirmPassword: [
		{
			required: true,
			trigger: ["blur"],
			message: "Confirm Password is required"
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return value === model.value.password
			},
			message: "Password is not same as re-entered password",
			trigger: ["blur", "password-input"]
		}
	],
	username: [
		{
			required: true,
			trigger: ["blur"],
			message: "Username Code is required"
		}
	]
	/*
	customerCode: [
		{
			required: true,
			trigger: ["blur"],
			message: "Customer Code is required"
		}
	],
	firstName: [
		{
			required: true,
			trigger: ["blur"],
			message: "First Name is required"
		}
	],
	lastName: [
		{
			required: true,
			trigger: ["blur"],
			message: "Last Name is required"
		}
	]
	*/
}

function signUp(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			loading.value = true

			const payload: RegisterPayload = {
				password: model.value.password,
				email: model.value.email,
				username: model.value.username,
				role_id: 1
				/*
				customerCode: model.value.customerCode,
				usersFirstName: model.value.firstName,
				usersLastName: model.value.lastName,
				usersEmail: model.value.email,
				usersRole: "admin",
				imageFile: model.value.propic,
				notifications: 0,
				*/
			}

			Api.auth
				.register(payload)
				.then(res => {
					if (res.data.success) {
						message.success("User registered successfully. Please log in.")
						emit("goto-signin")
					} else {
						message.warning(res.data?.message || "An error occurred. Please try again later.")
					}
				})
				.catch(err => {
					message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				})
				.finally(() => {
					loading.value = false
				})
		} else {
			for (const err of errors) {
				message.error(err[0].message || "Invalid fields")
			}
		}
	})
}
/*
function setCroppedImage(result: ImageCropperResult) {
	const canvas = result.canvas as HTMLCanvasElement
	// model.value.propic = canvas.toDataURL()
}
*/
</script>
