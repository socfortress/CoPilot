<template>
	<div class="page page-wrapped flex items-center justify-center">
		<n-result status="404" :title="$t('navigation.notFound.title')" size="huge">
			<div class="flex justify-center">
				<n-button @click="redirect()">{{ $t("navigation.notFound.home") }}</n-button>
			</div>
		</n-result>
	</div>
</template>

<script lang="ts" setup>
import { NButton, NResult } from "naive-ui"
import { useRouter } from "vue-router"

const router = useRouter()

function redirect() {
	router.push({ path: "/" })
}
</script>
