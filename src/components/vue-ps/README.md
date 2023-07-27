# `vue-ps`

[perfect-scrollbar](https://github.com/noraesae/perfect-scrollbar) vue version

## 1.install

```
npm install vue-ps
```

## 2. example

### 2.1 base example

```html
<template>
  <VuePs class="scroll-area" v-once :settings="settings" @ps-scroll-y="scrollHanle">
    <img src="./assets/azusa.jpg" height="720" width="1280" alt="azusa">
  </VuePs>
</template>

<script>
import VuePs from 'vue-ps'

export default {
  components: {
    VuePs
  },
  name: 'app',
  data() {
    return {
      settings: {
        maxScrollbarLength: 60
      }
    }
  },
  methods: {
    scrollHanle(evt) {
      console.log(evt)
    }
  }
}

</script>
<style lang="scss">
.scroll-area {
  position: relative;
  margin: auto;
  width: 400px;
  height: 300px;
}
</style>

```
Also,you can clone this repository to run the example:

```shell
git clone git@github.com:Linko91/vue-ps.git
cd vue-ps
npm install
npm run example
```
### 2.2 example with vuerouter
```shell
git clone git@github.com:Linko91/vue-ps.git
cd vue-ps
npm install
npm run example:vuerouter
```

## 3. props

### settings:please refer to [optional-parameters of perfect-scrollbar](https://github.com/noraesae/perfect-scrollbar#optional-parameters)
### swicher:which you could use to turn off the scrollbar for mobile or other case


## 4. events

please refer to [events of perfect-scrollbar](https://github.com/noraesae/perfect-scrollbar#events)

## 5. use vue and webpack
you can do it like this:

### install
```shell
npm install vue-ps perfect-scrollbar --save
```

### use
```js
import VuePs from 'vue-ps/index.vue'
export default {
  components: {
    VuePs
  },
  //...
}
```

## License

The MIT License (MIT) Copyright (c) 2016 Hyunje Alex Jun and other contributors.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
