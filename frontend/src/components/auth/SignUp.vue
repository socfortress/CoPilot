<template>
	<n-spin :show="loading">
		<n-form ref="formRef" :model="model" :rules="rules">
			<n-steps :current="wizardCurrent" vertical>
				<n-step title="Account">
					<div v-show="wizardCurrent === 1" class="pt-3">
						<n-form-item path="email" label="Email" first>
							<n-input
								v-model:value="model.email"
								size="large"
								placeholder="Email..."
								@keydown.enter="signUp"
							/>
						</n-form-item>
						<n-form-item path="password" label="Password" first>
							<n-input
								v-model:value="model.password"
								type="password"
								size="large"
								show-password-on="click"
								placeholder="At least 8 characters"
								@keydown.enter="signUp"
							/>
						</n-form-item>
						<n-form-item path="confirmPassword" label="Confirm Password" first>
							<n-input
								v-model:value="model.confirmPassword"
								type="password"
								:disabled="!model.password"
								size="large"
								show-password-on="click"
								placeholder="At least 8 characters"
								@keydown.enter="signUp"
							/>
						</n-form-item>
						<div class="mt-3 flex items-center justify-end">
							<n-button
								type="primary"
								size="large"
								icon-placement="right"
								:disabled="!accountStepValid"
								@click="wizardCurrent = 2"
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
					<div v-show="wizardCurrent === 2" class="pt-3">
						<n-form-item path="username" label="Username" first>
							<n-input
								v-model:value="model.username"
								size="large"
								placeholder="Username..."
								@keydown.enter="signUp"
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

						<div class="mt-3 flex items-center justify-between gap-3">
							<n-button size="large" @click="wizardCurrent = 1">
								<template #icon>
									<Icon :name="ArrowLeftIcon"></Icon>
								</template>
								Back
							</n-button>
							<n-button
								type="success"
								size="large"
								:loading="loading"
								:disabled="!accountStepValid || !detailsStepValid"
								@click="signUp"
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
import type { RegisterPayload } from "@/types/auth.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import _trim from "lodash/trim"
import {
	type FormInst,
	type FormItemRule,
	type FormRules,
	type FormValidationError,
	NButton,
	NForm,
	NFormItem,
	NInput,
	NSpin,
	NStep,
	NSteps,
	useMessage
} from "naive-ui"
import PasswordValidator from "password-validator"
import isEmail from "validator/es/lib/isEmail"
import { computed, ref } from "vue"
// import ImageCropper, { type ImageCropperResult } from "@/components/common/ImageCropper.vue"

interface ModelType {
	email: string | null
	password: string | null
	username: string | null
	confirmPassword: string | null
	/*
	customerCode: string | null
	firstName: string | null
	lastName: string | null
	propic: string | null
	*/
}

const { unavailableUsernameList, unavailableEmailList } = defineProps<{
	unavailableUsernameList?: string[]
	unavailableEmailList?: string[]
}>()

const emit = defineEmits<{
	(e: "success"): void
}>()

// const ImageIcon = "carbon:image"
// const RemoveImageIcon = "carbon:no-image"
const ArrowRightIcon = "carbon:arrow-right"
const ArrowLeftIcon = "carbon:arrow-left"
const UserAddIcon = "carbon:user-admin"

const wizardCurrent = ref(1)
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>(getModel())

const accountStepValid = computed(
	() =>
		!!_trim(model.value.email || "") &&
		!!model.value.password &&
		!!model.value.confirmPassword &&
		model.value.password === model.value.confirmPassword
)
const detailsStepValid = computed(() => !!_trim(model.value.username || ""))
// const detailsStepValid = computed(() => !!model.value.customerCode && !!model.value.firstName && !!model.value.lastName)

const passwordSchema = new PasswordValidator()
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
			trigger: ["blur", "input"],
			message: "Email is required"
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return isEmail(value)
			},
			message: "The email is not formatted correctly",
			trigger: ["blur", "input"]
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return !unavailableEmailList?.length || !unavailableEmailList.includes(value)
			},
			message: "The Email is already used",
			trigger: ["blur", "input"]
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
			trigger: ["blur", "input"],
			message: "Confirm Password is required"
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return value === model.value.password
			},
			message: "Password is not same as re-entered password",
			trigger: ["blur"]
		}
	],
	username: [
		{
			required: true,
			trigger: ["blur", "input"],
			message: "Username is required"
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return !unavailableUsernameList?.length || !unavailableUsernameList.includes(value)
			},
			message: "The Username is already used",
			trigger: ["blur", "input"]
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

function getModel(): ModelType {
	return {
		email: null,
		password: null,
		confirmPassword: null,
		username: null
		/*
		customerCode: null,
		firstName: null,
		lastName: null,
		propic: null
		*/
	}
}

function reset() {
	model.value = getModel()
	wizardCurrent.value = 1
}

function signUp(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			loading.value = true

			const payload: RegisterPayload = {
				password: model.value.password || "",
				email: _trim(model.value.email || ""),
				username: _trim(model.value.username || ""),
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
						message.success("User registered successfully.")
						reset()
						emit("success")
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
