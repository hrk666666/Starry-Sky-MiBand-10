#!/usr/bin/env node
/**
 * regression-starry.mjs — 《星空列车与白的旅行》内容包端到端回归
 *
 * 用 createMemoryAdapter 的 fs 模式加载仓库真实 game.txt + src/common/scn/chunk*.txt，
 * 验证：
 *   - 全流程无崩溃、无未解析跳转（全部 17 个场景块可达）
 *   - 两条路线（全选第 1 项 / 全选最后一项）均能到达结局（gameend）
 *   - 4 组选项全部被访问
 *   - 快进跳选项不串线、正确结束
 *
 * 运行：node tests/regression-starry.mjs
 */
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, "..")
const ESM = path.join(__dirname, "_esm")

// 复制引擎源码为 ESM（与 run-tests.mjs 相同机制）
fs.mkdirSync(ESM, { recursive: true })
for (const f of fs.readdirSync(path.join(ROOT, "src", "engine"))) {
  if (f.endsWith(".js")) {
    let src = fs.readFileSync(path.join(ROOT, "src", "engine", f), "utf-8")
    src = src.replace(/from "\.\/([\w-]+)\.js"/g, 'from "./$1.mjs"')
    fs.writeFileSync(path.join(ESM, f.replace(/\.js$/, ".mjs")), src)
  }
}

const { createMemoryAdapter } = await import(`./_esm/platformAdapter.mjs`)
const { createVnEngine } = await import(`./_esm/index.mjs`)

const adapter = createMemoryAdapter({}, null, { fs, baseDir: ROOT })
const cfg = await adapter.readConfig()
console.log(`内容包: ${cfg.title} v${cfg.version}，${cfg.scenarios.main.length} 个场景块`)

let pass = 0
let fail = 0
function check(name, cond, extra = "") {
  if (cond) {
    pass++
    console.log(`  ✓ ${name}`)
  } else {
    fail++
    console.log(`  ✗ ${name} ${extra}`)
  }
}

async function walkRoute(choicePolicy, label, defaultPick = () => 0) {
  let state = null
  const engine = await createVnEngine({
    adapter,
    options: { saveSlots: 4 },
    onState: (s) => { state = s }
  })
  const rt = engine.runtime
  await rt.load("001")
  let steps = 0
  const visited = new Set()
  const optionsSeen = []
  const perScnCount = {}
  while (!state.ended && steps < 800000) {
    steps++
    visited.add(state.scnId)
    if (state.showOptions) {
      const opts = state.options || []
      if (opts.length === 0) {
        console.log(`  [${label}] 空选项 @ ${state.scnId}:${state.lineIndex} — 强制推进`)
        rt.advance()
      } else {
        optionsSeen.push(opts.map((o) => o.text))
        const n = perScnCount[state.scnId] = (perScnCount[state.scnId] || 0)
        let idx = defaultPick(opts.length)
        if (choicePolicy && choicePolicy[state.scnId]) {
          const want = choicePolicy[state.scnId][n]
          if (want !== undefined) idx = Math.min(want, opts.length - 1)
        }
        if (opts[idx] && opts[idx].enabled === false) {
          const alt = opts.findIndex((o) => o.enabled !== false)
          if (alt !== -1) idx = alt
        }
        perScnCount[state.scnId]++
        rt.choose(idx)
      }
    } else if (state.isTextComplete) {
      rt.advance()
    } else {
      rt.markTextComplete()
    }
    await Promise.resolve()
  }
  return { state, steps, visited, optionsSeen }
}

async function walkRouteWithSkips(choicePolicy, label, skipEvery = 400) {
  let state = null
  const engine = await createVnEngine({
    adapter,
    options: { saveSlots: 4 },
    onState: (s) => { state = s }
  })
  const rt = engine.runtime
  await rt.load("001")
  let steps = 0
  const visited = new Set()
  const perScnCount = {}
  while (!state.ended && steps < 1000000) {
    steps++
    visited.add(state.scnId)
    if (state.showOptions) {
      const opts = state.options || []
      if (opts.length === 0) { rt.advance(); continue }
      const n = perScnCount[state.scnId] = (perScnCount[state.scnId] || 0)
      let idx = 0
      if (choicePolicy && choicePolicy[state.scnId]) {
        const want = choicePolicy[state.scnId][n]
        if (want !== undefined) idx = Math.min(want, opts.length - 1)
      }
      perScnCount[state.scnId]++
      rt.choose(idx)
    } else if (state.isTextComplete) {
      if (steps % skipEvery === 0 && !state.ended) {
        rt.skipToNextSelect()
      } else {
        rt.advance()
      }
    } else {
      rt.markTextComplete()
    }
    await Promise.resolve()
  }
  return { state, steps, visited }
}

// ---- 路线 1：全选第 1 项 ----
console.log(`\n== 路线 1（全选第 1 项）==`)
const r1 = await walkRoute(null, "路线1")
check("路线 1 到达结局（ended）", r1.state.ended,
  `steps=${r1.steps} scnId=${r1.state.scnId}`)
check("路线 1 全部 17 个场景块可达", r1.visited.size === 17,
  `实际 ${r1.visited.size} 块: ${[...r1.visited].join(",")}`)
check("路线 1 访问到全部 4 组选项", r1.optionsSeen.length === 4,
  `实际 ${r1.optionsSeen.length} 组`)
console.log(`  路线 1 推进 ${r1.steps} 步，选项：`)
for (const o of r1.optionsSeen) console.log(`    - ${o.join(" / ")}`)

// ---- 路线 2：全选最后一项 ----
console.log(`\n== 路线 2（全选最后一项）==`)
const r2 = await walkRoute(null, "路线2", (n) => n - 1)
check("路线 2 到达结局（ended）", r2.state.ended,
  `steps=${r2.steps} scnId=${r2.state.scnId}`)
check("路线 2 全部 17 个场景块可达", r2.visited.size === 17,
  `实际 ${r2.visited.size} 块`)
check("路线 2 访问到全部 4 组选项", r2.optionsSeen.length === 4,
  `实际 ${r2.optionsSeen.length} 组`)

// ---- 路线 3：快进跳选项 ----
console.log(`\n== 路线 3（快进跳选项）==`)
const r3 = await walkRouteWithSkips(null, "全选1+快进", 300)
check("快进路线到达结局（ended）", r3.state.ended,
  `steps=${r3.steps} scnId=${r3.state.scnId}`)
check("快进路线全部 17 个场景块可达", r3.visited.size === 17,
  `实际 ${r3.visited.size} 块`)

// ---- 汇总 ----
console.log(`\n========== 结果 ==========`)
console.log(`通过 ${pass} / ${pass + fail}`)
if (fail > 0) process.exit(1)
