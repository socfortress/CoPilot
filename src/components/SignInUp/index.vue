<template>
	<div class="form-wrap">
		<div class="logo mb-4">
			<img src="@/assets/images/brand-logo_dark.svg?url" v-if="isDark" />
			<img src="@/assets/images/brand-logo_light.svg?url" v-else />
		</div>
		<div class="title mb-4">{{ title }}</div>
		<div class="text mb-12">
			Today is a new day. It's your day. You shape it. Sign in to start managing your projects.
		</div>

		<div class="form">
			<transition name="form-fade" mode="out-in" appear>
				<SignIn v-if="typeRef === 'signin'" key="signin" @forgot-password="gotoForgotPassword()" />
				<ForgotPassword v-else-if="typeRef === 'forgotpassword'" key="forgotpassword" />
				<SignUp v-else-if="typeRef === 'signup'" key="signup" />
			</transition>
		</div>

		<n-divider title-placement="center">Or</n-divider>

		<div class="social-btns flex flex-col gap-4 mb-12">
			<n-button strong secondary size="large">
				<span class="b-icon">
					<img src="@/assets/images/google-icon.svg?url" />
				</span>
				Sign in with Google
			</n-button>
			<n-button strong secondary>
				<span class="b-icon" size="large">
					<img src="@/assets/images/facebook-icon.svg?url" />
				</span>
				Sign in with Facebook
			</n-button>
		</div>

		<div class="sign-text text-center">
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
import { NButton, NDivider } from "naive-ui"
import { ref, onBeforeMount, computed } from "vue"

export type FormType = "signin" | "signup" | "forgotpassword"

const props = defineProps<{
	type?: FormType
}>()

const typeRef = ref<FormType>("signin")

const isDark = computed<boolean>(() => useThemeStore().isThemeDark)
const title = computed<string>(() =>
	typeRef.value === "signin" ? "Welcome Back" : typeRef.value === "signup" ? "Hello" : "Forgot Password"
)

function gotoSignIn() {
	typeRef.value = "signin"
}
function gotoSignUp() {
	typeRef.value = "signup"
}
function gotoForgotPassword() {
	typeRef.value = "forgotpassword"
}

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

	.social-btns {
		.b-icon {
			margin-right: 16px;

			img {
				display: block;
				height: 20px;
			}
		}
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
