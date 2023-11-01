<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Space</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/space"
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
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
					<n-button>Long! Long! Cross the line!</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space>
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
						<n-button>Long! Long! Cross the line!</n-button>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Vertical">
				<n-space vertical>
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space vertical>
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="From End">
				<n-space justify="end">
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space justify="end">
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Space Between">
				<n-space justify="space-between">
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space justify="space-between">
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Space Around">
				<n-space justify="space-around" size="large">
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space justify="space-around" size="large">
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="From Center">
				<n-space justify="center">
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
					<n-button>Oops!</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space justify="center">
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
						<n-button>Oops!</n-button>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
