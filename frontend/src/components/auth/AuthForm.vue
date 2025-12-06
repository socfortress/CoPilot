<template>
	<div class="w-full max-w-96 min-w-64">
		<div>
			<Logo type="small" class="mb-4" max-height="40px" />
			<div class="font-display mb-4 text-4xl font-bold" data-test="login-title">
				{{ title }}
			</div>
			<div class="text-secondary text-lg">
				Access the world of OpenSource security: Simplified, Streamlined, Accessible.
			</div>
		</div>

		<transition name="form-fade" mode="out-in" appear class="my-10">
			<SignIn v-if="type === 'signin'" key="signin" />
		</transition>
	</div>
</template>

<script lang="ts" setup>
import type { FormType } from "./types.d"
import { computed, onBeforeMount, ref } from "vue"
import Logo from "@/app-layouts/common/Logo.vue"
import SignIn from "./SignIn.vue"

const props = defineProps<{
	type?: FormType
}>()

const type = ref<FormType>("signin")
const title = computed<string>(() =>
	type.value === "signin"
		? "SOCFortress CoPilot"
		: type.value === "signup"
			? "SOCFortress CoPilot"
			: "Forgot Password"
)

onBeforeMount(() => {
	if (props.type) {
		type.value = props.type
	}
})
</script>

<style lang="scss" scoped>
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
