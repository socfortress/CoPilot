<template>
    <div class="page-flag-icons flex column">
        <div class="page-header">
            <h1>Flag icons</h1>
            <h4>
                <a href="https://github.com/lipis/flag-icon-css" target="_blank"
                    ><i class="mdi mdi-book-open-page-variant"></i> see from the complete documentation</a
                >
            </h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Icons</el-breadcrumb-item>
                <el-breadcrumb-item>Flag icons</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="card-base card-shadow--small icons-list scrollable only-y p-10">
            <div class="icon" v-for="i in icons" :key="i">
                <i class="flag-icon" :class="{ ['flag-icon-' + i]: true }"></i>
                <div>flag-icon-{{ i }}</div>
            </div>
        </div>
    </div>
</template>

<script>
import "flag-icon-css/css/flag-icons.min.css"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "FlagIcons",
    data() {
        return {
            icons: [
                "ad",
                "ae",
                "af",
                "ag",
                "ai",
                "al",
                "am",
                "ao",
                "aq",
                "ar",
                "as",
                "at",
                "au",
                "aw",
                "ax",
                "az",
                "ba",
                "bb",
                "bd",
                "be",
                "bf",
                "bg",
                "bh",
                "bi",
                "bj",
                "bl",
                "bm",
                "bn",
                "bo",
                "bq",
                "br",
                "bs",
                "bt",
                "bv",
                "bw",
                "by",
                "bz",
                "ca",
                "cc",
                "cd",
                "cf",
                "cg",
                "ch",
                "ci",
                "ck",
                "cl",
                "cm",
                "cn",
                "co",
                "cr",
                "cu",
                "cv",
                "cw",
                "cx",
                "cy",
                "cz",
                "de",
                "dj",
                "dk",
                "dm",
                "do",
                "dz",
                "ec",
                "ee",
                "eg",
                "eh",
                "er",
                "es",
                "et",
                "fi",
                "fj",
                "fk",
                "fm",
                "fo",
                "fr",
                "ga",
                "gb",
                "gd",
                "ge",
                "gf",
                "gg",
                "gh",
                "gi",
                "gl",
                "gm",
                "gn",
                "gp",
                "gq",
                "gr",
                "gs",
                "gt",
                "gu",
                "gw",
                "gy",
                "hk",
                "hm",
                "hn",
                "hr",
                "ht",
                "hu",
                "id",
                "ie",
                "il",
                "im",
                "in",
                "io",
                "iq",
                "ir",
                "is",
                "it",
                "je",
                "jm",
                "jo",
                "jp",
                "ke",
                "kg",
                "kh",
                "ki",
                "km",
                "kn",
                "kp",
                "kr",
                "kw",
                "ky",
                "kz",
                "la",
                "lb",
                "lc",
                "li",
                "lk",
                "lr",
                "ls",
                "lt",
                "lu",
                "lv",
                "ly",
                "ma",
                "mc",
                "md",
                "me",
                "mf",
                "mg",
                "mh",
                "mk",
                "ml",
                "mm",
                "mn",
                "mo",
                "mp",
                "mq",
                "mr",
                "ms",
                "mt",
                "mu",
                "mv",
                "mw",
                "mx",
                "my",
                "mz",
                "na",
                "nc",
                "ne",
                "nf",
                "ng",
                "ni",
                "nl",
                "no",
                "np",
                "nr",
                "nu",
                "nz",
                "om",
                "pa",
                "pe",
                "pf",
                "pg",
                "ph",
                "pk",
                "pl",
                "pm",
                "pn",
                "pr",
                "ps",
                "pt",
                "pw",
                "py",
                "qa",
                "re",
                "ro",
                "rs",
                "ru",
                "rw",
                "sa",
                "sb",
                "sc",
                "sd",
                "se",
                "sg",
                "sh",
                "si",
                "sj",
                "sk",
                "sl",
                "sm",
                "sn",
                "so",
                "sr",
                "ss",
                "st",
                "sv",
                "sx",
                "sy",
                "sz",
                "tc",
                "td",
                "tf",
                "tg",
                "th",
                "tj",
                "tk",
                "tl",
                "tm",
                "tn",
                "to",
                "tr",
                "tt",
                "tv",
                "tw",
                "tz",
                "ua",
                "ug",
                "um",
                "us",
                "uy",
                "uz",
                "va",
                "vc",
                "ve",
                "vg",
                "vi",
                "vn",
                "vu",
                "wf",
                "ws",
                "ye",
                "yt",
                "za",
                "zm",
                "zw"
            ]
        }
    }
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";

.page-flag-icons {
    .icons-list {
        .icon {
            width: 120px;
            height: 90px;
            margin: 10px;
            display: inline-block;
            text-align: center;
            padding: 10px;
            box-sizing: border-box;

            i {
                width: 50px;
                height: 50px;
            }
        }
    }
}

@media (max-width: 768px) {
    .page-flag-icons {
        overflow-x: hidden !important;
        overflow-y: auto !important;
        flex: none !important;
        display: block !important;
        width: 100%;

        .icons-list {
            .icon {
                width: 110px;
                height: 80px;
                margin: 6px;
                padding: 6px;
            }
        }
    }
}
</style>
