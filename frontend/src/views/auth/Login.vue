<template>
	<div class="page-auth">
		<div class="flex wrapper justify-center" v-if="!isLogged">
			<div class="image-box basis-2/3" v-if="align === 'right'"></div>
			<div class="form-box basis-1/3 flex items-center justify-center" :class="{ centered: align === 'center' }">
				<AuthForm :type="type" />
			</div>
			<div class="image-box basis-2/3" v-if="align === 'left'">
				<video playsinline autoplay muted loop poster="/images/login/cover.webp">
					<source src="/images/login/video.mp4" type="video/mp4" />
					Your browser does not support the video tag.
				</video>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import AuthForm from "@/components/auth/AuthForm.vue"
import { ref, computed, onBeforeMount, toRefs } from "vue"
import { useRoute } from "vue-router"
import { useThemeStore } from "@/stores/theme"
import { useAuthStore } from "@/stores/auth"
import type { FormType } from "@/components/auth/types.d"

type Align = "left" | "center" | "right"

const props = defineProps<{
	formType?: FormType
}>()
const { formType } = toRefs(props)

const route = useRoute()
const align = ref<Align>("left")
const type = ref<FormType | undefined>(formType.value || undefined)

const themeStore = useThemeStore()
const activeColor = computed(() => themeStore.primaryColor)
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
@import "./main.scss";

.page-auth {
	.wrapper {
		.image-box {
			background-color: v-bind(activeColor);

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
	}
}
</style>
