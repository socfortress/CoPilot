<template>
	<div class="page">
		<div class="settings flex items-center justify-between" v-if="!isLogged">
			<div class="layout">
				<n-button quaternary circle @click="align = 'left'">
					<template #icon>
						<Icon>
							<Iconify :icon="AlignLeftActive" v-if="align === 'left'" />
							<Iconify :icon="AlignLeft" v-else />
						</Icon>
					</template>
				</n-button>
				<n-button quaternary circle @click="align = 'center'">
					<template #icon>
						<Icon>
							<Iconify :icon="AlignCenterActive" v-if="align === 'center'" />
							<Iconify :icon="AlignCenter" v-else />
						</Icon>
					</template>
				</n-button>
				<n-button quaternary circle @click="align = 'right'">
					<template #icon>
						<Icon>
							<Iconify :icon="AlignRightActive" v-if="align === 'right'" />
							<Iconify :icon="AlignRight" v-else />
						</Icon>
					</template>
				</n-button>
			</div>
			<div class="colors">
				<n-button quaternary circle v-for="color of colors" :key="color" @click="activeColor = color">
					<template #icon>
						<Icon :color="color">
							<Iconify :icon="SquareActive" v-if="activeColor === color" />
							<Iconify :icon="Square" v-else />
						</Icon>
					</template>
				</n-button>
				<n-button quaternary circle @click="activeColor = primaryColor">
					<template #icon>
						<Icon :color="primaryColor">
							<Iconify :icon="SquareActive" v-if="activeColor === primaryColor" />
							<Iconify :icon="Square" v-else />
						</Icon>
					</template>
				</n-button>
			</div>
		</div>
		<div class="flex wrapper justify-center" v-if="!isLogged">
			<div class="image-box basis-2/3" v-if="align === 'right'"></div>
			<div class="form-box basis-1/3 flex items-center justify-center" :class="{ centered: align === 'center' }">
				<AuthForm :type="type" />
			</div>
			<div class="image-box basis-2/3" v-if="align === 'left'"></div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { Icon as Iconify } from "@iconify/vue"

import AuthForm from "@/components/AuthForm/index.vue"
import { ref, computed, onBeforeMount } from "vue"
import { useRoute } from "vue-router"
import { useThemeStore } from "@/stores/theme"
import { useAuthStore } from "@/stores/auth"
import type { FormType } from "@/components/AuthForm/index.vue"

const AlignLeft = "fluent:textbox-align-bottom-rotate-90-24-regular"
const AlignCenter = "fluent:textbox-align-middle-rotate-90-24-regular"
const AlignRight = "fluent:textbox-align-top-rotate-90-24-regular"
const AlignLeftActive = "fluent:textbox-align-bottom-rotate-90-24-filled"
const AlignCenterActive = "fluent:textbox-align-middle-rotate-90-24-filled"
const AlignRightActive = "fluent:textbox-align-top-rotate-90-24-filled"
const Square = "fluent:square-24-filled"
const SquareActive = "fluent:checkbox-indeterminate-24-regular"

type Align = "left" | "center" | "right"

const route = useRoute()
const align = ref<Align>("left")
const activeColor = ref("")
const type = ref<FormType | undefined>(undefined)

const colors = computed(() => useThemeStore().secondaryColors)
const primaryColor = computed(() => useThemeStore().primaryColor)
const isLogged = computed(() => useAuthStore().isLogged)

onBeforeMount(() => {
	if (route.query.step) {
		const step = route.query.step as FormType
		type.value = step
	}
	activeColor.value = primaryColor.value
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/common.scss";

.page {
	min-height: 100vh;

	.settings {
		position: fixed;
		top: 10px;
		left: 50%;
		transform: translateX(-50%);
		background-color: var(--bg-secondary-color);
		height: 44px;
		width: 300px;
		border-radius: 50px;
		padding: 5px;
		z-index: 1;
	}

	.wrapper {
		min-height: 100vh;

		.image-box {
			background-color: v-bind(activeColor);
			position: relative;

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
		}

		.form-box {
			padding: 50px;

			&.centered {
				flex-basis: 100%;
				.form-wrap {
					padding: 60px;
					width: 100%;
					max-width: 500px;
					background-color: var(--bg-color);
					border-radius: 20px;
					@apply shadow-xl;
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
		.settings {
			width: 112px;
			.colors {
				display: none;
			}
		}
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
