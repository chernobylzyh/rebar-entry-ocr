<template>
  <div class="library-layout">
    <div class="main">
      <!-- 左栏：PDF 文档 / 页码 -->
      <aside class="sidebar">
        <div class="sidebar-top">
          <div class="libinfo">{{ libraryInfo }}</div>
          <button class="upload-btn" :disabled="processing.upload" @click="triggerPdfInput">
            {{ processing.upload ? '⏳ 上传转换中...' : '＋ 上传 PDF' }}
          </button>
          <input ref="pdfInput" type="file" accept="application/pdf,.pdf" hidden @change="onPdfInput" />
          <div class="label">PDF 文件</div>
          <select :value="selectedPdfName" @change="onSelectPdfFromDropdown">
            <option value="">-- 选择 PDF --</option>
            <option v-for="pdf in library.pdfs" :key="pdf.name" :value="pdf.name">
              {{ pdf.originalName || pdf.name }} ({{ pdf.pageCount }} 页){{ recognitionStore.isRunning(pdf.name) ? ' ⏳' : '' }}
            </option>
          </select>
          <div v-if="currentPdf" class="meta">
            {{ currentPdf.pageCount }} 页 · OCR 缓存 {{ currentPdf.ocrCachedCount }}
            <template v-if="!currentPdf.hasSourcePdf"> · 旧卷（无源 PDF）</template>
          </div>
          <div v-if="currentPdf" class="pdf-actions">
            <button :disabled="!currentPdf.hasSourcePdf || processing.resplit" @click="resplitPdf"
                    :title="currentPdf.hasSourcePdf ? '用 source.pdf 按新 DPI 重新渲染图片（会清掉 OCR 缓存和台账）' : '该卷没有原始 PDF（旧卷），请重新上传后再重切'">
              {{ processing.resplit ? '⏳ 切分中...' : '✂ 重新切分' }}
            </button>
            <button class="danger" :disabled="processing.delete" @click="deletePdf">
              {{ processing.delete ? '⏳ 删除中...' : '🗑 删除' }}
            </button>
          </div>
        </div>

        <div v-if="currentPdf" class="ledger-status" :class="ledgerStatusClass">
          {{ ledgerStatusText }}
        </div>

        <div v-if="currentPdf" class="page-list">
          <div v-if="!currentPdf.pages.length" class="empty-state">无页面</div>
          <div v-for="page in currentPdf.pages" :key="page.page"
               class="page-item"
               :class="{ active: currentPage === page.page }"
               @click="onSelectPage(page.page)">
            <span class="dot" :class="dotClass(page)"></span>
            <span>page {{ String(page.page).padStart(3, '0') }}</span>
          </div>
        </div>
        <div v-else class="empty-state" style="height:auto;padding:24px">
          <div class="icon" style="font-size:28px;margin-bottom:4px">📂</div>
          <div class="subtitle">选择一个 PDF 开始</div>
        </div>
      </aside>
      <div class="workspace">
<div v-if="currentPdf" class="toolbar">
          <span class="cur-page">
            <span>📚 单卷台账</span>
            <span v-if="currentPdf" class="sub">{{ pdfDisplayName }}</span>
          </span>
          <span class="spacer"></span>
          <button v-if="false" :disabled="processing.currentPage" @click="rerunPageOcr" title="只重跑当前页 OCR">↻ 单页 OCR</button>
          <button :disabled="!currentPdf.ledgerRecognized" @click="clearCache('ledger')" title="删除台账（保留 OCR 缓存）">🗑 清台账</button>
          <button @click="clearCache('all')" title="删除台账 + 所有 pageNNN.ocr.json">🗑 清全部</button>
          <button :class="{ active: configDrawerOpen }" @click="configDrawerOpen = !configDrawerOpen">⚙ 配置</button>
          <button class="primary" :disabled="recognitionStore.isRunning(selectedPdfName)" @click="recognizePdf">
            {{ recognitionStore.isRunning(selectedPdfName) ? ('⏳ ' + (recognizeProgress || '识别中...')) : '▶ 识别整卷 PDF' }}
          </button>
        </div>

        <div v-show="configDrawerOpen && currentPdf" class="config-drawer" :class="{ open: configDrawerOpen }">
          <div class="config-inner">
            <div class="field">
              <label>识别方式</label>
              <select v-model="config.model">
                <option value="local-paddle">本地 PaddleOCR + 自动匹配规则</option>
              </select>
            </div>
            <div class="field inline">
              <input id="forceOcrRefresh" type="checkbox" v-model="config.forceOcrRefresh" />
              <label for="forceOcrRefresh">强制重跑 OCR</label>
            </div>
          </div>
        </div>


        <div class="workspace-body">


      <!-- 中栏：源页溯源 -->
      <section class="source" :class="{ collapsed: sourceCollapsed }">
        <div class="source-head">
          <span class="source-title">源页溯源</span>
          <span class="spacer"></span>
          <button class="collapse-btn" @click="sourceCollapsed = !sourceCollapsed"
                  :title="sourceCollapsed ? '展开源页' : '折叠源页'">{{ sourceCollapsed ? '»' : '«' }}</button>
        </div>
        <div v-if="!sourceCollapsed" class="source-body">
          <div class="source-bar">
            <span class="cur-page">
              <template v-if="selectedPdfName">{{ pdfDisplayName }} / <span class="idx">page {{ String(currentPage).padStart(3, '0') }}</span></template>
              <template v-else>未选择页</template>
            </span>
            <button class="zoom-btn" :disabled="!selectedPdfName" @click="openViewer" title="放大查看当前页图片">⛶ 放大</button>
            <button class="rotate-btn" :disabled="!selectedPdfName || processing.rotate" @click="rotatePage"
                    title="顺时针旋转 90°（无损，会清本页 OCR 和整卷台账）">
              {{ processing.rotate ? '⏳ 旋转中...' : '↻ 旋转90°' }}
            </button>
          </div>
          <div class="source-meta">
            <template v-if="!selectedPdfName">选择左侧 PDF 和页码查看源页与 OCR 坐标框</template>
            <template v-else-if="pageOcr">
              📐 {{ pageOcr.image_width }} × {{ pageOcr.image_height }} ·
              {{ (pageOcr.items || []).length }} 个 OCR 项 ·
              <span class="green">绿框 {{ matchedCount }} 个 = 台账值（可点击）</span> ·
              <span class="yellow">黄框 = 其他 OCR</span>
            </template>
            <template v-else>本页无 OCR 缓存，识别整卷后阶段 1 会实时填充坐标框</template>
          </div>
          <div class="source-img">
            <div v-if="selectedPdfName" class="image-preview" @dblclick="openViewer" title="双击放大查看">
              <img :src="imageUrl" @load="onImageLoad" alt="page" />
              <svg v-if="imageLoaded && pageOcr && pageOcr.image_width"
                   :viewBox="'0 0 ' + pageOcr.image_width + ' ' + pageOcr.image_height" preserveAspectRatio="none">
                <polygon v-if="focusedEvidence" :points="focusedEvidence" class="bbox ledger flash"><title>核验字段或候选位置</title></polygon>
                <polygon v-for="(it, idx) in (pageOcr.items || [])" :key="idx"
                         :points="pointsOf(it)"
                         :data-path="pathOf(it)"
                         :class="['bbox', isMatched(it) ? 'ledger' : 'other', (highlightedPath && pathOf(it) === highlightedPath) ? 'flash' : '']"
                         @click.stop="onBboxClick(it)" @dblclick.stop>
                  <title>{{ titleOf(it) }}</title>
                </polygon>
              </svg>
            </div>
            <div v-else class="empty-state">
              <div class="icon">🖼️</div>
              <div class="subtitle">选择页码查看源页</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右栏：单卷台账 -->
      <main class="content">
        <!-- 未选择 / 加载 -->
        <div v-if="!currentPdf && !libraryLoaded" class="loading">
          <div class="spinner"></div> 加载 library 中...
        </div>
        <div v-else-if="!currentPdf" class="empty-state" style="height:50vh">
          <div class="icon">📑</div>
          <div class="title">请先选择 PDF</div>
          <div class="subtitle">从左侧下拉框选择，或到「上传识别」页上传新的 PDF</div>
        </div>

        <!-- 单卷台账视图 -->
        <template v-else>
          <div class="metrics-bar">
            <div class="m"><span class="k">总取值</span><span class="v">{{ metrics.total }}</span></div>
            <div class="m"><span class="k">命中源页</span><span class="v ok">{{ metrics.hit }}</span></div>
            <div class="m"><span class="k">待核验</span><span class="v" :class="metrics.halluc ? 'warn' : 'ok'">{{ metrics.halluc }}</span></div>
            <span class="spacer"></span>
            <button class="filter-btn" :class="{ active: hallucOnly }" @click="hallucOnly = !hallucOnly">⚠ 仅看异常字段</button>
          </div>

          <div class="ledger-toolbar">
            <span class="toolbar-title">
              该卷台账
              <template v-if="rowsData && rowsData.rows">（{{ rowsData.rows.length }} 条记录）</template>
            </span>
            <span class="spacer"></span>
            <button class="export-btn" :disabled="!rowsData || rowsData.empty" @click="confirmExportReview">✓ 核验关键字段</button>
            <button class="export-btn" :disabled="!rowsData || rowsData.empty || !allReviewed" @click="exportLedger('xlsx')">⬇ 导出 Excel</button>
            <button class="export-btn" :disabled="!rowsData || rowsData.empty || !allReviewed" @click="exportLedger('csv')">⬇ 导出 CSV</button>
            <button class="export-btn" :disabled="!rowsData || rowsData.empty || comparing" @click="manualExcelInput.click()" title="导入人工识别结果 Excel，与识别台账比对">📤 导入人工 Excel</button>
            <input ref="manualExcelInput" type="file" accept=".xlsx" class="hidden-file-input" @change="onManualExcelChange" />
            <button class="export-btn" @click="loadRows" title="刷新台账">↻ 刷新</button>
          </div>

          <div v-if="rowsData && !rowsData.empty" class="review-note">
            {{ allReviewed ? '已完成导出前核验' : '自动匹配已完成；请集中核验关键字段。点击单元格定位，双击补正，核验后导出。' }}
            <div v-for="(issue, i) in (rowsData.diagnostics || [])" :key="i">
              ⚠ {{ issue.reason || issue.code }}
              <button v-if="issue.page_no" @click="onJumpToPage(issue.page_no)">p{{ issue.page_no }}</button>
            </div>
          </div>
          <div v-if="selectedDiagnosticCell" class="review-note">
            <strong>{{ selectedDiagnosticCell.label }}</strong>
            <div v-for="(issue, i) in selectedDiagnosticCell.issues" :key="i">
              ⚠ {{ issue.reason || issue.code }}
              <button v-for="(loc, j) in (issue.locations || [])" :key="j" @click="jumpToEvidence(loc)">p{{ loc.page_no || '?' }}</button>
            </div>
            <div v-for="(candidate, i) in selectedDiagnosticCell.candidates" :key="'candidate-'+i">
              匹配候选 {{ i+1 }}
              <span>{{ candidate.reason || '候选来源' }}</span>
              <button v-for="(loc, j) in (candidate.locations || [])" :key="j" @click="jumpToEvidence(loc)">p{{ loc.page_no }}</button>
            </div>
          </div>
          <div class="table-scroll">
            <div v-if="!rowsData || rowsData.empty" class="empty-state">
              <div class="icon">📚</div>
              <div class="title">尚未生成台账</div>
              <div class="subtitle">点右上"▶ 识别整卷 PDF"开始（已缓存 OCR 时只需推理）</div>
            </div>
            <div v-else-if="!visibleRows.length" class="empty-state">
              <div class="icon">✅</div>
              <div class="subtitle">本卷没有待核验字段</div>
            </div>
            <table v-else class="master-table" :style="{ minWidth: rowsData.columns.length * 150 + 'px' }">
              <thead>
                <tr>
                  <th v-for="col in rowsData.columns" :key="col" :title="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in visibleRows" :key="row.pdf_name + '-' + row.record_index">
                  <td v-for="col in rowsData.columns" :key="col"
                      :class="{ 'empty-cell': isEmptyCell(row.cells[col]), 'has-page': !isEmptyCell(row.cells[col]) && row.cells[col].page }"
                      :data-cell="cellKey(row, col)"
                      @click="onCellClick(row, col)" @dblclick.stop="editLedgerCell(row, col)">
                    <div v-if="isEmptyCell(row.cells[col])" class="empty-marker" :title="cellReason(row.cells[col])">⚠ 未识别</div>
                    <div v-else class="chip-list">
                      <div class="mc-chip" :class="{ bad: row.cells[col].found_in_ocr === false }">
                        <span class="mc-val"
                              :title="cellReason(row.cells[col])">
                          {{ row.cells[col].value }}
                        </span>
                        <span v-if="row.cells[col].page" class="mc-page"
                              @click.stop="onJumpToPage(row.cells[col].page, cellKey(row, col))">p{{ row.cells[col].page }}</span>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="compareResult" class="compare-panel" :class="'status-' + compareResult.status">
            <div class="compare-head">
              <span class="compare-title">{{ compareStatusText(compareResult.status) }}</span>
              <span class="spacer"></span>
              <span v-if="compareResult.status === 'matched'" class="compare-badge ok">差异 0</span>
              <span v-else-if="compareResult.status === 'diff'" class="compare-badge warn">差异 {{ compareResult.diff_count }}</span>
              <button class="export-btn" @click="compareResult = null">✕ 关闭</button>
            </div>

            <div v-if="compareResult.status === 'field_unmatched'" class="compare-msg warn">
              字段未对齐，无法逐格比较。缺失列：{{ (compareResult.field_alignment.missing_columns || []).join('、') }}
              <div v-if="(compareResult.field_alignment.extra_columns || []).length" class="compare-msg">
                未识别列：{{ (compareResult.field_alignment.extra_columns || []).join('、') }}
              </div>
            </div>
            <div v-else-if="compareResult.status === 'record_unmatched'" class="compare-msg warn">
              记录未对齐：人工 {{ compareResult.record_alignment.manual_count }} 条，识别 {{ compareResult.record_alignment.recognized_count }} 条，匹配 {{ compareResult.record_alignment.matched_count }} 条
            </div>
            <div v-else-if="compareResult.status === 'matched'" class="compare-msg ok">
              完全对应：{{ compareResult.record_alignment.matched_count }} 条记录全部一致
            </div>
            <div v-else class="compare-msg warn">
              有 {{ compareResult.diff_count }} 处内容不一致，准确率 {{ accuracyText }}
            </div>

            <div v-if="compareResult.status === 'record_unmatched'" class="compare-sub">
              <div v-if="(compareResult.record_alignment.unmatched_manual || []).length" class="compare-msg">
                人工未匹配：{{ (compareResult.record_alignment.unmatched_manual || []).join('；') }}
              </div>
              <div v-if="(compareResult.record_alignment.unmatched_recognized || []).length" class="compare-msg">
                识别未匹配：{{ (compareResult.record_alignment.unmatched_recognized || []).join('；') }}
              </div>
            </div>

            <div v-if="compareResult.accuracy != null" class="compare-meta">
              共比较 {{ compareResult.total_cells }} 个单元格，一致 {{ compareResult.total_cells - compareResult.diff_count }} 个，准确率 {{ accuracyText }}
            </div>

            <table v-if="compareResult.diffs && compareResult.diffs.length" class="compare-table">
              <thead>
                <tr>
                  <th>人工记录</th>
                  <th>识别记录</th>
                  <th>字段</th>
                  <th>人工值</th>
                  <th>识别值</th>
                  <th v-if="hasDiffPage">页</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(d, i) in compareResult.diffs" :key="i">
                  <td>{{ d.manual_label }}</td>
                  <td>{{ d.recognized_label }}</td>
                  <td>{{ d.field }}</td>
                  <td class="diff-cell">{{ d.manual_value || '—' }}</td>
                  <td class="diff-cell">{{ d.recognized_value || '—' }}</td>
                  <td v-if="hasDiffPage">{{ d.page || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </main>
        </div>
      </div>
    </div>
  </div>
    <!-- 图片放大查看弹窗：按钮/滚轮缩放 + 拖拽平移 -->
    <teleport to="body">
      <div v-if="viewerOpen" class="img-viewer">
        <div class="viewer-toolbar">
          <span class="viewer-title">{{ pdfDisplayName }} · page {{ String(currentPage).padStart(3, '0') }}</span>
          <span class="spacer"></span>
          <span class="viewer-zoom-info">{{ Math.round(viewerScale * 100) }}%</span>
          <button :disabled="viewerScale <= 0.25" title="缩小" @click="zoomBy(-0.25)">−</button>
          <button :disabled="viewerScale >= 8" title="放大" @click="zoomBy(0.25)">＋</button>
          <button title="重置为 100%（双击也可重置）" @click="resetViewer">100%</button>
          <button class="close" title="关闭 (Esc)" @click="closeViewer">✕</button>
        </div>
        <div class="viewer-stage" :class="{ dragging: viewerDragging }"
             @wheel.prevent="onViewerWheel"
             @mousedown.prevent="onViewerMouseDown"
             @mousemove="onViewerMouseMove"
             @mouseup="onViewerMouseUp"
             @mouseleave="onViewerMouseUp"
             @dblclick="resetViewer">
          <div class="viewer-canvas" :style="viewerStyle">
            <img :src="imageUrl" alt="page" draggable="false" @load="onViewerImgLoad" />
            <svg v-if="imageLoaded && pageOcr && pageOcr.image_width"
                 :viewBox="'0 0 ' + pageOcr.image_width + ' ' + pageOcr.image_height" preserveAspectRatio="none">
              <polygon v-for="(it, idx) in (pageOcr.items || [])" :key="idx"
                       :points="pointsOf(it)"
                       :class="['bbox', isMatched(it) ? 'ledger' : 'other']">
                <title>{{ titleOf(it) }}</title>
              </polygon>
            </svg>
          </div>
        </div>
      </div>
    </teleport>
</template>
<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRecognitionStore } from '@/stores/recognition'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const recognitionStore = useRecognitionStore()

const library = ref({ pdfs: [] })

const libraryInfo = computed(() => {
  const l = library.value || { pdfs: [] }
  const totalPages = l.pdfs.reduce((s, p) => (s + (p.pageCount || 0)), 0)
  const recognized = l.pdfs.filter(p => p.ledgerRecognized).length
  return '📁 ' + l.pdfs.length + ' PDF · ' + totalPages + ' 页 · 台账 ' + recognized
})

const libraryLoaded = ref(false)
const currentPdf = ref(null)
const selectedPdfName = ref('')
const currentPage = ref(1)
const pageOcr = ref(null)
const imageLoaded = ref(false)
const highlightedPath = ref('')
let _highlightTimer = null
const pdfInput = ref(null)
const rowsData = ref(null)          // 单卷台账行视图：{ columns, rows, empty }
const hallucOnly = ref(false)       // 仅看异常字段
const sourceCollapsed = ref(false)  // 源页溯源面板折叠
const configDrawerOpen = ref(false)
const processing = ref({ currentPage: false, upload: false, resplit: false, delete: false, rotate: false })
const recognizeProgress = ref('')
const imgVersion = ref(0)
const comparing = ref(false)        // 正在导入人工 Excel 比对
const compareResult = ref(null)     // 人工 Excel 与识别台账的比对结果
const manualExcelInput = ref(null)

function setRecognizeProgress(text) {
  recognizeProgress.value = text
}

// ---- 推理配置（默认 Prompt 来自后端 presets，见 loadPresets）----
const config = ref({
  model: 'local-paddle',
  ocrPrompt: 'Read all the text in the image.',
  reasoningPrompt: `你是一名专业的工程监理资料员，擅长从复杂的工程报审资料中精准提取信息并录入台账。
你的任务是从提供的整卷 OCR 文字（内容来自报审表、进场检验记录、质保书/配合比报告、送货单，已用「===== 第 N 页 =====」标注页号）中提取关键信息，输出成一条条材料记录的材料监理监督台账。

一、什么是一条记录（最重要）：
台账的一行 = 一条材料记录 = 数据库的一行，由四个字段唯一确定：
  规格品种 + 炉批号 + 验收数量 + 质保书编号
- 这四个值的组合只要有一个不同，就必须拆成不同的记录（各占一个对象），严禁合并成一条。
- 四者完全相同才是同一条记录。
- 报审表上的公共字段（文件编号、材料名称、使用部位等）在本卷每条记录上都应相同。
- 典型：同一份报审表里有 C60、C35P10 等不同规格，或同一规格不同炉批号/质保书编号，必须逐条分开。

二、每个字段必须是单个值（标量），严禁数组！
- 一条记录就是一个 JSON 对象，对象里每个字段都只能有一个值，绝不能是数组/列表。
- 有 N 种不同材料，就输出 N 个记录对象，而不是在一个对象里把字段写成 ["值1","值2"]。
- 错误示例（无法入库）：{"规格品种": ["HRB400E/10mm","HRB400E/12mm"], "炉批号": ["...","..."]}
- 正确示例：{"规格品种": {"value":"HRB400E/10mm","page":7}, ...} 和 {"规格品种": {"value":"HRB400E/12mm","page":9}, ...} 是两个对象。

三、资料结构与字段来源（务必先理解，否则会张冠李戴）：
- 第1、2页是《工程材料报审表》，是整卷的公共表头。下列字段从报审表读取，对本卷所有材料记录都相同，应原样复制到每一条记录上；不要到后面的质保书/送货单里找，也不要按记录编造出不同的值：
  · 文件编号（报审表右上角编号）
  · 材料名称（报审表上的材料名称，如"混凝土""钢筋"）
  · 使用部位（报审表"拟用于工程【部位】部位"）
  · 供应商是否报审、供货日期与工程材料报审签认日期同样以报审表为准。
- 第3页起是随货资料：质保书/配合比报告来自"生产单位"，送货单/发货单来自"供应单位"，进场检验记录登记进场数量。下列字段按每条材料记录分别从这些单据提取，随规格品种/炉批号不同而不同：
  · 规格品种、验收数量、炉批号、质保书编号、生产单位、供应单位、送货单编号。
  · 【极易填反，务必区分】炉批号取质保书/质保卡上的「轧制批号」或「炉批号」（抚顺新钢铁等钢厂通常是一串纯数字，如 8 位 46200156）；质保书编号取质保书的「合同编号」或「质检号」（抚顺多为 WK 开头的编号）。带 WK 等字母前缀的是质保书编号，不是炉批号；纯数字的炉批号不要填到质保书编号。

四、字段提取规则：
1. 供应商是否报审：报审表存在且提交过 → 填"是"；否则省略【报审表】
2. 文件编号：报审表右上角编号，无则省略【报审表·整卷公共】
3. 材料名称：报审表中的材料名称（如"混凝土"、"钢筋"）【报审表·整卷公共】
4. 规格品种：提取材料的规格型号（混凝土如 C60、C35P10；钢筋按"牌号/直径mm"，如 HRB400E/Φ16mm）【质保书/送货单】
5. 生产单位：从质保书/配合比设计报告的顶部标题栏提取（如"XX 公司"）【生产单位单据】
6. 供应单位：从送货单/发货单的顶部标题栏提取（如"XX 拌站"）【供应单位单据】
7. 供货日期与工程材料报审签认日期：提取报审表上的进场/签认日期，格式：YYYY/MM/DD【报审表】
8. 使用部位：报审表固定句式为"拟用于工程【部位】部位的【材料名称】，经我方检验合格"。只提取"工程"与"部位"之间的内容（如"B区地上钢结构"），严禁把"部位的"之后的材料名称并入使用部位；该部分应填入"材料名称"字段【报审表·整卷公共】
9. 送货单编号：提取送货单/发货单右上角的单据编号，无则省略【供应单位单据】
10. 炉批号：取质保书/电子质保卡上「轧制批号」或「炉批号」标签对应的值（不是合同编号/质检号！）。钢厂（如抚顺新钢铁）的炉批号通常是一串纯数字（如 8 位 46200156）；带 WK 等字母前缀的编号是质保书编号，不要填到这里。配合比报告则取其报告编号。与送货单编号是两个独立字段，严禁合并或用 / 拼接【质保书/质保卡】
11. 验收数量：按进场检验记录或送货单的总量填写，带单位（如 99m3、38.925t）。进场检验记录是核对清单：其「合格证号」列必须能与对应质保书的「合同编号」对上，用这一对齐关系确定每一行的规格品种/炉批号/数量归属；若相邻行的数量与规格明显错位（表格物理串行，常见于同规格相邻行互换），以「合格证号能对上质保书合同编号」的那行为准，不要机械照抄错位行【进场检验记录/送货单】
12. 质保书编号：取质保书的「合同编号」或「质检号」（抚顺新钢铁等多为 WK 开头的编号，如 WK……）；它应与进场检验记录「合格证号」列的值一致，可互相印证。不要把纯数字的炉批号填到这里。配合比报告取其报告编号【生产单位单据】
13. 【提取规则，不是字段】跨单据对齐：一套材料通常由「质保书 + 电子质保卡 + 送货单 + 进场检验记录一行」组成。先用质保书的合同编号去进场检验记录「合格证号」列定位到对应行，再把该行的规格品种、验收数量、炉批号与质保书/质保卡/送货单上的值归集到同一条记录；合同编号对不上的不要强行并到一起。

五、输出格式（务必严格遵守，否则渲染失败）：
输出一个 JSON 对象，形如 {"records": [ {记录1}, {记录2}, ... ]}。
- records 是数组，每个元素是一条材料记录，是"字段名 → 字段对象"的映射。
- **每个字段的值必须是一个对象 {"value": "字段值", "page": N}**：
  · value 是该字段的单个字符串值（严禁数组）；
  · page 是**这个值实际出现在第几页**，必须取自 OCR 文本里 "===== 第 N 页 =====" 分隔线中的 N（全卷绝对页号）。
- **每个字段标它自己的来源页**：同一条记录的不同字段往往来自不同页。例如规格品种/验收数量在送货单页就标送货单页号，炉批号/质保书编号/生产单位在质保书页就标质保书页号，报审表公共字段标第 1 或第 2 页。**不要图省事把整条记录的字段都标成同一个页号**。
- 严禁用"第几张图片""第几个附件"这类相对序号作为 page。
- 每条记录必须包含那四个主键字段（规格品种、炉批号、验收数量、质保书编号）；找不到就填 {"value":"","page":该字段应在的页号}，但键要保留。
- 报审表公共字段（文件编号、材料名称、使用部位等）在报审表存在时应出现在每条记录上，page 标报审表所在页。
- 其余字段找不到就省略该键，不要填 null、"无"、"N/A"、"暂无" 等占位符，也不要输出数组。
- 去除 OCR 识别产生的乱码，确保数字和字母准确。OCR 可能把 0/8、1/7、5/6 等数字认错或截断；当相邻两页属于同一套单据时（如电子质保卡 + 质保书、送货单 + 进场记录），可用两页文字互相校正数字，但 OCR 原文里完全不存在的编号严禁臆造。
- 只允许出现上述 1-12 列出的字段（下面第 13 条是提取规则，不是字段，禁止把它作为字段输出），不要凭空造出"准用证、产品标志、外观质量、抗压强度、氯离子含量、碱含量"等未定义字段。
- 记录对象顶层可带一个整数 page（取规格品种/验收数量所在的主要页）作为兜底；但只要某字段实际来自别的页，就必须在该字段对象里写它自己的 page，不能依赖顶层兜底。
- 没有任何材料记录时输出 {"records": []}。
- 直接输出 JSON，不要 markdown 代码块围栏（\`\`\`），不要任何解释文字。`,
  forceOcrRefresh: false
})

// ----------------- computed -----------------

const pdfDisplayName = computed(() => {
  if (!currentPdf.value) return ''
  return currentPdf.value.originalName || currentPdf.value.name
})

const imageUrl = computed(() => {
  if (!selectedPdfName.value) return ''
  return '/api/library/' + encodeURIComponent(selectedPdfName.value) +
    '/pages/' + currentPage.value + '/image?t=' + Date.now() + '&v=' + imgVersion.value
})

const ledgerStatusClass = computed(() => {
  if (!currentPdf.value) return ''
  if (recognitionStore.isRunning(selectedPdfName.value)) return 'processing'
  if (currentPdf.value.ledgerRecognized) {
    return (currentPdf.value.ledgerHallucinationCount || 0) > 0 ? 'warn' : 'ok'
  }
  return ''
})

const ledgerStatusText = computed(() => {
  if (!currentPdf.value) return ''
  if (recognitionStore.isRunning(selectedPdfName.value)) {
    return recognizeProgress.value ? '📚 ' + recognizeProgress.value : '📚 生成台账中…'
  }
  if (currentPdf.value.ledgerRecognized) {
    const h = currentPdf.value.ledgerHallucinationCount || 0
    return h > 0 ? ('📚 台账已生成 · ⚠ ' + h + ' 处待核验') : '📚 台账已生成 · ✓ 全部命中'
  }
  return '📚 未生成台账，点右上"识别整卷 PDF"'
})

// ---- 台账行视图派生数据 ----

const visibleRows = computed(() => {
  const rows = (rowsData.value && rowsData.value.rows) || []
  if (!hallucOnly.value) return rows
  return rows.filter(rowHasBadCell)
})

function rowHasBadCell(row) {
  return Object.values((row && row.cells) || {}).some(c => c && c.found_in_ocr === false)
}

const metrics = computed(() => {
  const rows = (rowsData.value && rowsData.value.rows) || []
  let total = 0
  let halluc = 0
  for (const row of rows) {
    for (const c of Object.values((row && row.cells) || {})) {
      if (c && c.value) {
        total++
        if (c.found_in_ocr === false) halluc++
      }
    }
  }
  return { total, hit: total - halluc, halluc }
})

const accuracyText = computed(() => {
  const a = compareResult.value && compareResult.value.accuracy
  return a == null ? '—' : (a * 100).toFixed(1) + '%'
})

const hasDiffPage = computed(() => {
  const diffs = (compareResult.value && compareResult.value.diffs) || []
  return diffs.some(d => d.page != null)
})

function isEmptyCell(cell) {
  return !cell || !cell.value
}

// 单元格唯一 key：record_index 稳定（过滤后不变），用于 bbox ↔ 单元格互相定位
function cellKey(row, col) {
  const idx = (row && row.record_index != null) ? row.record_index : 0
  return idx + '::' + col
}

// ----------------- 源页 bbox 匹配 -----------------

function normalize(s) {
  return (s == null ? '' : String(s)).replace(/\s+/g, '').toLowerCase()
}

function textMatchesValue(textNorm, valueNorm) {
  if (!valueNorm) return false
  if (textNorm.includes(valueNorm)) return true
  const parts = valueNorm.split(/[^\p{L}\p{N}]+/u)
  for (const p of parts) {
    if (p.length >= 2 && textNorm.includes(p)) return true
  }
  return false
}

function ledgerValuesForCurrentPage() {
  const vals = []
  if (!rowsData.value || !rowsData.value.rows) return vals
  for (const row of rowsData.value.rows) {
    for (const c of Object.values((row && row.cells) || {})) {
      if (c && c.page === currentPage.value && c.value) vals.push(c.value)
    }
  }
  return vals
}

function ledgerEntryForCurrentPage(text) {
  if (!rowsData.value || !rowsData.value.rows) return null
  const tn = normalize(text)
  for (const row of rowsData.value.rows) {
    const cells = (row && row.cells) || {}
    for (const name of Object.keys(cells)) {
      const c = cells[name]
      if (c && c.page === currentPage.value && c.value && textMatchesValue(tn, normalize(c.value))) {
        return { name, value: c.value, key: cellKey(row, name) }
      }
    }
  }
  return null
}

function isMatched(it) {
  if (it && it.path) return true
  if (pageOcr.value?.schema_version === 'automatic-ledger-v1') return false
  if (!it || !it.text) return false
  const vals = ledgerValuesForCurrentPage()
  if (!vals.length) return false
  const tn = normalize(it.text)
  return vals.some(v => textMatchesValue(tn, normalize(v)))
}

function pathOf(it) {
  const match = it && it.path && it.path.match(/^records\[(\d+)\]\.(.+)$/)
  if (match) return match[1] + '::' + match[2]
  if (pageOcr.value?.schema_version === 'automatic-ledger-v1') return ''
  // 返回第一个命中本 OCR 项的台账单元格 key（record_index::字段），未命中返回空串
  if (!it || !it.text) return ''
  const e = ledgerEntryForCurrentPage(it.text)
  return e ? e.key : ''
}

function onBboxClick(it) {
  // 仅命中台账的绿框可点击 → 反向跳转到台账表格对应单元格
  if (!isMatched(it)) return
  const key = pathOf(it)
  if (!key) return
  jumpToLedgerCell(key)
}

async function jumpToLedgerCell(key) {
  await nextTick()
  const root = document.querySelector('.table-scroll')
  if (!root) return
  const target = root.querySelector('td[data-cell="' + cssEscapeAttr(key) + '"]')
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' })
  target.classList.remove('cell-flash')
  void target.offsetWidth
  target.classList.add('cell-flash')
  setTimeout(() => target.classList.remove('cell-flash'), 10000)
}

function cssEscapeAttr(s) {
  // 简单转义：data-cell selector 用的双引号/反斜杠
  return String(s == null ? '' : s).replace(/("|\\)/g, '\\$1')
}

const matchedCount = computed(() => {
  if (!pageOcr.value || !pageOcr.value.items) return 0
  return pageOcr.value.items.filter(isMatched).length
})

function pointsOf(it) {
  const loc = it && it.location
  if (loc && loc.length >= 8) {
    return [[loc[0], loc[1]], [loc[2], loc[3]], [loc[4], loc[5]], [loc[6], loc[7]]]
      .map(p => p.join(',')).join(' ')
  }
  return ''
}

function titleOf(it) {
  if (!it) return ''
  if (isMatched(it)) {
    const e = ledgerEntryForCurrentPage(it.text)
    if (e) return e.name + ': ' + e.value + '\n\n' + (it.text || '')
  }
  return it.text || ''
}

function dotClass(page) {
  if (page.page === currentPage.value) return 'selected'
  return page.ocrCached ? 'ocr-cached' : ''
}

const selectedDiagnosticCell = ref(null)
const focusedEvidence = ref('')
const allReviewed = computed(() => !!rowsData.value?.rows?.length && rowsData.value.rows.every(r => r.review_confirmed))
function cellReason(cell) {
  return (cell?.diagnostics || []).map(i => i.reason || i.code).join('；') || (cell?.page ? '来源页 p' + cell.page : '来源位置未定位')
}
async function jumpToEvidence(loc) {
  if (!loc?.page_no) return
  await onJumpToPage(loc.page_no)
  if (!loc.polygon_page || !pageOcr.value) return
  // Original PDF page axes -> current display image axes. Evidence may come from 300 DPI inspection cells.
  const size = loc.source_pixel_size || [pageOcr.value.original_width, pageOcr.value.original_height]
  const width = pageOcr.value.image_width, height = pageOcr.value.image_height
  const rotation = pageOcr.value.rotation_cw || 0
  const ow = rotation % 180 ? height : width, oh = rotation % 180 ? width : height
  focusedEvidence.value = loc.polygon_page.map(([x,y]) => {
    x = x * ow / size[0]; y = y * oh / size[1]
    if (rotation === 90) return [oh-y,x].join(',')
    if (rotation === 180) return [ow-x,oh-y].join(',')
    if (rotation === 270) return [y,ow-x].join(',')
    return [x,y].join(',')
  }).join(' ')
}
async function editLedgerCell(row, col) {
  const value = window.prompt('补正「' + col + '」（保留原始OCR和诊断）', row.cells[col]?.value || '')
  if (value === null) return
  try {
    const response = await fetch('/api/library/' + encodeURIComponent(selectedPdfName.value) + '/ledger/field', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ record_index: row.record_index, field: col, value })
    })
    const body = await response.json()
    if (!response.ok || body.code !== 200) throw new Error(body.msg || '补正失败')
    await loadRows()
  } catch (e) { ElMessage.error(e.message) }
}
async function confirmExportReview() {
  if (!rowsData.value?.revision) { ElMessage.warning('请重新识别以生成可核验版本'); return }
  if (!window.confirm('请核对全部关键字段及缺失、冲突、重复诊断。确认已检查原图并完成必要补正？修改字段或重新识别会使本次确认失效。')) return
  try {
    const response = await fetch('/api/library/' + encodeURIComponent(selectedPdfName.value) + '/ledger/review', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ revision: rowsData.value.revision, note: '用户在导出前集中核验关键字段和匹配异常' })
    })
    const body = await response.json()
    if (!response.ok || body.code !== 200) throw new Error(body.msg || '核验失败')
    await loadRows(); ElMessage.success('核验已保存，可以导出')
  } catch (e) { ElMessage.error(e.message) }
}
function onCellClick(row, col) {
  const current = row.cells[col]
  selectedDiagnosticCell.value = { label: col, issues: [...(current?.diagnostics || []), ...(row.diagnostics || [])], candidates: row.match_candidates || [] }
  const cell = (row && row.cells && row.cells[col]) || null
  if (!cell || !cell.page) return
  onJumpToPage(cell.page, cellKey(row, col))
}


// ---- 图片放大查看弹窗（滚轮/按钮缩放 + 拖拽平移） ----
const viewerOpen = ref(false)
const viewerScale = ref(1)
const viewerTx = ref(0)
const viewerTy = ref(0)
const viewerDragging = ref(false)
let _viewerDrag = null
let _viewerAutoCentered = false

const viewerStyle = computed(() => ({
  transform: 'translate(' + viewerTx.value + 'px, ' + viewerTy.value + 'px) scale(' + viewerScale.value + ')',
  transformOrigin: '0 0'
}))

function openViewer() {
  if (!selectedPdfName.value) return
  _viewerAutoCentered = false
  resetViewer()
  viewerOpen.value = true
  window.addEventListener('keydown', onViewerKey)
}

function closeViewer() {
  viewerOpen.value = false
  viewerDragging.value = false
  _viewerDrag = null
  window.removeEventListener('keydown', onViewerKey)
  resetViewer()
}

function onViewerKey(e) {
  if (e.key === 'Escape') closeViewer()
}

function resetViewer() {
  viewerScale.value = 1
  centerViewer()
  viewerDragging.value = false
  _viewerDrag = null
}

// 图片默认在弹窗舞台中居中显示；拖拽/缩放均基于该居中位置累加
function viewerCenterOffsets() {
  const stage = document.querySelector('.viewer-stage')
  const img = document.querySelector('.viewer-canvas img')
  if (!stage || !img || !img.offsetWidth || !img.offsetHeight) return { cx: 0, cy: 0 }
  return {
    cx: Math.max(0, (stage.clientWidth - img.offsetWidth) / 2),
    cy: Math.max(0, (stage.clientHeight - img.offsetHeight) / 2)
  }
}

function centerViewer() {
  const o = viewerCenterOffsets()
  viewerTx.value = o.cx
  viewerTy.value = o.cy
}

// 弹窗图片加载完成后居中一次（避免打开瞬间偏左）
function onViewerImgLoad() {
  if (viewerOpen.value && !_viewerAutoCentered) {
    _viewerAutoCentered = true
    centerViewer()
  }
}

function zoomBy(delta) {
  const stage = document.querySelector('.viewer-stage')
  const cx = stage ? stage.clientWidth / 2 : 0
  const cy = stage ? stage.clientHeight / 2 : 0
  zoomAt(cx, cy, viewerScale.value + delta)
}

function onViewerWheel(e) {
  const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12
  const rect = e.currentTarget.getBoundingClientRect()
  zoomAt(e.clientX - rect.left, e.clientY - rect.top, viewerScale.value * factor)
}

// 以锚点 (mx, my) 缩放：保持鼠标下的内容不动
function zoomAt(mx, my, target) {
  const next = Math.min(8, Math.max(0.25, target))
  const ratio = next / viewerScale.value
  viewerTx.value = mx - (mx - viewerTx.value) * ratio
  viewerTy.value = my - (my - viewerTy.value) * ratio
  viewerScale.value = next
}

function onViewerMouseDown(e) {
  if (e.button !== 0) return
  _viewerDrag = { startX: e.clientX, startY: e.clientY, tx0: viewerTx.value, ty0: viewerTy.value }
  viewerDragging.value = true
}

function onViewerMouseMove(e) {
  if (!_viewerDrag) return
  viewerTx.value = _viewerDrag.tx0 + (e.clientX - _viewerDrag.startX)
  viewerTy.value = _viewerDrag.ty0 + (e.clientY - _viewerDrag.startY)
}

function onViewerMouseUp() {
  _viewerDrag = null
  viewerDragging.value = false
}

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onViewerKey)
})

// ----------------- data fetching -----------------

async function loadLibrary() {
  try {
    const r = await fetch('/api/library')
    if (!r.ok) throw new Error('HTTP ' + r.status)
    const data = await r.json()
    // 后端用 ApiResponse.ok 包裹: {code, msg, data: 真正的内容}
    library.value = (data && data.data) ? data.data : (data || { pdfs: [] })
    if (!library.value.pdfs) library.value = { pdfs: [] }
    if (selectedPdfName.value) {
      currentPdf.value = library.value.pdfs.find(p => p.name === selectedPdfName.value) || null
    }
  } catch (e) {
    ElMessage.error('加载 library 失败: ' + e.message)
    library.value = { pdfs: [] }
  } finally {
    libraryLoaded.value = true
  }
}

function onSelectPdfFromDropdown(e) {
  const name = e.target.value
  const routeName = decodeURIComponent(route.params.pdfName || '')
  if (!name) {
    selectedPdfName.value = ''
    currentPdf.value = null
    pageOcr.value = null
    rowsData.value = null
    compareResult.value = null
    return
  }
  if (name === selectedPdfName.value) return
  if (name === routeName) {
    selectCurrentPdf(name)
  } else {
    router.push('/history/' + encodeURIComponent(name))
  }
}

let _loadSeq = 0
async function selectCurrentPdf(name) {
  const seq = ++_loadSeq
  selectedPdfName.value = name
  currentPdf.value = library.value.pdfs.find(p => p.name === name) || null
  if (currentPdf.value && currentPdf.value.pages && currentPdf.value.pages.length) {
    currentPage.value = currentPdf.value.pages[0].page
    await loadPageOcr()
  } else {
    currentPage.value = 1
    pageOcr.value = null
  }
  if (seq !== _loadSeq) return
  compareResult.value = null
  await loadRows()
}

async function onSelectPage(p) {
  focusedEvidence.value = ''
  currentPage.value = p
  sourceCollapsed.value = false
  await loadPageOcr()
}

// 从台账表点 [pN] / 单元格：跳源页 + 展开溯源面板 + 高亮对应 bbox
async function onJumpToPage(p, path) {
  highlightedPath.value = path || ''
  if (_highlightTimer) clearTimeout(_highlightTimer)
  if (path) {
    _highlightTimer = setTimeout(() => { highlightedPath.value = '' }, 10000)
  }
  await onSelectPage(p)
}

async function loadPageOcr() {
  if (!selectedPdfName.value) return
  imageLoaded.value = false
  pageOcr.value = null
  try {
    const r = await fetch('/api/library/' + encodeURIComponent(selectedPdfName.value) +
      '/pages/' + currentPage.value + '/ocr')
    if (r.status === 404) return
    if (!r.ok) throw new Error('HTTP ' + r.status)
    const data = await r.json()
    pageOcr.value = (data && data.data) || data
    // 图片可能因同 URL 缓存不触发 load 事件（如从总台账跳回默认第 1 页），
    // 若图片已完成加载则直接置位，否则等 <img @load> 回调（onImageLoad）
    const img = document.querySelector('.source-img img')
    if (img && img.complete && img.naturalWidth > 0) {
      imageLoaded.value = true
    }
  } catch (e) {
    pageOcr.value = null
  }
}

// 单卷台账行视图：与总台账同款 columns + rows（未生成时后端返回 code=404，这里静默置空）
async function loadRows() {
  if (!selectedPdfName.value) { rowsData.value = null; return }
  try {
    const r = await fetch('/api/library/' + encodeURIComponent(selectedPdfName.value) + '/ledger/rows')
    const j = await r.json().catch(() => ({}))
    if (!r.ok || (j && j.code && j.code !== 200)) { rowsData.value = null; return }
    rowsData.value = (j && j.data) || null
  } catch (e) {
    rowsData.value = null
  }
}

function onImageLoad() { imageLoaded.value = true }

async function rerunPageOcr() {
  if (!selectedPdfName.value || processing.value.currentPage) return
  processing.value.currentPage = true
  try {
    const fd = new URLSearchParams()
    if (config.value.ocrPrompt) fd.append('prompt', config.value.ocrPrompt)
    fd.append('fields', '')
    fd.append('classify_prompt', '')
    fd.append('classify_schema', '')
    const r = await fetch('/api/library/' + encodeURIComponent(selectedPdfName.value) +
      '/pages/' + currentPage.value + '/ocr', {
      method: 'POST',
      body: fd,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    const j = await r.json().catch(() => ({}))
    if (!r.ok || (j && j.code && j.code !== 200)) {
      throw new Error((j && j.msg) || ('HTTP ' + r.status))
    }
    await loadLibrary()
    await loadPageOcr()
    ElMessage.success('单页 OCR 完成')
  } catch (e) {
    ElMessage.error('单页 OCR 失败: ' + e.message)
  } finally {
    processing.value.currentPage = false
  }
}

// 识别请求未确认时的兜底：轮询 /api/library，直到该卷 ledgerRecognized=true 再刷新视图（最多约 30 分钟）。
async function ensureLedgerRefreshed(name, dispName) {
  const check = async () => {
    try {
      const r = await fetch('/api/library')
      if (!r.ok) return false
      const data = await r.json()
      const lib = (data && data.data) || data
      const p = (lib.pdfs || []).find(x => x.name === name)
      return !!(p && p.ledgerRecognized)
    } catch (e) {
      return false
    }
  }
  const applyResult = async () => {
    await loadLibrary()
    if (selectedPdfName.value === name) await selectCurrentPdf(name)
    ElMessage.success('台账已生成：' + dispName)
  }
  // 先立即查一次：可能请求虽失败但后台已写完
  if (await check()) {
    await applyResult()
    return
  }
  await new Promise((resolve) => {
    let attempts = 0
    const timer = setInterval(async () => {
      attempts++
      let ok = false
      try { ok = await check() } catch (e) { /* ignore */ }
      if (ok) {
        clearInterval(timer)
        await applyResult()
        resolve()
      } else if (attempts >= 360) {
        clearInterval(timer)
        resolve()
      }
    }, 5000)
  })
}

async function recognizePdf() {
  const name = selectedPdfName.value
  if (!name || recognitionStore.isRunning(name)) return
  if (!config.value.reasoningPrompt) {
    ElMessage.warning('请先填写推理 Prompt（点 配置 按钮打开抽屉）')
    configDrawerOpen.value = true
    return
  }
  const startPdf = currentPdf.value && currentPdf.value.name === name ? currentPdf.value : null
  const dispName = (startPdf && (startPdf.originalName || startPdf.name)) || name
  recognitionStore.start(name)
  setRecognizeProgress('')
  try {
    // ---- 阶段 1：逐页 OCR，先出黄框 ----
    const forceOcr = config.value.forceOcrRefresh
    const ocrPrompt = config.value.ocrPrompt
    const pages = (startPdf && startPdf.pages) || []
    const todo = pages.filter(pg => forceOcr || !pg.ocrCached)
    const CONCURRENCY = 4
    let done = 0
    let failed = 0
    const progressText = () => {
      let t = '阶段1 逐页OCR ' + Math.min(done, todo.length) + '/' + todo.length
      if (failed > 0) t += '（失败 ' + failed + '）'
      return t
    }
    if (todo.length) {
      setRecognizeProgress(progressText())
      for (let i = 0; i < todo.length; i += CONCURRENCY) {
        const chunk = todo.slice(i, i + CONCURRENCY)
        await Promise.allSettled(chunk.map(async (pg) => {
          try {
            const fd = new URLSearchParams()
            if (ocrPrompt) fd.append('prompt', ocrPrompt)
            const r = await fetch('/api/library/' + encodeURIComponent(name) +
              '/pages/' + pg.page + '/ocr', {
              method: 'POST',
              body: fd,
              headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            })
            const j = await r.json().catch(() => ({}))
            if (!r.ok || (j && j.code && j.code !== 200)) {
              throw new Error((j && j.msg) || ('HTTP ' + r.status))
            }
            const d = (j && j.data) || j
            if (d && d.error) throw new Error(d.error)
          } catch (e) { /* 单页失败不阻断；阶段2远端会补跑缺失页 */ failed++ }
          // 正在查看的页识别完成后立即刷新黄框（不等整批结束）
          if (selectedPdfName.value === name && pg.page === currentPage.value) {
            await loadPageOcr()
            imageLoaded.value = true
          }
        }))
        done += chunk.length
        setRecognizeProgress(progressText())
        // 当前页有新 OCR 时立即刷新黄框
        if (selectedPdfName.value === name) {
          await loadPageOcr()
          imageLoaded.value = true
        }
      }
      await loadLibrary()
    }

    // ---- 阶段 2：整卷推理（复用阶段1的 OCR 缓存），生成台账并标绿框 ----
    setRecognizeProgress('阶段2 整卷推理中...')
    const fd2 = new URLSearchParams()
    fd2.append('prompt', config.value.reasoningPrompt)
    if (ocrPrompt) fd2.append('ocr_prompt', ocrPrompt)
    if (config.value.model) fd2.append('model', config.value.model)
    const r2 = await fetch('/api/library/' + encodeURIComponent(name) +
      '/recognize', {
      method: 'POST',
      body: fd2,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    const j2 = await r2.json().catch(() => ({}))
    if (!r2.ok || (j2 && j2.code && j2.code !== 200)) {
      throw new Error((j2 && j2.msg) || ('HTTP ' + r2.status))
    }
    await loadLibrary()
    if (selectedPdfName.value === name) {
      await selectCurrentPdf(name)
    }
    ElMessage.success('台账已生成：' + dispName)
  } catch (e) {
    const errMsg = String((e && e.message) || e || '')
    const mayStillRun = /fetch|timeout|timed out|NetworkError|ECONNABORTED|SocketTimeout/i.test(errMsg)
    if (mayStillRun) {
      ElMessage.error('识别请求未确认（' + errMsg + '），后台可能仍在识别，正在自动检查结果...')
      await ensureLedgerRefreshed(name, dispName)
    } else {
      ElMessage.error('识别失败: ' + errMsg)
    }
  } finally {
    recognitionStore.finish(name)
    setRecognizeProgress('')
  }
}

async function clearCache(scope) {
  if (!selectedPdfName.value) return
  const msg = scope === 'all'
    ? '清除全部缓存？下次 recognize 全部要重跑 OCR（约 4 分钟）。图片本身不会被删除。'
    : '清除台账？下次 recognize 只重推理（约 40 秒）。'
  if (!confirm(msg)) return
  try {
    const r = await fetch('/api/library/' + encodeURIComponent(selectedPdfName.value) +
      '/cache?scope=' + scope, { method: 'DELETE' })
    const j = await r.json().catch(() => ({}))
    if (!r.ok || (j && j.code && j.code !== 200)) {
      throw new Error((j && j.msg) || ('HTTP ' + r.status))
    }
    await loadLibrary()
    pageOcr.value = null
    rowsData.value = null
    await loadRows()
    ElMessage.success('清除成功')
  } catch (e) {
    ElMessage.error('清除失败: ' + e.message)
  }
}

function exportLedger(format) {
  const name = selectedPdfName.value
  if (!name) return
  if (!rowsData.value || rowsData.value.empty) {
    ElMessage.warning('暂无可导出数据')
    return
  }
  window.location.href = '/api/library/' + encodeURIComponent(name) + '/export?format=' + (format || 'xlsx')
}

function compareStatusText(status) {
  if (status === 'matched') return '完全对应'
  if (status === 'diff') return '内容不一致'
  if (status === 'field_unmatched') return '字段未对齐'
  if (status === 'record_unmatched') return '记录未对齐'
  return '比对结果'
}

async function onManualExcelChange(e) {
  const input = e.target
  const file = input && input.files && input.files[0]
  if (input) input.value = ''
  if (!file) return
  if (!/\.xlsx$/i.test(file.name)) {
    ElMessage.error('暂只支持 .xlsx 格式的人工识别结果')
    return
  }
  comparing.value = true
  compareResult.value = null
  try {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch('/api/library/' + encodeURIComponent(selectedPdfName.value) + '/ledger/compare', {
      method: 'POST',
      body: fd
    })
    const j = await r.json().catch(() => ({}))
    if (!r.ok || (j && j.code && j.code !== 200)) {
      throw new Error((j && j.msg) || ('HTTP ' + r.status))
    }
    compareResult.value = (j && j.data) || null
    if (compareResult.value && compareResult.value.status === 'matched') {
      ElMessage.success('人工 Excel 与识别台账完全对应')
    }
  } catch (err) {
    ElMessage.error('比对失败: ' + err.message)
  } finally {
    comparing.value = false
  }
}

// ---------------- 上传 / 删除 / 重新切分 / 旋转 ----------------

function triggerPdfInput() { pdfInput.value && pdfInput.value.click() }

function onPdfInput(e) {
  const file = e.target.files && e.target.files[0]
  if (file) uploadPdf(file)
  e.target.value = ''
}

async function uploadPdf(fileObj) {
  if (!fileObj || processing.value.upload) return
  const send = async (overwrite) => {
    const fd = new FormData()
    fd.append('file', fileObj)
    fd.append('dpi', '200')
    fd.append('image_format', 'PNG')
    if (overwrite) fd.append('overwrite', 'true')
    const r = await fetch('/api/library/upload', { method: 'POST', body: fd })
    const data = await r.json().catch(() => ({}))
    if (!r.ok || (data && data.code && data.code !== 200)) {
      const err = new Error((data && data.msg) || ('HTTP ' + r.status))
      err.code = data && data.code
      throw err
    }
    return data
  }
  processing.value.upload = true
  try {
    let data
    try {
      data = await send(false)
    } catch (e) {
      if (e && e.code === 409) {
        const ok = await ElMessageBox.confirm(
          `「${fileObj.name}」已存在，覆盖会删除该卷已有的 OCR 缓存和台账，确定覆盖吗？`,
          '同名 PDF',
          { type: 'warning', confirmButtonText: '覆盖', cancelButtonText: '取消' }
        ).catch(() => false)
        if (!ok) return
        data = await send(true)
      } else {
        throw e
      }
    }
    await loadLibrary()
    const d = (data && data.data) || {}
    const pdfName = d.pdfName || ''
    if (pdfName) await selectCurrentPdf(pdfName)
    ElMessage.success('上传成功：' + (d.originalName || pdfName) + '，共 ' + (d.pageCount || 0) + ' 页')
  } catch (e) {
    ElMessage.error('上传失败: ' + e.message)
  } finally {
    processing.value.upload = false
  }
}

async function resplitPdf() {
  if (!selectedPdfName.value || !currentPdf.value || processing.value.resplit) return
  if (!currentPdf.value.hasSourcePdf) {
    ElMessage.warning('该卷没有原始 PDF（旧卷），请重新上传后再重切')
    return
  }
  const name = currentPdf.value.name
  const dpiInput = prompt('重新切分「' + name + '」\n\n请输入渲染 DPI（72-600，推荐 200-300）：', '200')
  if (dpiInput === null) return
  const dpi = parseInt(dpiInput, 10)
  if (!Number.isInteger(dpi) || dpi < 72 || dpi > 600) {
    ElMessage.warning('DPI 必须是 72-600 之间的整数')
    return
  }
  const lost = []
  if (currentPdf.value.ocrCachedCount) lost.push(currentPdf.value.ocrCachedCount + ' 页 OCR 缓存')
  if (currentPdf.value.ledgerRecognized) lost.push('整卷台账')
  const warn = lost.length ? '\n\n注意：会清掉 ' + lost.join('、') + '（换 DPI 后旧坐标框会错位），需要重新识别。' : ''
  if (!confirm('将用 source.pdf 按 ' + dpi + ' DPI 重新生成 ' + (currentPdf.value.pageCount || 0) + ' 页图片。' + warn + '\n\n继续吗？')) return
  processing.value.resplit = true
  try {
    const fd = new FormData()
    fd.append('dpi', String(dpi))
    fd.append('image_format', 'PNG')
    const r = await fetch('/api/library/' + encodeURIComponent(name) + '/resplit', { method: 'POST', body: fd })
    const data = await r.json().catch(() => ({}))
    if (!r.ok || (data && data.code && data.code !== 200)) {
      throw new Error((data && data.msg) || ('HTTP ' + r.status))
    }
    imgVersion.value++
    pageOcr.value = null
    rowsData.value = null
    await loadLibrary()
    const d = (data && data.data) || {}
    await selectCurrentPdf(name)
    ElMessage.success('重新切分完成：' + (d.page_count || 0) + ' 页 @ ' + (d.dpi || dpi) + ' DPI')
  } catch (e) {
    ElMessage.error('重新切分失败: ' + e.message)
  } finally {
    processing.value.resplit = false
  }
}

async function deletePdf() {
  if (!selectedPdfName.value || !currentPdf.value || processing.value.delete) return
  const p = currentPdf.value
  const parts = [p.pageCount + ' 页图片']
  if (p.ocrCachedCount) parts.push(p.ocrCachedCount + ' 页 OCR 缓存')
  if (p.ledgerRecognized) parts.push('整卷台账')
  if (p.hasSourcePdf) parts.push('原始 PDF')
  if (!confirm('确定删除「' + p.name + '」吗？\n\n将永久删除：' + parts.join('、') + '。\n\n此操作不可恢复。')) return
  processing.value.delete = true
  try {
    const r = await fetch('/api/library/' + encodeURIComponent(p.name), { method: 'DELETE' })
    const data = await r.json().catch(() => ({}))
    if (!r.ok || (data && data.code && data.code !== 200)) {
      throw new Error((data && data.msg) || ('HTTP ' + r.status))
    }
    await loadLibrary()
    selectedPdfName.value = ''
    currentPdf.value = null
    currentPage.value = 1
    pageOcr.value = null
    rowsData.value = null
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  } finally {
    processing.value.delete = false
  }
}

// 单页旋转：顺时针 90°。可逆（点 4 次回原位），不弹确认框。
async function rotatePage() {
  if (!selectedPdfName.value || !currentPdf.value || processing.value.rotate) return
  if (currentPage.value == null) return
  processing.value.rotate = true
  const name = currentPdf.value.name
  const page = currentPage.value
  try {
    const fd = new FormData()
    fd.append('angle', '90')
    const r = await fetch('/api/library/' + encodeURIComponent(name) +
      '/pages/' + page + '/rotate', { method: 'POST', body: fd })
    const data = await r.json().catch(() => ({}))
    if (!r.ok || (data && data.code && data.code !== 200)) {
      throw new Error((data && data.msg) || ('HTTP ' + r.status))
    }
    imgVersion.value++
    pageOcr.value = null
    rowsData.value = null
    await loadLibrary()
    await selectCurrentPdf(name)
    await onSelectPage(page)
    ElMessage.success('已旋转 90°（该页 OCR 与台账已清，需重新识别）')
  } catch (e) {
    ElMessage.error('旋转失败: ' + e.message)
  } finally {
    processing.value.rotate = false
  }
}

async function loadPresets() {
  try {
    const r = await fetch('/api/presets')
    const data = await r.json()
    if (data && data.data && Array.isArray(data.data.presets) && data.data.presets[0]) {
      const p = data.data.presets[0]
      if (!config.value.reasoningPrompt) config.value.reasoningPrompt = p.prompt || ''
      if (!config.value.ocrPrompt) config.value.ocrPrompt = 'Read all the text in the image.'
    }
  } catch (e) { /* ignore */ }
}

// 同一 ResultView 实例内通过下拉/路由切换 PDF 时，重新加载对应卷；fullPath 覆盖 ?jump=N 跳转
watch(() => route.fullPath, async () => {
  const pdfName = decodeURIComponent(route.params.pdfName || '')
  if (pdfName && pdfName !== selectedPdfName.value) {
    await selectCurrentPdf(pdfName)
  }
  const jump = parseInt(route.query.jump)
  if (Number.isFinite(jump) && jump > 0) {
    await onJumpToPage(jump)
  }
})

onMounted(async () => {
  await loadPresets()
  await loadLibrary()
  const routeName = decodeURIComponent(route.params.pdfName || '')
  if (routeName) {
    await selectCurrentPdf(routeName)
  }
  // 处理来自总台账等的 pN 跳转参数
  const jump = parseInt(route.query.jump)
  if (Number.isFinite(jump) && jump > 0) {
    await onJumpToPage(jump)
  }
})
</script>
<style scoped>
/* === 浅色数据表盘风 — 单卷台账（左侧栏 + 源页溯源 + 台账横表） === */
.library-layout {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--sans);
  font-size: var(--type-body);
  line-height: var(--type-body-lh);
}
.main { flex: 1; display: flex; min-height: 0; border-top: var(--divider); }
.spacer { flex: 1; }

/* === 左栏 sidebar === */
.sidebar {
  width: 280px;
  min-width: 280px;
  background: #fff;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-top { padding: 14px 16px 14px; border-bottom: 1px solid var(--border); }
.sidebar-top .label {
  font-size: var(--type-label);
  color: var(--ink-mute);
  text-transform: uppercase;
  letter-spacing: var(--type-label-ls);
  margin-bottom: 8px;
}
.sidebar-top select {
  width: 100%;
  padding: 7px 9px;
  background: #fff;
  border: 1px solid var(--border-mid);
  color: var(--ink);
  font-size: 13px;
  font-family: var(--sans);
  border-radius: var(--radius-sm);
  outline: none;
}
.sidebar-top .meta {
  margin-top: 8px;
  font-size: var(--type-micro);
  color: var(--ink-mid);
  font-family: var(--mono);
  line-height: 1.5;
}
.libinfo {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-mid);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--border);
  word-break: break-all;
}
.upload-btn {
  width: 100%;
  margin-bottom: 12px;
  padding: 7px 10px;
  background: var(--accent);
  border: 1px solid var(--accent);
  color: #fff;
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.upload-btn:hover:not(:disabled) { background: var(--accent-mid); border-color: var(--accent-mid); }
.upload-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.pdf-actions { display: flex; gap: 8px; margin-top: 10px; }
.pdf-actions button {
  flex: 1;
  padding: 5px 8px;
  background: #fff;
  border: 1px solid var(--border-mid);
  border-radius: var(--radius-sm);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 12px;
  cursor: pointer;
}
.pdf-actions button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.pdf-actions button.danger:hover:not(:disabled) { border-color: var(--warn); color: var(--warn); }
.pdf-actions button:disabled { opacity: 0.5; cursor: not-allowed; }

.ledger-status {
  margin: 10px 12px;
  padding: 8px 12px;
  border-left: 3px solid var(--border);
  background: var(--bg-soft);
  font-size: 12px;
  color: var(--ink-mid);
  line-height: 1.5;
}
.ledger-status.ok { border-left-color: var(--ok); color: var(--ok); }
.ledger-status.warn { border-left-color: var(--warn); color: var(--warn); }
.ledger-status.processing { border-left-color: var(--accent); color: var(--accent); }

.page-list { flex: 1; overflow-y: auto; padding: 6px 0; }
.page-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px;
  cursor: pointer;
  border-left: 2px solid transparent;
  color: var(--ink-mid);
  font-family: var(--mono);
  font-size: 12px;
  transition: background 0.1s;
}
.page-item:hover { background: var(--bg-soft); }
.page-item.active {
  background: var(--accent-soft);
  border-left-color: var(--accent);
  color: var(--ink);
  font-weight: 600;
}
.page-item .dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #d6d2c5;
  flex-shrink: 0;
}
.page-item .dot.ocr-cached { background: var(--accent); }
.page-item .dot.selected { background: var(--warn); }

/* === 中栏 源页溯源 === */
.source {
  width: 460px;
  min-width: 340px;
  background: #fff;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.2s ease, min-width 0.2s ease;
}
.source.collapsed { width: 46px; min-width: 46px; }
.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  padding: 0 14px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--border);
  background: var(--bg-tint);
}
.source-title { font-size: 13px; font-weight: 600; font-family: var(--serif); color: var(--ink); }
.collapse-btn {
  background: #fff;
  border: 1px solid var(--border-mid);
  border-radius: var(--radius-sm);
  color: var(--ink-mid);
  font-size: 12px;
  padding: 2px 8px;
  cursor: pointer;
}
.collapse-btn:hover { border-color: var(--accent); color: var(--accent); }
.source-body { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.source-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--ink);
}
.source-bar .idx { color: var(--accent); }
.rotate-btn {
  margin-left: auto;
  padding: 3px 10px;
  background: #fff;
  border: 1px solid var(--border-mid);
  border-radius: var(--radius-sm);
  color: var(--ink);
  font-size: 12px;
  font-family: var(--sans);
  cursor: pointer;
  white-space: nowrap;
}
.rotate-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.rotate-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.source-meta {
  padding: 0 14px 8px;
  font-size: 11px;
  font-family: var(--mono);
  color: var(--ink-mid);
  line-height: 1.6;
}
.source-meta .green { color: var(--accent); }
.source-meta .yellow { color: #b58900; }
.source-img {
  flex: 1;
  overflow: auto;
  background: var(--bg);
  border: 1px solid var(--border);
  margin: 0 14px 14px;
  border-radius: var(--radius);
  display: flex;
  align-items: flex-start;
  justify-content: center;
}
.image-preview {
  position: relative;
  display: inline-block;
  max-width: 100%;
}
.image-preview img { display: block; max-width: 100%; height: auto; }
.image-preview svg {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
}
.image-preview .bbox {
  fill: transparent;
  stroke-width: 2;
  pointer-events: all;
  cursor: help;
}
.image-preview .bbox.other {
  fill: rgba(220, 220, 170, 0.10);
  stroke: #dcdcaa;
}
.image-preview .bbox.other:hover { fill: rgba(220, 220, 170, 0.25); }
.image-preview .bbox.ledger {
  fill: rgba(11, 110, 79, 0.16);
  stroke: var(--accent);
  stroke-width: 2.5;
}
.image-preview .bbox.ledger:hover { fill: rgba(11, 110, 79, 0.30); }
.image-preview .bbox.flash {
  animation: bboxFlash 10s ease-out;
}
@keyframes bboxFlash {
  0% { fill: rgba(194, 65, 12, 0.50); stroke: var(--warn); stroke-width: 4; }
  25% { fill: rgba(194, 65, 12, 0.25); }
  100% { fill: transparent; }
}

/* === 右栏 单卷台账 === */
.workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.workspace-body {
  flex: 1;
  display: flex;
  min-height: 0;
}
.content { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg); min-width: 0; }

.toolbar {
  background: #fff;
  border-bottom: 1px solid var(--border);
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 56px;
}
.toolbar .cur-page {
  font-size: var(--type-h2);
  line-height: var(--type-h2-lh);
  color: var(--ink);
  font-weight: 500;
  font-family: var(--serif);
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.toolbar .cur-page .sub {
  color: var(--ink-mid);
  font-size: 13px;
  font-family: var(--sans);
  font-weight: 400;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.toolbar button {
  background: #fff;
  border: 1px solid var(--border-mid);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 500;
  padding: 6px 14px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.toolbar button:hover:not(:disabled) { background: var(--bg-soft); border-color: var(--accent); color: var(--accent); }
.toolbar button:disabled { color: var(--ink-mute); background: var(--bg-soft); cursor: not-allowed; opacity: 0.6; }
.toolbar button.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.toolbar button.primary:hover:not(:disabled) { background: var(--accent-mid); border-color: var(--accent-mid); color: #fff; }
.toolbar button.primary:disabled { background: var(--accent-soft); border-color: var(--accent-soft); color: var(--accent); }
.toolbar button.active { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

/* === 配置抽屉 === */
.config-drawer {
  background: #fff;
  border-bottom: 1px solid var(--border);
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.25s ease;
}
.config-drawer.open { max-height: 80vh; overflow-y: auto; }
.config-inner { padding: 18px 24px 20px; }
.field { margin-bottom: 14px; }
.field.inline { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.field label {
  display: block;
  font-size: var(--type-label);
  color: var(--ink-mute);
  text-transform: uppercase;
  letter-spacing: var(--type-label-ls);
  margin-bottom: 5px;
  font-weight: 500;
}
.field.inline label { display: inline; margin-bottom: 0; text-transform: none; letter-spacing: 0; color: var(--ink); font-size: 13px; cursor: pointer; }
.field select, .field textarea, .field input[type="checkbox"] {
  font-family: var(--sans);
  font-size: 13px;
  color: var(--ink);
  background: #fff;
  border: 1px solid var(--border-mid);
  border-radius: var(--radius);
  padding: 6px 10px;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.field select { width: 100%; max-width: 480px; }
.field textarea { width: 100%; resize: vertical; min-height: 60px; line-height: 1.6; }
.field select:focus, .field textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.field input[type="checkbox"] { width: 14px; height: 14px; padding: 0; margin: 0; accent-color: var(--accent); cursor: pointer; }
.hint { font-size: var(--type-micro); color: var(--ink-mute); margin-top: 4px; font-style: italic; }

/* === 指标条 === */
.metrics-bar {
  display: flex;
  align-items: center;
  gap: 28px;
  height: 44px;
  padding: 0 20px;
  box-sizing: border-box;
  background: var(--bg-tint);
  border-bottom: 1px solid var(--border);
}
.metrics-bar .m { display: flex; align-items: baseline; gap: 6px; }
.metrics-bar .k { font-size: 11px; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.06em; }
.metrics-bar .v { font-size: 16px; font-weight: 600; font-family: var(--mono); color: var(--ink); }
.metrics-bar .v.ok { color: var(--ok); }
.metrics-bar .v.warn { color: var(--warn); }
.filter-btn {
  background: #fff;
  border: 1px solid var(--border-mid);
  border-radius: var(--radius-sm);
  color: var(--ink-mid);
  font-size: 12px;
  font-family: var(--sans);
  padding: 4px 12px;
  cursor: pointer;
}
.filter-btn.active { background: var(--warn); border-color: var(--warn); color: #fff; }

/* === 台账工具条（导出） === */
.ledger-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: #fff;
  border-bottom: 1px solid var(--border);
}
.ledger-toolbar .toolbar-title { font-size: 13px; font-weight: 600; font-family: var(--serif); color: var(--ink); }
.export-btn {
  background: #fff;
  border: 1px solid var(--border-mid);
  border-radius: var(--radius-sm);
  color: var(--ink);
  font-size: 12px;
  font-family: var(--sans);
  padding: 5px 12px;
  cursor: pointer;
}
.export-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.export-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.hidden-file-input { display: none; }

/* === 人工 Excel 比对面板 === */
.compare-panel {
  margin: 0 20px 16px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid var(--border);
  border-left: 4px solid var(--border-mid);
  max-height: 46vh;
  overflow: auto;
}
.compare-panel.status-matched { border-left-color: var(--ok); }
.compare-panel.status-diff, .compare-panel.status-field_unmatched, .compare-panel.status-record_unmatched { border-left-color: var(--warn); }
.compare-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.compare-title { font-family: var(--serif); font-size: 14px; font-weight: 700; color: var(--ink); }
.compare-badge { font-family: var(--mono); font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 10px; }
.compare-badge.ok { background: var(--warn-soft); color: var(--ok); }
.compare-badge.warn { background: var(--warn-soft); color: var(--warn); }
.compare-msg { font-size: 12.5px; line-height: 1.7; color: var(--ink-mid); }
.compare-msg.ok { color: var(--ok); font-weight: 600; }
.compare-msg.warn { color: var(--warn); }
.compare-sub { margin: 4px 0; }
.compare-meta { margin-top: 6px; font-size: 12px; color: var(--ink-mute); }
.compare-table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; table-layout: fixed; }
.compare-table th, .compare-table td { border: 1px solid var(--border-mid); padding: 6px 8px; vertical-align: top; word-break: break-all; text-align: left; }
.compare-table thead th { background: var(--bg-tint); font-weight: 600; color: var(--ink); }
.compare-table td.diff-cell { font-family: var(--mono); }

/* === 台账横表（Word 文档表格风，与总台账一致） === */
.table-scroll {
  flex: 1;
  overflow: auto;
  background: #fff;
  border: 1.5px solid #1A1A1A;
  border-radius: 0;
  margin: 16px 20px;
  min-height: 120px;
}
.master-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  line-height: 1.65;
  table-layout: fixed;
  font-family: var(--serif);
  color: var(--ink);
}
.master-table th, .master-table td {
  border: 1px solid #1A1A1A;
  padding: 7px 10px;
  vertical-align: top;
  word-break: break-all;
  line-height: 1.55;
}
.master-table thead th {
  background: #E8E5DD;
  color: var(--ink);
  font-weight: 700;
  font-size: 13px;
  font-family: var(--serif);
  text-align: center;
  text-transform: none;
  letter-spacing: 0.04em;
  border-bottom: 1.5px solid #1A1A1A;
  position: sticky;
  top: 0;
  z-index: 2;
}
.master-table tbody tr:nth-child(even) td { background: #FAF9F6; }
.master-table td.has-page { cursor: pointer; }
.master-table td.has-page:hover { background: var(--bg-tint) !important; }
.chip-list { display: flex; flex-direction: column; gap: 3px; }
.mc-chip { display: inline; padding: 0; border: none; background: transparent; }
.mc-val { font-family: var(--mono); font-size: 12.5px; color: var(--ink); cursor: text; user-select: text; }
.mc-page {
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--ink-mid);
  margin-left: 4px;
  cursor: pointer;
  white-space: nowrap;
}
.mc-page::before { content: "("; color: var(--ink-mute); }
.mc-page::after { content: ")"; color: var(--ink-mute); }
.mc-page:hover { color: var(--accent); }
.mc-chip.bad .mc-val { color: var(--warn); background: var(--warn-soft); padding: 0 3px; border-bottom: 1px dashed var(--warn); }
.mc-chip.bad .mc-page { color: var(--warn); opacity: 0.7; }
.empty-cell { color: var(--ink-mute); text-align: center; font-style: italic; }
.empty-marker { color: var(--ink-mute); }
td.cell-flash { animation: cellFlash 10s ease-out; }
@keyframes cellFlash {
  0% { background: rgba(194, 65, 12, 0.35); }
  25% { background: rgba(194, 65, 12, 0.18); }
  100% { background: transparent; }
}

/* === loading / empty === */
.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--ink-mute);
  font-size: 13px;
}
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 10px;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--ink-mute);
  padding: 40px 20px;
  text-align: center;
}
.empty-state .icon { font-size: 40px; margin-bottom: 10px; opacity: 0.45; }
.empty-state .title { font-size: 14px; color: var(--ink); margin-bottom: 4px; font-weight: 500; }
.empty-state .subtitle { font-size: 12px; color: var(--ink-mute); }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--ink-mute); }

/* === 图片放大查看弹窗 === */
.img-viewer {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.88);
  display: flex;
  flex-direction: column;
}
.viewer-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #1e1e1e;
  color: #d4d4d4;
  font-size: 13px;
  font-family: var(--sans);
  flex-shrink: 0;
}
.viewer-title {
  font-family: var(--mono);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.viewer-zoom-info {
  font-family: var(--mono);
  font-size: 12px;
  color: #9cdcfe;
  min-width: 52px;
  text-align: right;
}
.viewer-toolbar button {
  background: #333;
  border: 1px solid #555;
  color: #ddd;
  min-width: 32px;
  height: 26px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  line-height: 1;
}
.viewer-toolbar button:hover:not(:disabled) { border-color: #007acc; color: #fff; }
.viewer-toolbar button:disabled { opacity: 0.4; cursor: not-allowed; }
.viewer-toolbar .close { background: #b91c1c; border-color: #b91c1c; color: #fff; }
.viewer-stage {
  flex: 1;
  overflow: hidden;
  position: relative;
  cursor: grab;
}
.viewer-stage.dragging { cursor: grabbing; }
.viewer-canvas {
  position: absolute;
  top: 0; left: 0;
  transform-origin: 0 0;
  will-change: transform;
}
.viewer-canvas img {
  display: block;
  max-width: 88vw;
  max-height: 84vh;
  width: auto;
  height: auto;
  user-select: none;
  -webkit-user-drag: none;
}
.viewer-canvas svg {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
}
.viewer-canvas .bbox { fill: transparent; stroke-width: 2; pointer-events: none; }
.viewer-canvas .bbox.other { fill: rgba(220, 220, 170, 0.12); stroke: #dcdcaa; }
.viewer-canvas .bbox.ledger { fill: rgba(11, 110, 79, 0.20); stroke: var(--accent); stroke-width: 2.5; }

/* 源页栏「放大」按钮（与旋转按钮并排，靠右） */
.source-bar .zoom-btn {
  margin-left: auto;
  padding: 3px 10px;
  background: #fff;
  border: 1px solid var(--border-mid);
  border-radius: var(--radius-sm);
  color: var(--ink);
  font-size: 12px;
  font-family: var(--sans);
  cursor: pointer;
  white-space: nowrap;
}
.source-bar .zoom-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.source-bar .zoom-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.source-bar .rotate-btn { margin-left: 0; }
</style>

<style scoped>
.review-note { padding: 10px 14px; border: 1px solid var(--border); background: var(--bg-surface); line-height: 1.8; }
.review-note button { margin: 2px 5px; cursor: pointer; }
</style>
