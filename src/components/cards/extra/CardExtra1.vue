<template>
	<n-card hoverable content-style="padding: 0;">
		<n-tabs type="line" :tabs-padding="24" pane-style="padding: 20px;" animated>
			<n-tab-pane name="Tab One"><p v-html="text1"></p></n-tab-pane>
			<n-tab-pane name="Tab Two"><p v-html="text2"></p></n-tab-pane>
			<n-tab-pane name="Tab Three"><p v-html="text3"></p></n-tab-pane>
		</n-tabs>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NTabs, NTabPane } from "naive-ui"

const text1 = faker.lorem.sentences(5, "<br/><br/>")
const text2 = faker.lorem.sentences(5, "<br/><br/>")
const text3 = faker.lorem.sentences(5, "<br/><br/>")
</script>
