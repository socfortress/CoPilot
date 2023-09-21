<template>
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
					<div class="flex items-center justify-end">
						<n-button type="primary" @click="wizardCurrent = 2" size="large" icon-placement="right">
							<template #icon>
								<n-icon>
									<ArrowRightIcon />
								</n-icon>
							</template>
							Next
						</n-button>
					</div>
				</div>
			</n-step>
			<n-step title="Details">
				<div class="pt-3" v-show="wizardCurrent === 2">
					<div class="propic flex gap-5 mb-5">
						<div class="avatar">
							<n-avatar :size="80" :src="model.propic" round />
						</div>
						<div class="buttons flex flex-col gap-2 justify-center">
							<ImageCropper
								v-slot="{ openCropper }"
								@crop="setCroppedImage"
								:placeholder="'Select your profile picture'"
							>
								<n-button type="primary" @click="openCropper()" size="small">
									<template #icon>
										<n-icon>
											<ImageIcon />
										</n-icon>
									</template>
									{{ model.propic ? "Edit" : "Add" }} Photo
								</n-button>
							</ImageCropper>
							<n-button @click="model.propic = ''" v-if="model.propic" size="small">
								<template #icon>
									<n-icon>
										<RemoveImageIcon />
									</n-icon>
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

					<div class="flex items-center justify-between">
						<n-button @click="wizardCurrent = 1" size="large">
							<template #icon>
								<n-icon>
									<ArrowLeftIcon />
								</n-icon>
							</template>
							Back
						</n-button>
						<n-button type="primary" @click="signUp" size="large">
							<template #icon>
								<n-icon>
									<UserAddIcon />
								</n-icon>
							</template>
							Create account
						</n-button>
					</div>
				</div>
			</n-step>
		</n-steps>
	</n-form>
</template>

<script lang="ts" setup>
import { ref } from "vue"

import {
	type FormInst,
	type FormValidationError,
	useMessage,
	type FormRules,
	NForm,
	NFormItem,
	NInput,
	NButton,
	NSteps,
	NStep,
	NIcon,
	NAvatar,
	type FormItemRule
} from "naive-ui"
import { useAuthStore } from "@/stores/auth"
import { useRouter } from "vue-router"
import ArrowRightIcon from "@vicons/carbon/ArrowRight"
import ArrowLeftIcon from "@vicons/carbon/ArrowLeft"
import ImageIcon from "@vicons/carbon/Image"
import RemoveImageIcon from "@vicons/carbon/NoImage"
import UserAddIcon from "@vicons/carbon/UserAdmin"
import ImageCropper, { type ImageCropperResult } from "@/components/common/ImageCropper.vue"

interface ModelType {
	email: string
	password: string
	confirmPassword: string
	customerCode: string
	firstName: string
	lastName: string
	propic: string
}

const wizardCurrent = ref(1)
const router = useRouter()
const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	email: "",
	password: "",
	confirmPassword: "",
	customerCode: "",
	firstName: "",
	lastName: "",
	propic: ""
})

const rules: FormRules = {
	email: [
		{
			required: true,
			trigger: ["blur"],
			message: "Email is required"
		}
	],
	password: [
		{
			required: true,
			trigger: ["blur"],
			message: "Password is required"
		}
	],
	confirmPassword: [
		{
			required: true,
			trigger: ["blur"],
			message: "confirmPassword is required"
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return value === model.value.password
			},
			message: "Password is not same as re-entered password!",
			trigger: ["blur", "password-input"]
		}
	]
}

function signUp(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			if (model.value.email === "admin@admin.com" && model.value.password === "password") {
				useAuthStore().setLogged()
				router.push({ path: "/", replace: true })
			} else {
				message.error("Invalid credentials")
			}
		} else {
			message.error("Invalid credentials")
		}
	})
}

function setCroppedImage(result: ImageCropperResult) {
	const canvas = result.canvas as HTMLCanvasElement
	model.value.propic = canvas.toDataURL()
}
</script>
