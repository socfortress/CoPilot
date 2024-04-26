<template>
	<n-button :size="size" :type="type" @click="showFormDrawer = true">
		<template #icon>
			<Icon :name="PasswordIcon" :size="14"></Icon>
		</template>
		Change Password
	</n-button>

	<n-drawer
		v-model:show="showFormDrawer"
		:width="500"
		style="max-width: 90vw"
		:trap-focus="false"
		display-directive="show"
	>
		<n-drawer-content title="Change Password" closable :native-scrollbar="false">
			<n-spin :show="loading">
				<n-form ref="formRef" :model="model" :rules="rules">
					<div class="flex flex-col gap-3">
						<n-form-item label="Username" required>
							<n-input :value="username" disabled readonly />
						</n-form-item>
						<n-form-item path="password" label="Password">
							<n-input
								v-model:value="model.password"
								type="password"
								@keydown.enter="submit"
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
								@keydown.enter="submit"
								size="large"
								show-password-on="click"
								placeholder="At least 8 characters"
							/>
						</n-form-item>

						<div class="flex justify-end">
							<n-button type="primary" :disabled="!isValid" @click="submit">Send new password</n-button>
						</div>
					</div>
				</n-form>
			</n-spin>
		</n-drawer-content>
	</n-drawer>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue"
import {
	useMessage,
	NDrawer,
	NDrawerContent,
	NForm,
	NFormItem,
	NInput,
	NButton,
	NSpin,
	type FormInst,
	type FormValidationError,
	type FormRules,
	type FormItemRule
} from "naive-ui"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import passwordValidator from "password-validator"
import Icon from "@/components/common/Icon.vue"
import type { Size, Type } from "naive-ui/es/button/src/interface"

const { type, size, username } = defineProps<{
	username: string
	size?: Size
	type?: Type
}>()

const showFormDrawer = ref(false)

watch(showFormDrawer, () => {
	clear()
})

const PasswordIcon = "carbon:password"
const message = useMessage()
const loading = ref(false)
const model = ref({
	password: "",
	confirmPassword: ""
})
const formRef = ref<FormInst | null>(null)
const storedUserName = useAuthStore().userName
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
	]
}

const isValid = computed(() => {
	return !!model.value.password && !!model.value.confirmPassword && !!username
})

function clear() {
	model.value.password = ""
	model.value.confirmPassword = ""
}

function submit(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			loading.value = true

			const method = username === storedUserName ? "resetOwnPassword" : "resetPassword"

			Api.auth[method](username, model.value.password)
				.then(res => {
					if (res.data.success) {
						clear()
						message.success(res.data?.message || "New Password submitted.")
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
</script>
