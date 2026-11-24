<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
const props = defineProps({ content: { type: String, default: '' } })
// 只渲染安全的 Markdown 结构：禁止原始 HTML、图片和链接。
// 既防止模型输出脚本，也避免自动加载外部图片。
const markdown = new MarkdownIt({ html: false, breaks: true }).disable(['image', 'link', 'autolink'])
const rendered = computed(() => markdown.render(props.content))
</script>
<template><div class="markdown-content" v-html="rendered" /></template>
