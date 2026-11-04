<template>
	<div class="page">
		<TalonChatPage />
	</div>
</template>

<script setup lang="ts">
import TalonChatPage from "@/components/talonChat/TalonChatPage.vue"
import { useHideLayoutFooter } from "@/composables/common/useHideLayoutFooter"

// The inbox is the window's height: with the footer below it, the whole page would scroll.
useHideLayoutFooter()
</script>
