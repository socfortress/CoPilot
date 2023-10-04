<template>
	<n-card>
		<template #cover>
			<n-skeleton :sharp="true" :height="200" />
		</template>
		<template #header>
			<n-skeleton text width="60%" />
		</template>
		<n-skeleton text width="20%" />
		<n-skeleton text :repeat="6" />
	</n-card>
</template>

<script setup lang="ts">
import { NCard, NSkeleton } from "naive-ui"
</script>
