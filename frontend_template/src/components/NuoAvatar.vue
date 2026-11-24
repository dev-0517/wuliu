<script setup>
defineProps({ compact: Boolean })
</script>
<template><span class="nuo-character" :class="{'is-compact':compact}" aria-hidden="true"><span class="nuo-halo" /><span class="nuo-body"><span class="nuo-eye left" /><span class="nuo-eye right" /><span class="nuo-smile" /><span class="nuo-cheek left" /><span class="nuo-cheek right" /></span><span class="nuo-star">✦</span><span class="nuo-spark">+</span></span></template>
