<template>
	<div class="page-auth">
		<div v-if="!isLogged" class="wrapper flex justify-center">
			<div v-if="align === 'right'" class="image-box basis-2/3" />
			<div class="form-box flex basis-1/3 items-center justify-center" :class="{ centered: align === 'center' }">
				<AuthForm :type="type" />
			</div>
			<div v-if="align === 'left'" class="image-box basis-2/3">
				<video playsinline autoplay muted loop poster="/images/login/cover.webp">
					<source src="/images/login/video.mp4" type="video/mp4" />
					Your browser does not support the video tag.
				</video>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import type { FormType } from "@/components/auth/types.d"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { useRoute } from "vue-router"
import AuthForm from "@/components/auth/AuthForm.vue"
import { useAuthStore } from "@/stores/auth"
import { useThemeStore } from "@/stores/theme"

type Align = "left" | "center" | "right"

const props = defineProps<{
	formType?: FormType
}>()
const { formType } = toRefs(props)

const route = useRoute()
const align = ref<Align>("left")
const type = ref<FormType | undefined>(formType.value || undefined)

const themeStore = useThemeStore()
const activeColor = computed(() => themeStore.style["primary-color"])
const authStore = useAuthStore()
const isLogged = computed(() => authStore.isLogged)

onBeforeMount(() => {
	if (route.query.step) {
		const step = route.query.step as FormType
		type.value = step
	}
})
</script>

<style lang="scss" scoped>
.page-auth {
	min-height: 100svh;

	.wrapper {
		min-height: 100svh;

		.image-box {
			position: relative;
			background-color: v-bind(activeColor);

			/*
			&::after {
				content: "";
				width: 100%;
				height: 100%;
				position: absolute;
				top: 0;
				left: 0;
				background-image: url(@/assets/images/pattern-onboard.png);
				background-size: 500px;
				background-position: center center;
			}
			*/

			video {
				position: absolute;
				top: 0;
				left: 0;
				width: 100%;
				height: 100%;
				object-fit: cover;
				object-position: center;
			}
		}

		.form-box {
			padding: 50px;

			&.centered {
				flex-basis: 100%;

				.form-wrap {
					padding: 60px;
					width: 100%;
					max-width: 500px;
				}

				@media (max-width: 600px) {
					padding: 4%;
					.form-wrap {
						padding: 8%;
					}
				}
			}
		}
	}

	@media (max-width: 800px) {
		.wrapper {
			.image-box {
				display: none;
			}

			.form-box {
				flex-basis: 100%;
			}
		}
	}
}
</style>
