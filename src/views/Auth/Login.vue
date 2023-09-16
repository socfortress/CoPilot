<template>
	<div class="page">
		<div class="settings flex items-center justify-between">
			<div class="layout">
				<n-button quaternary circle @click="align = 'left'">
					<template #icon>
						<n-icon>
							<AlignLeftActive v-if="align === 'left'" />
							<AlignLeft v-else />
						</n-icon>
					</template>
				</n-button>
				<n-button quaternary circle @click="align = 'center'">
					<template #icon>
						<n-icon>
							<AlignCenterActive v-if="align === 'center'" />
							<AlignCenter v-else />
						</n-icon>
					</template>
				</n-button>
				<n-button quaternary circle @click="align = 'right'">
					<template #icon>
						<n-icon>
							<AlignRightActive v-if="align === 'right'" />
							<AlignRight v-else />
						</n-icon>
					</template>
				</n-button>
			</div>
			<div class="colors">
				<n-button quaternary circle v-for="color of colors" :key="color" @click="activeColor = color">
					<template #icon>
						<n-icon :color="color">
							<SquareActive v-if="activeColor === color" />
							<Square v-else />
						</n-icon>
					</template>
				</n-button>
				<n-button quaternary circle @click="activeColor = primaryColor">
					<template #icon>
						<n-icon :color="primaryColor">
							<SquareActive v-if="activeColor === primaryColor" />
							<Square v-else />
						</n-icon>
					</template>
				</n-button>
			</div>
		</div>
		<div class="flex wrapper justify-center">
			<div class="image-box basis-2/3" v-if="align === 'right'"></div>
			<div class="form-box basis-1/3 flex items-center justify-center" :class="{ centered: align === 'center' }">
				<SignInUp :type="type" />
			</div>
			<div class="image-box basis-2/3" v-if="align === 'left'"></div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NButton, NIcon } from "naive-ui"
import SignInUp from "@/components/SignInUp"
import AlignLeft from "@vicons/fluent/TextboxAlignBottomRotate9024Regular"
import AlignCenter from "@vicons/fluent/TextboxAlignMiddleRotate9024Regular"
import AlignRight from "@vicons/fluent/TextboxAlignTopRotate9024Regular"
import AlignLeftActive from "@vicons/fluent/TextboxAlignBottomRotate9024Filled"
import AlignCenterActive from "@vicons/fluent/TextboxAlignMiddleRotate9024Filled"
import AlignRightActive from "@vicons/fluent/TextboxAlignTopRotate9024Filled"
import Square from "@vicons/fluent/Square24Filled"
import SquareActive from "@vicons/fluent/CheckboxIndeterminate24Regular"
import { ref, computed, onBeforeMount } from "vue"
import { useRoute } from "vue-router"
import { useThemeStore } from "@/stores/theme"
import { type FormType } from "@/components/SignInUp/SignInUp.vue"

defineOptions({
	name: "Login"
})

type Align = "left" | "center" | "right"

const route = useRoute()
const align = ref<Align>("left")
const activeColor = ref("")
const type = ref<FormType | undefined>(undefined)

const colors = computed(() => useThemeStore().secondaryColors)
const primaryColor = computed(() => useThemeStore().primaryColor)

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
		backdrop-filter: blur(10px);
		background-color: rgba(var(--bg-color-rgb), 0.4);
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
