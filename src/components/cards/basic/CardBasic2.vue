<template>
	<n-card>
		<template #cover>
			<img :src="image" width="900" height="400" />
		</template>
		<template #default>
			<n-avatar round :src="avatar" :size="50" class="avatar" />
			<div class="title">
				{{ title }}
			</div>
			<p class="text">
				{{ text }}
			</p>
		</template>
		<template #action>
			<div class="flex items-center justify-between">
				<n-button type="primary">Message</n-button>
				<n-avatar-group :options="options" :size="40" :max="4" />
			</div>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NAvatarGroup, NAvatar, NButton } from "naive-ui"

const image = faker.image.urlPicsumPhotos({ width: 900, height: 400 })
const avatar = faker.image.avatarGitHub()
const title = faker.lorem.sentence({ min: 2, max: 5 })
const text = faker.lorem.paragraph()

const options = faker.helpers.uniqueArray(faker.word.sample, 5).map(() => ({
	name: faker.person.fullName(),
	src: faker.image.avatarGitHub()
}))
</script>

<style lang="scss" scoped>
.n-card {
	.avatar {
		margin-top: -25px;
	}

	.title {
		font-size: var(--n-title-font-size);
		padding: var(--n-padding-top) 0 var(--n-padding-bottom) 0;
		font-weight: 700;
		font-family: var(--font-family-display);
		transition: color 0.3s var(--n-bezier);
		flex: 1;
		min-width: 0;
		color: var(--n-title-text-color);
	}
}
</style>
