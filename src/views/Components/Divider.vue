<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Divider</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/divider"
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
				Oops
				<n-divider />
				Oops
				<template #code="{ html }">
					{{ html(`
					<div>
						Oops
						<n-divider />
						Oops
					</div>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Title">
				Oops
				<n-divider title-placement="left">Left</n-divider>
				Oops
				<n-divider title-placement="right">Right</n-divider>
				Oops
				<n-divider dashed>Dashed</n-divider>
				Oops
				<template #code="{ html }">
					{{ html(`
					<div>
						Oops
						<n-divider title-placement="left">Left</n-divider>
						Oops
						<n-divider title-placement="right">Right</n-divider>
						Oops
						<n-divider dashed>Dashed</n-divider>
						Oops
					</div>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Vertical">
				It is
				<n-divider vertical />
				not clear
				<n-divider vertical />
				to see, emmm...
				<template #code="{ html }">
					{{ html(` It is
					<n-divider vertical />
					not clear
					<n-divider vertical />
					to see, emmm... `) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NDivider } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
