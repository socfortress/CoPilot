<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Switch</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/switch"
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
				<n-space>
					<n-switch />
					<n-switch disabled />
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space>
						<n-switch />
						<n-switch disabled />
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Size">
				<n-space>
					<n-switch size="small" />
					<n-switch size="medium" />
					<n-switch size="large" />
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space>
						<n-switch size="small" />
						<n-switch size="medium" />
						<n-switch size="large" />
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Loading">
				<n-switch :rubber-band="false" loading />
				<template #code="{ html }">
					{{ html(`
					<n-switch :rubber-band="false" loading />
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Content">
				<n-switch>
					<template #checked>Big wheels keep on turnin'</template>
					<template #unchecked>Carry me home to see my kin</template>
				</n-switch>
				<template #code="{ html }">
					{{ html(`
					<n-switch>
						<template #checked>Big wheels keep on turnin'</template>
						<template #unchecked>Carry me home to see my kin</template>
					</n-switch>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Shape">
				<n-space>
					<n-switch :round="false" />
					<n-switch />
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space>
						<n-switch :round="false" />
						<n-switch />
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSwitch, NSpace } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
