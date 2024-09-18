<template>
	<div class="page grow flex flex-col justify-center items-center">
		<LicenseCheckoutResponse class="max-w-96" type="success" :data="{ email: route.query.email?.toString() }" />
	</div>
</template>

<script setup lang="ts">
import LicenseCheckoutResponse from "@/components/license/LicenseCheckoutResponse.vue"
import { useRoute } from "vue-router"

const route = useRoute()
</script>
