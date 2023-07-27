<template>
    <el-scrollbar class="login-page">
        <div class="align-vertical">
            <div class="form-wrapper align-vertical-middle">
                <div class="form-box card-base card-shadow--extraLarge">
                    <img class="image-logo" src="@/assets/images/logo.svg" alt="logo" />

                    <div class="field-box">
                        <input type="username" name="username" placeholder="Username" />
                    </div>
                    <div class="field-box">
                        <input type="password" name="password" placeholder="Password" />
                    </div>

                    <div class="flex align-center">
                        <div class="box grow"><el-checkbox>Remember Me </el-checkbox></div>
                        <div class="box grow text-right">
                            <router-link to="/dashboard">Forgot Password?</router-link>
                        </div>
                    </div>

                    <div class="flex text-center center pt-30 pb-10">
                        <button @click="login" class="login-btn">LOGIN</button>
                    </div>

                    <div class="text-divider mv-10">or</div>

                    <div class="flex column center pt-10 pb-10">
                        <button @click="login" class="social-btn google">Log in with Google</button>
                        <button @click="login" class="social-btn facebook">Log in with Facebook</button>
                    </div>

                    <div class="text-center signin-box pt-20">Don't have an account? <a>Sign in</a></div>
                </div>
            </div>
        </div>
    </el-scrollbar>
</template>

<script>
import { defineComponent } from "@vue/runtime-core"
import { useMainStore } from "../../../stores/main"

export default defineComponent({
    name: "Login",
    data() {
        return {
            form: {
                email: "",
                password: ""
            }
        }
    },
    methods: {
        login() {
            useMainStore().setLogin()
            this.$router.push("dashboard")
        }
    }
})
</script>

<style lang="scss">
@import "@/assets/scss/_variables";

.login-page {
    background: $text-color-primary;
    margin-left: -30px;
    margin-right: -30px;

    .form-wrapper {
        width: 100%;
    }

    .form-box {
        width: 100%;
        max-width: 340px;
        padding: 30px;
        box-sizing: border-box;
        margin: 20px auto;

        a {
            font-size: 14px;
            color: $text-color-accent;
            text-decoration: none;
            font-weight: 500;
        }

        .image-logo {
            width: 80px;
            margin: 0px auto;
            margin-bottom: 30px;
            display: block;
        }

        .field-box {
            margin-bottom: 10px;
            input {
                width: 100%;
                box-sizing: border-box;
                border-radius: 10px;
                padding: 10px 20px;
                outline: none;
                border: 1px solid $text-color-primary;
            }
        }

        .login-btn {
            margin-top: 20px;
            width: 100%;
            background-color: $text-color-primary;
            color: #fff;
            font-weight: bold;
            border-radius: 10px;
            padding: 10px 20px;
            outline: none;
            border: none;
        }

        .social-btn {
            width: 160px;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;

            &.google {
                margin-bottom: 10px;
                background-color: #d73d32;
                color: white;

                &:hover {
                    border-color: #d73d32;
                }
            }
            &.facebook {
                background-color: #3f5c9a;
                color: white;

                &:hover {
                    border-color: #3f5c9a;
                }
            }
        }

        .signin-box {
            font-size: 14px;
        }
    }
}

@media (max-width: 768px) {
    .layout-container .container .view.login-page {
        margin-left: -5px;
        margin-right: -5px;
        max-width: calc(100% + 10px);
    }
}
</style>
