<template>
	<n-card>
		<template #header>
			<div class="flex items-center">
				<n-avatar round :src="avatar" :size="30" class="mr-3" />
				<span>
					{{ name }}
				</span>
			</div>
		</template>
		<template #default>
			<n-rate readonly :allow-half="true" :default-value="4.5" color="#FFB600" />
			<p v-html="text" class="mt-2"></p>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NRate, NAvatar } from "naive-ui"

const avatar = faker.image.avatarGitHub()
const name = faker.person.fullName()
const text = faker.lorem.sentences(3, "<br/><br/>") + faker.lorem.paragraph()
</script>
