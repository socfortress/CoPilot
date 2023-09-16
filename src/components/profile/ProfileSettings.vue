<template>
	<n-card class="settings">
		<n-form ref="refForm" :label-width="80" :model="formValue" :rules="formRules">
			<div class="title">General</div>
			<div class="flex justify-between flex-col md:flex-row md:gap-4">
				<n-form-item label="Username" path="username" class="basis-1/2">
					<n-input v-model:value="formValue.username" placeholder="Type username">
						<template #prefix>@</template>
					</n-input>
				</n-form-item>
				<n-form-item label="Email" path="email" class="basis-1/2">
					<n-input v-model:value="formValue.email" placeholder="Type email" />
				</n-form-item>
			</div>
			<div class="title">Profile</div>
			<n-form-item label="Fullname" path="name">
				<n-input v-model:value="formValue.name" placeholder="Type Fullname" />
			</n-form-item>
			<div class="flex justify-between flex-col md:flex-row md:gap-4">
				<n-form-item label="Location" path="location" class="basis-1/2">
					<n-input v-model:value="formValue.location" placeholder="Type location" />
				</n-form-item>
				<n-form-item label="Website" path="website" class="basis-1/2">
					<n-input v-model:value="formValue.website" placeholder="Type website" />
				</n-form-item>
			</div>
			<n-form-item label="Bio" path="bio">
				<n-input v-model:value="formValue.bio" type="textarea" placeholder="Type bio" />
			</n-form-item>
			<div class="title">Social</div>
			<div class="flex justify-between flex-col md:flex-row md:gap-4">
				<n-form-item label="Twitter" path="twitter" class="basis-1/3">
					<n-input v-model:value="formValue.twitter" placeholder="Type twitter" />
				</n-form-item>
				<n-form-item label="Facebook" path="facebook" class="basis-1/3">
					<n-input v-model:value="formValue.facebook" placeholder="Type facebook" />
				</n-form-item>
				<n-form-item label="Google" path="google" class="basis-1/3">
					<n-input v-model:value="formValue.google" placeholder="Type google" />
				</n-form-item>
			</div>
			<div class="flex justify-between flex-col md:flex-row md:gap-4">
				<n-form-item label="Instagram" path="instagram" class="basis-1/3">
					<n-input v-model:value="formValue.instagram" placeholder="Type instagram" />
				</n-form-item>
				<n-form-item label="Github" path="github" class="basis-1/3">
					<n-input v-model:value="formValue.github" placeholder="Type github" />
				</n-form-item>
				<n-form-item label="Threads" path="threads" class="basis-1/3">
					<n-input v-model:value="formValue.threads" placeholder="Type threads" />
				</n-form-item>
			</div>
			<n-form-item>
				<n-button type="primary">Save</n-button>
			</n-form-item>
		</n-form>
	</n-card>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { NCard, NForm, NFormItem, NInput, NButton } from "naive-ui"

const formValue = ref({
	username: "sigmund67",
	email: "sigmund67@gmail.com",
	name: "Margie Dibbert",
	location: "New York No. 1 Lake Park",
	bio: "",
	website: "",
	twitter: "",
	facebook: "",
	google: "",
	instagram: "",
	threads: "",
	github: ""
})

const refForm = ref()

const formRules = {
	username: {
		required: true,
		message: "Please input username",
		trigger: "blur"
	},
	email: {
		required: true,
		message: "Please input email",
		trigger: "blur"
	}
}
</script>

<style lang="scss" scoped>
.settings {
	.title {
		font-size: 20px;
		margin-bottom: 20px;

		&:not(:first-child) {
			margin-top: 20px;
		}
	}
}
</style>
