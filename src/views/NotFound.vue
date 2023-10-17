<template>
	<div class="page page-wrapped flex items-center justify-center">
		<n-result status="404" title="404 Not Found" size="huge">
			<div class="flex justify-center">
				<n-button @click="redirect()">Go to home</n-button>
			</div>
		</n-result>
	</div>
</template>

<script lang="ts" setup>
import { NResult, NButton } from "naive-ui"
import { useRouter } from "vue-router"

const router = useRouter()

function redirect() {
	router.push({ path: "/" })
}
</script>

<style lang="scss" scoped>
.page {
	font-size: 300px;
}
</style>
