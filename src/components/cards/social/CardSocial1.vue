<template>
	<n-card hoverable>
		<div class="post-box">
			<div class="user flex items-start">
				<div class="avatar">
					<n-avatar round :src="avatar" :size="40" lazy />
				</div>
				<div class="info">
					<div class="name">
						{{ name }}
					</div>
					<div class="date">
						<n-time :time="date" format="d MMM @ HH:mm" />
					</div>
				</div>
			</div>

			<div class="content flex flex-col gap-4">
				<div class="image" v-if="image">
					<n-image :src="image" width="500" height="300" lazy />
				</div>
				<p class="text" v-if="text">
					{{ text }}
				</p>
			</div>

			<div class="reactions flex items-center gap-7">
				<n-button
					text
					class="item comments"
					:class="{ active: commentActive }"
					@click="commentActive = !commentActive"
				>
					<Icon :size="18" v-if="commentActive" :name="CommentsActiveIcon"></Icon>
					<Icon :size="18" v-else :name="CommentsIcon"></Icon>
					<span class="count">{{ commentsCount }}</span>
				</n-button>
				<n-button text class="item likes" :class="{ active: likeActive }" @click="likeActive = !likeActive">
					<Icon :size="18" v-if="likeActive" :name="HeartActiveIcon"></Icon>
					<Icon :size="18" v-else :name="HeartIcon"></Icon>
					<span class="count">{{ likesCount }}</span>
				</n-button>
			</div>
		</div>

		<div class="comments-box" v-if="commentActive">
			<div class="comment flex" v-for="comment of comments" :key="comment.id">
				<div class="avatar">
					<n-avatar round :src="comment.avatar" :size="40" lazy />
				</div>
				<div class="content">
					<div class="info flex flex-wrap">
						<div class="name">{{ comment.name }}</div>
						<div class="date">
							<n-time :time="comment.date" format="d MMM @ HH:mm" />
						</div>
					</div>
					<p class="text" v-html="comment.text"></p>
				</div>
			</div>
		</div>

		<div class="reply-box flex">
			<div class="text-input grow">
				<n-input
					placeholder="Reply..."
					type="textarea"
					size="small"
					v-model:value="reply"
					@blur="resetWindowScroll()"
					:autosize="{
						minRows: 1,
						maxRows: 5
					}"
				/>
			</div>
			<div class="actions-group flex items-center">
				<n-button text type="primary" :disabled="!reply" @click="send()">
					<Icon :size="20" :name="SendIcon"></Icon>
				</n-button>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NAvatar, NInput, NButton, NTime, NImage } from "naive-ui"
import { toRefs, ref } from "vue"
import dayjs from "@/utils/dayjs"
import Icon from "@/components/common/Icon.vue"

const SendIcon = "carbon:send"
const HeartIcon = "ion:heart-outline"
const HeartActiveIcon = "ion:heart"
const CommentsIcon = "ion:chatbubbles-outline"
const CommentsActiveIcon = "ion:chatbubbles"

export interface CardSocial {
	showImage?: boolean
	hideText?: boolean
	showComments?: boolean
	like?: boolean
}

const props = defineProps<CardSocial>()
const { showImage, hideText, showComments, like } = toRefs(props)

const commentActive = ref(showComments?.value ?? false)
const likeActive = ref(like?.value ?? false)

const avatar = faker.image.avatarGitHub()
const name = faker.person.fullName()
const date = faker.date.between({ from: dayjs().subtract(10, "d").toDate(), to: dayjs().subtract(5, "d").toDate() })
const image = showImage?.value ? faker.image.urlPicsumPhotos({ width: 500, height: 300 }) : null
const text = hideText.value ? "" : faker.lorem.paragraph()

const reply = ref("")

const likesCount = faker.number.int({ min: 10, max: 50 })
const commentsCount = faker.number.int({ min: 1, max: 3 })

let lastDate = date
const comments = ref(
	new Array(commentsCount).fill(undefined).map(() => {
		const newDate = faker.date.between({ from: dayjs(lastDate).toDate(), to: dayjs().toDate() })
		lastDate = newDate
		return {
			id: faker.string.nanoid(),
			avatar: faker.image.avatarGitHub(),
			name: faker.person.fullName(),
			date: newDate,
			text: faker.lorem.paragraph()
		}
	})
)

function resetWindowScroll() {
	window.scrollTo(0, 0)
}

function send() {
	comments.value.push({
		id: faker.string.nanoid(),
		avatar: "/images/avatar-64.jpg",
		name: "Margie Dibbert",
		date: dayjs().toDate(),
		text: reply.value.replace(/\n/gim, "<br/>")
	})
	reply.value = ""
}
</script>

<style lang="scss" scoped>
.n-card {
	.post-box {
		.user {
			margin-bottom: 18px;
			.avatar {
				margin-right: 12px;
			}
			.info {
				.name {
					font-size: 16px;
					font-weight: 700;
				}
				.date {
					opacity: 0.5;
					font-size: 14px;
				}
			}
		}

		.content {
			margin-bottom: 18px;
			.image {
				width: 100%;
				.n-image {
					width: 100%;
				}
				:deep() {
					img {
						border-radius: var(--border-radius-small);
						width: 100%;
					}
				}
			}
		}

		.reactions {
			.item {
				display: flex;
				align-items: center;

				.count {
					font-size: 16px;
					margin-left: 8px;
					margin-top: 2px;
				}

				&.active {
					&.comments {
						.n-icon {
							color: var(--primary-color);
						}
					}
					&.likes {
						.n-icon {
							color: var(--secondary4-color);
						}
					}
				}
			}
		}
	}

	.comments-box {
		.comment {
			margin-top: 20px;
			.avatar {
				margin-right: 12px;
			}
			.content {
				.info {
					margin-bottom: 6px;
					.name {
						font-size: 16px;
						font-weight: 700;
						margin-right: 16px;
					}
					.date {
						opacity: 0.5;
						font-size: 14px;
					}
				}
			}
		}
	}

	.reply-box {
		border-block-start: var(--border-small-050);
		padding-top: var(--n-padding-bottom);
		gap: 20px;
		margin-top: var(--n-padding-bottom);

		.text-input {
			.n-input--textarea {
				background-color: transparent;

				:deep() {
					.n-input__border,
					.n-input__state-border {
						display: none;
					}
				}
			}
		}

		.actions-group {
			gap: 20px;
		}
	}
}
</style>
