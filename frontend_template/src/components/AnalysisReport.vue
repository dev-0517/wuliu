<script setup>
import SourceList from './SourceList.vue'
defineProps({ analysis: { type: Object, required: true }, asking: Boolean })
defineEmits(['ask'])
function date(value) { return value ? new Date(value.endsWith('Z') ? value : value + 'Z').toLocaleString('zh-CN', { hour12: false }) : '' }
</script>

<template>
  <div class="analysis-result">
    <div class="analysis-meta"><span class="badge">AI 辅助分析 · 待核实</span><span class="muted small">{{ date(analysis.generated_at) }}</span></div>
    <h3>案情摘要</h3><p class="preserve">{{ analysis.summary }}</p>
    <template v-if="analysis.facts?.length">
      <h3>记录中的事实陈述</h3><p class="muted small">引用校验只确认摘录存在于记录中，不代表事实或证据已经核实。</p>
      <article v-for="(fact, i) in analysis.facts" :key="i" class="fact-item">
        <div><span class="badge">{{ fact.record_type }}</span><code>{{ fact.source_ref }}</code></div>
        <p>{{ fact.statement }}</p><blockquote>原文：{{ fact.quote }}</blockquote>
      </article>
    </template>
    <div class="analysis-columns">
      <div><h3>待厘清的争议</h3><ul><li v-for="(s,i) in analysis.issues" :key="i">{{ s }}</li></ul><p v-if="!analysis.issues?.length" class="muted">暂无明确记录</p></div>
      <div><h3>待补充信息</h3><ul><li v-for="(s,i) in analysis.missing_information" :key="i">{{ s }}</li></ul><p v-if="!analysis.missing_information?.length" class="muted">请继续核实原始案情</p></div>
    </div>
    <h3>案情时间线</h3>
    <div v-if="analysis.timeline?.length" class="timeline"><div v-for="(event,i) in analysis.timeline" :key="i"><strong>{{ event.date }}</strong><p>{{ event.event }}</p><small class="muted">来源：{{ event.source }}</small><blockquote v-if="event.quote">原文：{{ event.quote }}</blockquote></div></div>
    <p v-else class="muted">记录中没有足够明确的日期，暂不生成时间线。</p>
    <template v-if="analysis.risks?.length"><h3>需要关注的事项</h3><article v-for="(risk,i) in analysis.risks" :key="i" class="analysis-risk"><strong>{{ risk.title }}</strong><p>{{ risk.reason }}</p><small class="muted">{{ risk.source_refs.join(' · ') }}</small></article></template>
    <h3>建议准备的材料</h3><p class="muted small">以下为准备建议，不代表已经持有或已经审核。</p><ul><li v-for="(s,i) in analysis.suggested_materials" :key="i">{{ s }}</li></ul>
    <template v-if="analysis.next_steps?.length"><h3>接下来可以做什么</h3><ol class="next-steps"><li v-for="(step,i) in analysis.next_steps" :key="i"><span class="badge" :class="{green:step.priority==='优先'}">{{ step.priority }}</span><strong>{{ step.action }}</strong><p>{{ step.reason }}</p></li></ol></template>
    <template v-if="analysis.follow_up_questions?.length"><h3>继续把问题说清楚</h3><p class="muted small">选择一个问题，进入本案咨询并补充你的情况。</p><div class="followup-list"><button v-for="(question,i) in analysis.follow_up_questions" :key="i" :disabled="asking" @click="$emit('ask', question)">{{ question }}<span aria-hidden="true">↗</span></button></div></template>
    <SourceList :sources="analysis.sources || []" />
    <p class="legal-note">AI 辅助整理不构成正式法律意见。未接入经审核的法律知识库，法律依据需另行核验。</p>
  </div>
</template>
