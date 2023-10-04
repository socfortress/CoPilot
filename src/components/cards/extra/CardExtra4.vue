<template>
	<n-card hoverable class="p-7">
		<n-empty description="You can't find anything">
			<template #extra>
				<n-button size="small">Find Something New</n-button>
			</template>
		</n-empty>
	</n-card>
</template>

<script setup lang="ts">
import { NCard, NEmpty, NButton } from "naive-ui"
</script>
