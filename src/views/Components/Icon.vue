<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Icon</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/icon"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic">
				<Icon :name="GameControllerOutline" :size="40" />
				<Icon :name="GameController" :size="40" color="#0e7a0d" />
				<Icon :name="GameController" :size="40" />
				<template #code="{ html, js }">
					{{ html(`
					<n-icon size="40">
						<game-controller-outline />
					</n-icon>
					<n-icon size="40" color="#0e7a0d">
						<game-controller />
					</n-icon>
					<n-icon size="40" :component="GameController" />
					`) }}
					{{
						js(`
						import { GameControllerOutline, GameController } from '@vicons/ionicons5'
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Icon with background">
				<template #description>Sometime it looks better with a background.</template>
				<Icon
					:name="Checkmark16Filled"
					:bgSize="24"
					:size="18"
					:border-radius="10"
					bgColor="#0e7a0d"
					color="#fff"
				/>

				<template #code="{ html, js }">
					{{ html(`
					<n-icon-wrapper :size="24" :border-radius="10">
						<n-icon :size="18" :component="Checkmark16Filled" />
					</n-icon-wrapper>
					`) }}

					{{ js(`import Checkmark16Filled from '@vicons/fluent/Checkmark16Filled'`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
const GameControllerOutline = "ion:game-controller-outline"
const GameController = "ion:game-controller"
const Checkmark16Filled = "fluent:checkmark-16-filled"
</script>
