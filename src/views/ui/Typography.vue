<template>
    <el-scrollbar class="page-typography">
        <div class="page-header">
            <h1>Typography</h1>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>UI</el-breadcrumb-item>
                <el-breadcrumb-item>Typography</el-breadcrumb-item>
            </el-breadcrumb>
        </div>
        <div class="card-base card-shadow--medium p-30">
            <el-tabs>
                <el-tab-pane label="Headers">
                    <div class="flex center demo-box">
                        <div class="left-box">big header 1</div>
                        <div class="right-box box grow"><h1 class="h-big">Lorem ipsum dolor sit amet</h1></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">big header 2</div>
                        <div class="right-box box grow"><h2 class="h-big">Lorem ipsum dolor sit amet</h2></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">big header 3</div>
                        <div class="right-box box grow"><h3 class="h-big">Lorem ipsum dolor sit amet</h3></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">header 1</div>
                        <div class="right-box box grow"><h1>Lorem ipsum dolor sit amet</h1></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">header 2</div>
                        <div class="right-box box grow"><h2>Lorem ipsum dolor sit amet</h2></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">header 3</div>
                        <div class="right-box box grow"><h3>Lorem ipsum dolor sit amet</h3></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">subheader 4</div>
                        <div class="right-box box grow"><h4>Lorem ipsum dolor sit amet</h4></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">subheader 5</div>
                        <div class="right-box box grow"><h5>Lorem ipsum dolor sit amet</h5></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">subheader 6</div>
                        <div class="right-box box grow"><h6>Lorem ipsum dolor sit amet</h6></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">paragraph</div>
                        <div class="right-box box grow">
                            <p>
                                Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet
                                dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam.
                            </p>
                        </div>
                    </div>
                </el-tab-pane>
                <el-tab-pane label="Text elements">
                    <div class="flex center demo-box mt-20">
                        <div class="left-box">blockquote</div>
                        <div class="right-box box grow">
                            <blockquote>
                                <p>
                                    Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut
                                    laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam.
                                </p>
                                <small class="secondary-text"> Lorem ipsum, Lorem ipsum </small>
                            </blockquote>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">blockquote reverse</div>
                        <div class="right-box box grow">
                            <blockquote class="reverse">
                                <p>
                                    Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut
                                    laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam.
                                </p>
                                <small class="secondary-text"> Lorem ipsum, Lorem ipsum </small>
                            </blockquote>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">code</div>
                        <div class="right-box box grow"><pre>import Vue from 'vue'</pre></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">definition lists</div>
                        <div class="right-box box grow">
                            <dl>
                                <dt>Definition term</dt>
                                <dd>This is the definition description</dd>

                                <dt>Another definition term</dt>
                                <dd>This is another definition description</dd>
                            </dl>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">definition lists horizontal</div>
                        <div class="right-box box grow">
                            <dl class="horizontal">
                                <dt>Definition term</dt>
                                <dd>This is the definition description</dd>

                                <dt>Another definition term</dt>
                                <dd>This is another definition description</dd>
                            </dl>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">unordered list</div>
                        <div class="right-box box grow">
                            <ul>
                                <li>List Item</li>
                                <li>
                                    List Item
                                    <ul>
                                        <li>List Item</li>
                                        <li>List Item</li>
                                        <li>List Item</li>
                                    </ul>
                                </li>
                                <li>List Item</li>
                            </ul>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">ordered list</div>
                        <div class="right-box box grow">
                            <ol>
                                <li>List Item</li>
                                <li>
                                    List Item
                                    <ol>
                                        <li>List Item</li>
                                        <li>List Item</li>
                                        <li>List Item</li>
                                    </ol>
                                </li>
                                <li>List Item</li>
                            </ol>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">unstyled list</div>
                        <div class="right-box box grow">
                            <ul class="list-unstyled">
                                <li>List Item</li>
                                <li>List Item</li>
                                <li>List Item</li>
                            </ul>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">anchor</div>
                        <div class="right-box box grow">a <a>link</a></div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">abbreviation</div>
                        <div class="right-box box grow">
                            <abbr title="HyperText Markup Language">HTML</abbr>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">highlight</div>
                        <div class="right-box box grow">a <mark>highlighted</mark> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">strike-through</div>
                        <div class="right-box box grow">a <s>strike-through</s> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">underline</div>
                        <div class="right-box box grow">an <u>underlined</u> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">selected</div>
                        <div class="right-box box grow">a <span class="text-selected">selected</span> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">small</div>
                        <div class="right-box box grow">a <small>small</small> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">strong</div>
                        <div class="right-box box grow">a <strong>strong</strong> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">italic</div>
                        <div class="right-box box grow">an <em>italic</em> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">super</div>
                        <div class="right-box box grow">a <sup>super</sup> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">sub</div>
                        <div class="right-box box grow">a <sub>sub</sub> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">capitalized</div>
                        <div class="right-box box grow">a <span class="text-capitalized">capitalized</span> text</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">lowercase</div>
                        <div class="right-box box grow">A <span class="text-lowercase">lowercase</span> TEXT</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">uppercase</div>
                        <div class="right-box box grow">an <span class="text-uppercase">uppercase</span> text</div>
                    </div>
                </el-tab-pane>
                <el-tab-pane label="Helpers" class="pt-20">
                    <div class="text-divider" style="margin-top: 0">LIST</div>
                    <div class="flex center demo-box">
                        <div class="left-box">unordered styled list</div>
                        <div class="right-box box grow">
                            <ul class="styled">
                                <li>List Item</li>
                                <li>
                                    List Item
                                    <ul>
                                        <li>List Item</li>
                                        <li>List Item</li>
                                        <li>List Item</li>
                                    </ul>
                                </li>
                                <li>List Item</li>
                            </ul>
                        </div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">ordered styled list</div>
                        <div class="right-box box grow">
                            <ol class="styled">
                                <li>List Item</li>
                                <li>
                                    List Item
                                    <ol>
                                        <li>List Item</li>
                                        <li>List Item</li>
                                        <li>List Item</li>
                                    </ol>
                                </li>
                                <li>List Item</li>
                            </ol>
                        </div>
                    </div>
                    <div class="text-divider">COLORS</div>
                    <br />
                    <div class="flex center demo-box" v-for="i in textColors" :key="i">
                        <div class="left-box">{{ i }}</div>
                        <div class="right-box box grow">
                            <span :class="i">Lorem Ipsum is simply dummy text of the printing and typesetting industry</span>
                        </div>
                    </div>
                    <br />
                    <div class="text-divider">FONT WEIGHT</div>
                    <br />
                    <div class="flex center demo-box" v-for="i in fontWeight" :key="i">
                        <div class="left-box">{{ i }}</div>
                        <div class="right-box box grow">
                            <span :class="i">Lorem Ipsum is simply dummy text of the printing and typesetting industry</span>
                        </div>
                    </div>
                    <br />
                    <div class="text-divider">
                        FONT SIZE ( from <strong class="mh-7">1px</strong> to <strong class="mh-7">200px</strong> )
                    </div>
                    <br />
                    <div class="flex center demo-box" v-for="(i, index) in fontSize" :key="i">
                        <div class="left-box">font-size-{{ 10 + index }}</div>
                        <div class="right-box box grow">
                            <span :class="'font-size-' + (10 + index)"
                                >Lorem Ipsum is simply dummy text of the printing and typesetting industry</span
                            >
                        </div>
                    </div>
                    <br />
                    <div class="text-divider">
                        LINE HEIGHT ( from <strong class="mh-7">1px</strong> to <strong class="mh-7">200px</strong> )
                    </div>
                    <br />
                    <div class="flex center demo-box" v-for="(i, index) in lineHeight" :key="i">
                        <div class="left-box">line-height-{{ 30 + index }}</div>
                        <div class="right-box box grow">
                            <span :class="'line-height-' + (30 + index)"
                                >Lorem Ipsum is simply dummy text of the printing and typesetting industry</span
                            >
                        </div>
                    </div>
                    <div class="text-divider">TEXT ALIGN</div>
                    <br />
                    <div class="flex center demo-box">
                        <div class="left-box">text-left</div>
                        <div class="right-box box grow text-left">text align left</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">text-center</div>
                        <div class="right-box box grow text-center">text align center</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">text-right</div>
                        <div class="right-box box grow text-right">text align right</div>
                    </div>
                    <div class="flex center demo-box">
                        <div class="left-box">text-truncate</div>
                        <div class="right-box box grow text-truncate">
                            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus laoreet mi vel semper venenatis. Integer eget
                            convallis libero, sit amet tristique est. Sed lacinia massa eget erat facilisis, et pulvinar arcu pharetra.
                            Morbi gravida metus et turpis efficitur bibendum. Praesent tortor leo, finibus et finibus in, malesuada vel
                            massa. Aliquam erat volutpat. Etiam efficitur lectus sit amet odio tempus, quis tempor enim molestie.
                        </div>
                    </div>
                </el-tab-pane>
            </el-tabs>
        </div>
    </el-scrollbar>
</template>

<script>
import { defineComponent } from "vue"

export default defineComponent({
    name: "Typography",
    data() {
        return {
            textColors: [
                "primary-text",
                "secondary-text",
                "hint-text",
                "accent-text",
                "black-text",
                "success-text",
                "warning-text",
                "danger-text",
                "info-text",
                "success-light-text",
                "warning-light-text",
                "danger-light-text",
                "info-light-text"
            ],
            fontWeight: [
                "font-weight-100",
                "font-weight-200",
                "font-weight-300",
                "font-weight-400",
                "font-weight-500",
                "font-weight-600",
                "font-weight-700",
                "font-weight-800",
                "font-weight-900"
            ],
            fontSize: Array(11),
            lineHeight: Array(11)
        }
    }
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

.card-base {
    .text-divider {
        margin-top: 80px;
        margin-bottom: 5px;
    }

    .demo-box {
        margin-bottom: 40px;

        .left-box {
            width: 200px;
            padding: 20px 40px;
            box-sizing: border-box;
            text-align: right;
            color: transparentize($text-color-primary, 0.5);
        }
    }
}

@media (max-width: 768px) {
    .card-base {
        .demo-box {
            display: block;
            overflow: hidden;

            .left-box {
                text-align: left;
                padding: 30px 0;
                padding-bottom: 15px;
            }

            .left-box,
            .right-box {
                width: 100%;
                display: block;
            }
        }
    }
}
</style>
