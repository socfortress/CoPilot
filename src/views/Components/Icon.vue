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
					class="ml-4"
				>
					<n-icon :size="16">
						<ExternalIcon />
					</n-icon>
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic">
				<n-icon size="40">
					<game-controller-outline />
				</n-icon>
				<n-icon size="40" color="#0e7a0d">
					<game-controller />
				</n-icon>
				<n-icon size="40" :component="GameController" />
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
				<n-icon-wrapper :size="24" :border-radius="10">
					<n-icon :size="18" :component="Checkmark16Filled" />
				</n-icon-wrapper>
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
import { NIcon, NIconWrapper } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import { GameControllerOutline, GameController } from "@vicons/ionicons5"
import Checkmark16Filled from "@vicons/fluent/Checkmark16Filled"
</script>
