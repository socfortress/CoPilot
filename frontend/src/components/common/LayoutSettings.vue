<template>
	<div class="layout-settings flex items-center justify-center shadow-xl" :class="{ open }">
		<Transition mode="out-in" name="anim">
			<div class="open-btn flex items-center justify-center" @click="open = true" v-if="!open" key="btn">
				<Icon :size="24" :name="SettingsIcon"></Icon>
			</div>

			<div class="ls-form flex flex-col" v-else key="form">
				<div class="ls-header flex items-center justify-between">
					<div class="ls-title">Layout settings</div>
					<div class="ls-icon flex items-center">
						<Icon @click="open = false" :size="20" :name="CloseIcon"></Icon>
					</div>
				</div>
				<n-scrollbar class="ls-main">
					<div class="ls-section ls-color-selection">
						<div class="ls-label">Primary color</div>
						<div class="color-picker-box">
							<n-color-picker
								v-model:value="darkColor"
								:modes="['hex']"
								:show-alpha="false"
								v-if="theme === ThemeEnum.Dark"
							/>
							<n-color-picker v-model:value="lightColor" :modes="['hex']" :show-alpha="false" v-else />
						</div>
						<div class="palette flex justify-around mt-3">
							<n-button text v-for="color of palette" :key="color.light" @click="setPrimary(color)">
								<template #icon>
									<Icon
										:color="theme === ThemeEnum.Dark ? color.dark : color.light"
										:size="24"
										:name="ColorIcon"
									></Icon>
								</template>
							</n-button>
						</div>
					</div>

					<div class="ls-section ls-theme-selection">
						<div class="ls-label">Theme</div>
						<div class="flex items-center gap-2">
							<div class="basis-1/2">
								<n-button
									class="!w-full"
									@click="theme = ThemeEnum.Light"
									:type="theme === ThemeEnum.Light ? 'primary' : 'default'"
								>
									<template #icon>
										<Icon :name="LightIcon" v-if="theme === ThemeEnum.Light"></Icon>
										<Icon :name="LightOutlineIcon" v-else></Icon>
									</template>
									Light
								</n-button>
							</div>
							<div class="basis-1/2">
								<n-button
									class="!w-full"
									@click="theme = ThemeEnum.Dark"
									:type="theme === ThemeEnum.Dark ? 'primary' : 'default'"
								>
									<template #icon>
										<Icon :name="DarkIcon" v-if="theme === ThemeEnum.Dark"></Icon>
										<Icon :name="DarkOutlineIcon" v-else></Icon>
									</template>
									Dark
								</n-button>
							</div>
						</div>
					</div>

					<div class="ls-section ls-nav-selection">
						<div class="ls-label">
							Navbar
							<span v-if="isMobileView" class="text-secondary-color">(desktop only)</span>
						</div>
						<div class="flex items-center gap-2">
							<div class="basis-1/2">
								<!--
									<n-button
									class="!w-full"
									@click="layout = Layout.VerticalNav"
									:type="layout === Layout.VerticalNav ? 'primary' : 'default'"
									:disabled="isMobileView"
									>
										Vertical
									</n-button>
								-->
							</div>
							<div class="basis-1/2">
								<n-button
									class="!w-full"
									@click="layout = Layout.HorizontalNav"
									:type="layout === Layout.HorizontalNav ? 'primary' : 'default'"
									:disabled="isMobileView"
								>
									Horizontal
								</n-button>
							</div>
						</div>
					</div>
					<div class="ls-section ls-boxed-selection">
						<div class="flex flex-col gap-3">
							<div class="flex justify-between items-center">
								<div class="switch-label">
									View boxed
									<span v-if="isMobileView" class="text-secondary-color px-1">desktop only</span>
								</div>
								<n-switch v-model:value="boxed" :disabled="isMobileView" size="small" />
							</div>
							<div class="flex justify-between items-center">
								<div class="switch-label">
									Toolbar boxed
									<span v-if="isMobileView" class="text-secondary-color px-1">desktop only</span>
								</div>
								<n-switch
									v-model:value="toolbarBoxed"
									:disabled="!boxed || isMobileView"
									size="small"
								/>
							</div>
							<div class="flex justify-between items-center">
								<div class="switch-label">Footer visible</div>
								<n-switch v-model:value="footerShown" size="small" />
							</div>
							<div class="flex justify-between items-center">
								<div class="switch-label">
									RTL
									<span class="text-secondary-color px-1">beta</span>
								</div>
								<n-switch v-model:value="rtl" size="small" />
							</div>
						</div>
					</div>

					<div class="ls-section ls-transition-selection">
						<div class="ls-label">Router transition</div>
						<div class="ls-input flex justify-between">
							<n-select v-model:value="routerTransition" :options="transitionOptions"></n-select>
						</div>
					</div>
					<div class="ls-section ls-reset-selection items-center">
						<n-button class="!w-full !mb-3" strong secondary type="primary" @click="reset()">
							Restore default
						</n-button>
						<a
							href="https://pinx-docs.vercel.app/layout"
							target="_blank"
							alt="docs"
							rel="nofollow noopener noreferrer"
						>
							Other settings
						</a>
					</div>
				</n-scrollbar>
			</div>
		</Transition>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import { NColorPicker, NButton, NSelect, useOsTheme, NScrollbar, NSwitch } from "naive-ui"
import { useThemeStore } from "@/stores/theme"
import Icon from "@/components/common/Icon.vue"
import { Layout, RouterTransition, ThemeEnum } from "@/types/theme.d"
import { useWindowSize } from "@vueuse/core"

interface ColorPalette {
	light: string
	dark: string
}

type Palette = ColorPalette[]

const SettingsIcon = "carbon:settings-adjust"
const CloseIcon = "carbon:close"
const LightIcon = "ion:sunny"
const DarkIcon = "ion:moon"
const LightOutlineIcon = "ion:sunny-outline"
const DarkOutlineIcon = "ion:moon-outline"
const ColorIcon = "carbon:circle-solid"

const themeStore = useThemeStore()
const { width: winWidth } = useWindowSize()
const isMobileView = computed<boolean>(() => winWidth.value < 700)
const open = ref(false)
const transitionOptions = [
	{
		label: "Fade",
		value: "fade"
	},
	{
		label: "FadeUp",
		value: "fade-up"
	},
	{
		label: "FadeBottom",
		value: "fade-bottom"
	},
	{
		label: "FadeLeft",
		value: "fade-left"
	},
	{
		label: "FadeRight",
		value: "fade-right"
	}
]

const layout = computed({
	get: () => themeStore.layout,
	set: val => themeStore.setLayout(val)
})

const routerTransition = computed({
	get: () => themeStore.routerTransition,
	set: val => themeStore.setRouterTransition(val)
})

const theme = computed({
	get: () => themeStore.themeName,
	set: val => themeStore.setTheme(val)
})

const darkColor = computed({
	get: () => themeStore.darkPrimaryColor,
	set: val => themeStore.setColor(ThemeEnum.Dark, "primary", val)
})

const lightColor = computed({
	get: () => themeStore.lightPrimaryColor,
	set: val => themeStore.setColor(ThemeEnum.Light, "primary", val)
})

const rtl = computed({
	get: () => themeStore.isRTL,
	set: val => themeStore.setRTL(val)
})

const boxed = computed({
	get: () => themeStore.isBoxed,
	set: val => themeStore.setBoxed(val)
})

const toolbarBoxed = computed({
	get: () => themeStore.isToolbarBoxed,
	set: val => themeStore.setToolbarBoxed(val)
})

const footerShown = computed({
	get: () => themeStore.isFooterShown,
	set: val => themeStore.setFooterShow(val)
})

const palette = ref<Palette>([
	{ light: "#00B27B", dark: "#00E19B" },
	{ light: "#6267FF", dark: "#6267FF" },
	{ light: "#FF61C9", dark: "#FF61C9" },
	{ light: "#FFB600", dark: "#FFB600" },
	{ light: "#FF0156", dark: "#FF0156" }
])

function setPrimary(color: ColorPalette) {
	themeStore.setColor(ThemeEnum.Dark, "primary", color.dark)
	themeStore.setColor(ThemeEnum.Light, "primary", color.light)
}

function reset() {
	themeStore.setColor(ThemeEnum.Dark, "primary", "#00E19B")
	themeStore.setColor(ThemeEnum.Light, "primary", "#00B27B")
	themeStore.setTheme(useOsTheme().value || ThemeEnum.Light)
	themeStore.setLayout(Layout.HorizontalNav)
	themeStore.setRouterTransition(RouterTransition.FadeUp)
	themeStore.setRTL(false)
	themeStore.setBoxed(true)
	themeStore.setToolbarBoxed(true)
	themeStore.setFooterShow(true)
}
</script>

<style scoped lang="scss">
.layout-settings {
	position: fixed;
	right: 10px;
	top: 50%;
	width: 50px;
	height: 50px;
	border-radius: 50px;
	background-color: var(--primary-color);
	color: var(--bg-color);
	transform: translateY(-50%);
	transition: all 0.3s;
	overflow: hidden;
	border: 1px solid transparent;

	.open-btn {
		cursor: pointer;
		width: 100%;
		height: 100%;
		position: absolute;
		will-change: opacity;
	}
	.ls-form {
		position: absolute;
		height: 100%;
		width: 100%;
		will-change: opacity;

		.ls-header {
			border-bottom: var(--border-small-050);
			font-size: 14px;
			text-transform: uppercase;
			font-weight: 700;
			padding: 10px 14px;
			line-height: 1;
			transition: all 0.3s;

			.ls-icon {
				cursor: pointer;
				opacity: 0.6;

				&:hover {
					opacity: 1;
					color: var(--primary-color);
				}
			}
		}

		.ls-main {
			.ls-section {
				padding: 14px;
				font-size: 12px;
				display: flex;
				flex-direction: column;

				&:not(:last-child) {
					border-bottom: var(--border-small-050);
				}

				.ls-label {
					font-size: 12px;
					margin-bottom: 8px;
					font-weight: 600;
					color: var(--fg-secondary-color);
				}

				&.ls-color-selection {
					.color-picker-box {
						line-height: 0;
						.n-color-picker {
							height: 28px;
							:deep() {
								.n-color-picker-trigger {
									.n-color-picker-trigger__fill {
										left: 5px;
										right: 5px;
										top: 5px;
										bottom: 5px;
										justify-content: flex-start;
										line-height: 0;

										.n-color-picker-checkboard {
											background: transparent;
											&::after {
												background-image: none;
											}

											& ~ div {
												width: 32px;
												border-radius: var(--border-radius-small);
												height: 100%;
											}
										}
										.n-color-picker-trigger__value {
											color: var(--fg-color) !important;
											margin-left: 44px;
											font-size: 12px;
											font-weight: 600;
											width: initial !important;
											height: initial !important;
										}
									}
								}
							}
						}
					}
				}

				&.ls-boxed-selection {
					.switch-label {
						font-size: 12px;
						font-weight: 600;
						color: var(--fg-secondary-color);
					}
				}

				&.ls-reset-selection {
					a {
						color: var(--fg-secondary-color);
						text-decoration-color: var(--fg-secondary-color);
					}
				}
			}
		}
	}

	&.open {
		width: 230px;
		height: 645px;
		right: 16px;
		border-radius: var(--border-radius);
		max-height: 90vh;
		max-height: 90svh;
		background-color: var(--bg-color);
		color: var(--fg-color);
		border-color: var(--border-color);
	}

	.anim-enter-active,
	.anim-leave-active {
		transition:
			opacity 0.1s var(--bezier-ease),
			transform 0.2s var(--bezier-ease);
	}

	.anim-enter-from,
	.anim-leave-to {
		opacity: 0;
		// transform: translateY(1%);
	}
}

.direction-rtl {
	.layout-settings {
		right: unset;
		left: 10px;

		.ls-form {
			.ls-header {
				direction: rtl;
			}

			:deep() {
				.n-color-picker {
					.n-color-picker-trigger {
						.n-color-picker-trigger__fill {
							.n-color-picker-trigger__value {
								margin-left: unset !important;
								margin-right: 44px;
							}
						}
					}
				}
			}
		}

		&.open {
			right: unset;
			left: 16px;
		}
	}
}
</style>
