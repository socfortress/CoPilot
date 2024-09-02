<template>
	<div class="form-wrap">
		<Logo mini :dark="isDark" class="mb-4" />
		<div class="title mb-4">{{ title }}</div>
		<div class="text mb-12">Access the world of OpenSource security: Simplified, Streamlined, Accessible.</div>

		<div class="form">
			<transition name="form-fade" mode="out-in" appear>
				<SignIn v-if="typeRef === 'signin'" key="signin" @goto-forgot-password="gotoForgotPassword()" />
				<ForgotPassword v-else-if="typeRef === 'forgotpassword'" key="forgotpassword" />
				<SignUp v-else-if="typeRef === 'signup'" key="signup" @goto-signin="gotoSignIn()" />
			</transition>
		</div>

		<div class="sign-text text-center mt-10">
			<div class="sign-text" v-if="typeRef === 'signin'">
				Don't you have an account?
				<n-button text @click="gotoSignUp()" type="primary" size="large">Sign up</n-button>
			</div>
			<div class="sign-text" v-if="typeRef === 'forgotpassword'">
				<n-button text @click="gotoSignIn()" type="primary" size="large">Back to Sign in</n-button>
			</div>
			<div class="sign-text" v-if="typeRef === 'signup'">
				Do you have an account?
				<n-button text @click="gotoSignIn()" type="primary" size="large">Sign in</n-button>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import SignIn from "./SignIn.vue"
import ForgotPassword from "./ForgotPassword.vue"
import SignUp from "./SignUp.vue"
import Logo from "@/layouts/common/Logo.vue"
import { NButton } from "naive-ui"
import { ref, onBeforeMount, computed } from "vue"
import { useRouter } from "vue-router"
import type { FormType } from "./types.d"

const props = defineProps<{
	type?: FormType
	useOnlyRouter?: boolean
}>()

const typeRef = ref<FormType>("signin")
const router = useRouter()
const themeStore = useThemeStore()
const isDark = computed<boolean>(() => themeStore.isThemeDark)
const title = computed<string>(() =>
	typeRef.value === "signin"
		? "SOCFortress CoPilot"
		: typeRef.value === "signup"
		? "SOCFortress CoPilot"
		: "Forgot Password"
)

function gotoSignIn() {
	if (!props.useOnlyRouter) {
		typeRef.value = "signin"
	}
	router.replace({ name: "Login" })
}

function gotoSignUp() {
	if (!props.useOnlyRouter) {
		typeRef.value = "signup"
	}
	router.replace({ name: "Register" })
}

function gotoForgotPassword() {
	if (!props.useOnlyRouter) {
		typeRef.value = "forgotpassword"
	}
}

onBeforeMount(() => {
	if (props.type) {
		typeRef.value = props.type
	}
})

onBeforeMount(() => {
	if (props.type) {
		typeRef.value = props.type
	}
})
</script>

<style lang="scss" scoped>
.form-wrap {
	width: 100%;
	min-width: 270px;
	max-width: 400px;

	.logo {
		:deep(img) {
			max-height: 37px;
		}
	}

	.title {
		font-size: 36px;
		font-family: var(--font-family-display);
		line-height: 1.2;
		font-weight: 700;
	}
	.text {
		font-size: 18px;
		line-height: 1.3;
		color: var(--fg-secondary-color);
	}
}

.form-fade-enter-active,
.form-fade-leave-active {
	transition:
		opacity 0.2s ease-in-out,
		transform 0.3s ease-in-out;
}
.form-fade-enter-from {
	opacity: 0;
	transform: translateX(10px);
}
.form-fade-leave-to {
	opacity: 0;
	transform: translateX(-10px);
}
</style>
