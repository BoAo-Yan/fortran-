# -*- coding: utf-8 -*-
"""生成互动式复习页（整段逐行注释版）
   - 每一行都有注释框（题面要求"整个代码的注释"）
   - 判定：72 个手工考点行用精确关键词；其余行按语句类型给通用答案
"""
import json, os, re, sys

HERE = r"E:\Fortran_Lab\复习"
OLD = os.path.join(HERE, "fortran_review.html")
OUT = os.path.join(HERE, "fortran_quiz.html")

sys.path.insert(0, HERE)
from quiz_data import STEMS


def norm(x):
    return re.sub(r"\s+", "", x).lower()


def strip_comments(code):
    ls = [l for l in code.split("\n") if not re.match(r"^\s*!", l)]
    while ls and not ls[0].strip():
        ls.pop(0)
    return ls


# ---------------------------------------------------------------- 通用规则
def classify(raw):
    """对没有手工考点的行，按语句类型给出参考答案 + 关键词；返回 None 表示不给注释框"""
    s = raw.strip()
    if not s:
        return None
    if re.match(r"^program\b", s, re.I):
        return None
    if re.match(r"^end\s*$", s, re.I):          # 程序最后那个 end
        return None
    if re.match(r"^implicit\s+none", s, re.I):
        return ("关闭隐式类型：所有变量必须先声明，否则编译报错", ["隐式", "声明", "先声明", "严格"], 1)
    if re.match(r"^(real|integer|logical|character|double\s*precision)\b", s, re.I):
        return ("类型说明语句：声明变量（或常量）及其类型", ["声明", "定义", "变量", "类型"], 1)
    if re.match(r"^read\b", s, re.I):
        return ("从键盘读入数据（表控格式，* 表示自由格式）", ["输入", "读入", "键盘", "读"], 1)
    if re.match(r"^open\b", s, re.I):
        return ("打开文件：指定通道号和文件名", ["打开", "文件", "通道"], 1)
    if re.match(r"^close\b", s, re.I):
        return ("关闭文件（缓冲区数据落盘）", ["关闭", "文件"], 1)
    if re.match(r"^write\s*\(\s*10", s, re.I):
        return ("向文件写出一条记录（通道 10 就是 open 里那个文件）", ["写", "文件", "输出", "通道"], 1)
    if re.match(r"^print\b", s, re.I):
        return ("输出到屏幕（表控格式）", ["输出", "打印", "屏幕", "显示"], 1)
    if re.match(r"^do\b", s, re.I):
        rest = s[2:].strip()
        if rest:
            return ("do 循环开始：" + rest + "（步长默认 1）", ["循环", "do", "遍历", "重复"], 1)
        return ("do 循环开始（不带循环变量，靠 exit 退出）", ["循环", "无限", "exit"], 1)
    if re.match(r"^end\s*do\b", s, re.I):
        return ("循环体结束，控制回到 do 语句", ["循环", "结束", "回到"], 1)
    if re.match(r"^else\s+if\b", s, re.I):
        return ("多分支：上一个条件不成立时再判断这一个", ["否则", "再判断", "分支", "互斥"], 1)
    if re.match(r"^else\s*$", s, re.I):
        return ("否则分支：前面条件都不成立时走这里（兜底）", ["否则", "兜底", "都不成立"], 1)
    if re.match(r"^if\s*\(", s, re.I):
        return ("条件判断：条件成立则执行下面的语句", ["判断", "条件", "成立", "分支", "选择"], 1)
    if re.match(r"^end\s*if\b", s, re.I):
        return ("选择结构结束", ["结束", "选择", "if"], 1)
    if re.match(r"^call\b", s, re.I):
        return ("调用子例行程序（用 call）", ["调用", "call", "子程序"], 1)
    if re.match(r"^subroutine\b", s, re.I):
        return ("子例行程序定义：没有返回值，结果靠参数带回", ["子例行", "子程序", "定义", "参数"], 1)
    if re.match(r"^(real\s+|integer\s+)?function\b", s, re.I):
        return ("函数子程序定义：有返回值，给函数名赋值即返回", ["函数", "子程序", "定义", "返回"], 1)
    if re.match(r"^end\s*(subroutine|function)\b", s, re.I):
        return ("子程序结束", ["结束", "子程序"], 1)
    if re.match(r"^exit\b", s, re.I):
        return ("跳出当前循环", ["跳出", "退出", "循环"], 1)
    if "=" in s:
        return ("赋值语句：把等号右边的计算结果存进左边变量", ["赋值", "计算", "存", "得到", "求"], 1)
    return ("执行语句", ["执行", "语句"], 1)


# ---------------------------------------------------------------- 组织题库
s = open(OLD, encoding="utf-8").read()
data = json.loads(re.search(r"const DATA = (\[.*?\]);\s*\n", s, re.S).group(1))

problems = []
for it in data:
    lines = strip_comments(it["code"])
    spec = {}
    for st in STEMS.get(it["id"], []):
        pat = norm(st[0])
        hit = [i for i, L in enumerate(lines) if pat in norm(L)]
        if not hit:
            problems.append((it["id"], st[0] + "  <找不到>"))
            continue
        if len(hit) > 1 and len({norm(lines[i]) for i in hit}) > 1:
            problems.append((it["id"], st[0] + "  <多行匹配>"))
        i = hit[0]
        spec[i] = {"ref": st[1], "kw": st[2], "need": st[3], "key": True}

    quiz = []
    for i, raw in enumerate(lines):
        if i in spec:
            q = spec[i]
        else:
            c = classify(raw)
            if c is None:                      # program 行、最后的 end、空行：只显示不提问
                quiz.append({"no": i + 1, "raw": raw.strip(), "ask": False})
                continue
            q = {"ref": c[0], "kw": c[1], "need": c[2], "key": False}
        quiz.append({"no": i + 1, "raw": raw.strip(), "ask": True, "key": q["key"],
                     "ref": q["ref"], "kw": q["kw"], "need": q["need"]})
    it["quiz"] = quiz
    it["nask"] = sum(1 for q in quiz if q["ask"])
    it["nkey"] = sum(1 for q in quiz if q.get("key"))

if problems:
    print("!! 校验问题：")
    for p in problems:
        print("   ", p[0], "|", p[1])

data = [d for d in data if d["nask"]]
total_q = sum(d["nask"] for d in data)
total_k = sum(d["nkey"] for d in data)
print(f"程序 {len(data)} 段，注释行 {total_q} 个（其中精判考点行 {total_k} 个）")
print("平均每段 {:.1f} 行".format(total_q / len(data)))

DATA_JS = json.dumps(data, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FORTRAN · 整段程序注释训练</title>
<style>
  :root{
    --bg:#060a11;--panel:rgba(11,19,30,.78);--line:rgba(56,189,248,.20);
    --txt:#c9dcea;--dim:#6d8ba1;--cyan:#22d3ee;--ok:#34d399;--bad:#fb7185;
  }
  *{box-sizing:border-box}
  body{
    margin:0;padding:24px 16px 80px;color:var(--txt);
    font:15px/1.7 ui-sans-serif,system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
    background:
      radial-gradient(900px 460px at 50% -12%, rgba(34,211,238,.15), transparent 62%),
      repeating-linear-gradient(0deg, rgba(56,189,248,.045) 0 1px, transparent 1px 34px),
      repeating-linear-gradient(90deg, rgba(56,189,248,.045) 0 1px, transparent 1px 34px),
      var(--bg);
    background-attachment:fixed;
  }
  .wrap{max-width:900px;margin:0 auto}
  h1{font-size:19px;margin:0 0 6px;font-weight:600;letter-spacing:1px;color:#e6f6ff}
  h1 .sys{font-size:11px;letter-spacing:2px;color:var(--cyan);border:1px solid rgba(34,211,238,.5);
    border-radius:4px;padding:2px 7px;margin-right:10px;vertical-align:3px}
  .status{font-size:12px;color:var(--dim);margin:0 0 20px;letter-spacing:.4px}
  .status i{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ok);
    box-shadow:0 0 8px var(--ok);margin-right:6px;vertical-align:1px}
  nav{display:flex;gap:10px;border-bottom:1px solid var(--line);padding-bottom:13px;margin-bottom:20px}
  nav button{font:inherit;font-size:14px;padding:7px 16px;background:transparent;color:var(--dim);
    border:1px solid var(--line);border-radius:6px;cursor:pointer;letter-spacing:.5px}
  nav button:hover{color:var(--cyan);border-color:rgba(34,211,238,.5)}
  nav button.on{color:#03141a;background:var(--cyan);border-color:var(--cyan);font-weight:600}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:16px}
  .meta{font-size:12px;color:var(--dim);letter-spacing:.4px;margin-bottom:12px}
  .meta b{color:var(--cyan);font-weight:600}
  .blk{border-radius:6px;margin:0 0 2px}
  .row{display:flex;align-items:baseline;gap:10px;padding:2px 6px;
    font:13px/1.62 "Cascadia Mono",Consolas,"Courier New",monospace;border-radius:5px}
  .row .no{color:#3a566b;width:2.1em;text-align:right;flex:none;user-select:none}
  .row .src{white-space:pre;color:#b6cfe1}
  .blk.key .row{background:rgba(34,211,238,.07);border-left:2px solid var(--cyan)}
  .blk.key .row .src{color:#d7f4fb}
  .tag{font-size:10px;letter-spacing:1px;color:#06222b;background:var(--cyan);
    border-radius:3px;padding:1px 5px;flex:none;font-family:inherit}
  .qline{display:flex;gap:8px;margin:4px 0 10px 3.2em}
  input{flex:1;font:13.5px/1.6 inherit;color:#dff3ff;background:rgba(4,10,18,.85);
    border:1px solid rgba(56,189,248,.20);border-radius:5px;padding:6px 10px;outline:none}
  input:focus{border-color:rgba(34,211,238,.6);box-shadow:0 0 0 2px rgba(34,211,238,.10)}
  input::placeholder{color:#3a566b}
  .btn{font:13px/1 inherit;padding:7px 13px;border-radius:5px;cursor:pointer;white-space:nowrap;
    background:transparent;color:#8fd8ec;border:1px solid rgba(34,211,238,.42)}
  .btn:hover{background:rgba(34,211,238,.12)}
  .btn.main{background:rgba(34,211,238,.14);color:#bdeffb;border-color:rgba(34,211,238,.6)}
  .res{font-size:12.5px;margin:0 0 10px 3.2em;line-height:1.7;display:none}
  .res.show{display:block}
  .res .ok{color:var(--ok)}.res .no{color:var(--bad)}
  .res .ref{color:#8fb0c6;display:block}
  .res .hit{color:#6f8fa5;font-size:12px;display:block}
  .bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:16px;
    border-top:1px dashed rgba(56,189,248,.16);padding-top:14px}
  .bar label{font-size:12.5px;color:var(--dim);display:flex;align-items:center;gap:6px;cursor:pointer}
  .score{margin-left:auto;font-size:13px;color:var(--dim)}
  .score b{color:var(--cyan);font-size:15px}
  .hide{display:none}
  .foot{margin-top:30px;text-align:center;font-size:12px;color:#3f5c72}
  .card.q .qtext{font-size:15.5px;margin:4px 0 2px;color:#e2f2fb}
  .self{display:flex;gap:8px;margin-top:10px}
  .card.self-ok{border-color:rgba(52,211,153,.55)}
  .card.self-bad{border-color:rgba(251,113,133,.55)}
  pre{background:#080f19;border:1px solid rgba(56,189,248,.14);border-radius:7px;padding:12px 14px;
    overflow:auto;font:12.5px/1.6 "Cascadia Mono",Consolas,monospace;color:#bcd4e6}
</style>
</head>
<body>
<div class="wrap">
  <h1><span class="sys">SYS</span>FORTRAN · 整段程序注释训练</h1>
  <p class="status"><i></i>ONLINE　__N__ 段程序 / __Q__ 个注释行（__K__ 行精判）　判定：关键词匹配，不看字数看说没说到点子上</p>

  <nav>
    <button id="t1" class="on" onclick="mode(1)">01 · 逐行注释</button>
    <button id="t2" onclick="mode(2)">02 · 抽 4 题手写</button>
  </nav>

  <section id="s1">
    <div class="card">
      <div class="meta" id="m1"></div>
      <div id="body"></div>
      <div class="bar">
        <button class="btn main" onclick="judgeAll()">全部判定</button>
        <button class="btn" onclick="next()">换一段</button>
        <label><input type="checkbox" id="onlyKey" onchange="toggleKey()" style="width:auto;flex:none"> 只看精判行</label>
        <span class="score" id="score">— 未判定 —</span>
      </div>
    </div>
  </section>

  <section id="s2" class="hide">
    <div class="bar" style="border:0;padding:0;margin:0 0 16px">
      <button class="btn main" onclick="draw()">随机抽 4 题（跨报告）</button>
      <span class="score" id="hint">点一下开始本轮</span>
    </div>
    <div id="list"></div>
  </section>

  <p class="foot">题面与标准答案取自 E:\Fortran_Lab\work\report*　·　离线单文件</p>
</div>

<script>
const DATA = __DATA__;
let cur=null, last=-1;

function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function norm(x){return x.replace(/\s+/g,"").toLowerCase().replace(/[\s，,。.；;：:、（）()【】\[\]"'“”‘’]/g,"");}

function mode(k){
  document.getElementById("s1").classList.toggle("hide",k!==1);
  document.getElementById("s2").classList.toggle("hide",k!==2);
  document.getElementById("t1").classList.toggle("on",k===1);
  document.getElementById("t2").classList.toggle("on",k===2);
  if(k===1 && !cur) next();
}

function next(){
  let i; do{ i=Math.floor(Math.random()*DATA.length); }while(DATA.length>1 && i===last);
  last=i; cur=DATA[i];
  document.getElementById("m1").innerHTML =
    '<b>报告 '+cur.rep+' · 第 '+cur.no+' 题</b>　'+cur.title+
    '　<span style="color:#3f5c72">／ 共 '+cur.nask+' 行要注释，其中精判 '+cur.nkey+' 行（标 CORE）</span>';

  cur.quiz.forEach(q=>q.ok=null);
  document.getElementById("body").innerHTML = cur.quiz.map((q,k)=>{
    const row = '<div class="row"><span class="no">'+q.no+'</span><span class="src">'+esc(q.raw)+
                '</span>'+(q.key?'<span class="tag">CORE</span>':'')+'</div>';
    if(!q.ask) return '<div class="blk" id="b'+k+'">'+row+'</div>';
    return '<div class="blk '+(q.key?'key':'')+'" id="b'+k+'">'+row+
      '<div class="qline"><input id="i'+k+'" placeholder="注释这一行…" onkeydown="if(event.key===\'Enter\')judge('+k+')">'+
      '<button class="btn" onclick="judge('+k+')">判定</button></div>'+
      '<div class="res" id="r'+k+'"></div></div>';
  }).join("");
  document.getElementById("score").textContent = "— 未判定 —";
  document.getElementById("onlyKey").checked = false;
  const f = document.getElementById("i0"); if(f) f.focus();
}

function judge(k){
  const q = cur.quiz[k];
  const raw = (document.getElementById("i"+k).value||"").trim();
  const res = document.getElementById("r"+k);
  if(!raw){
    res.className="res show";
    res.innerHTML='<span class="no">✗</span> 先写点什么再判定。';
    return false;
  }
  const t = norm(raw);
  const hit = q.kw.filter(x => t.includes(norm(x)));
  const ok = hit.length >= q.need;
  q.ok = ok;
  res.className="res show";
  res.innerHTML = (ok?'<span class="ok">✓ 正确</span>':'<span class="no">✗ 没说到点子上</span>') +
    '　<span class="hit">命中：'+(hit.length?hit.join("、"):"（无）")+'　需 ≥'+q.need+' 个</span>' +
    '<span class="ref">参考：'+q.ref+'</span>';
  update();
  return ok;
}

function update(){
  const asked = cur.quiz.filter(q=>q.ask);
  const done = asked.filter(q=>q.ok===true||q.ok===false).length;
  const ok = asked.filter(q=>q.ok===true).length;
  const el = document.getElementById("score");
  if(!done){ el.textContent="— 未判定 —"; return; }
  el.innerHTML = '已注 <b>'+done+'</b>/'+cur.nask+'　正确 <b>'+ok+'</b>';
}
function judgeAll(){
  cur.quiz.forEach((q,k)=>{
    if(!q.ask) return;
    const el = document.getElementById("i"+k);
    if(el && (el.value||"").trim()) judge(k);
  });
}
function toggleKey(){
  const on = document.getElementById("onlyKey").checked;
  cur.quiz.forEach((q,k)=>{ if(!q.key) document.getElementById("b"+k).classList.toggle("hide",on); });
}

/* ---------- 题型二 ---------- */
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
let round=0;
function draw(){
  const by={}; DATA.forEach(d=>{(by[d.rep]=by[d.rep]||[]).push(d);});
  const reps = shuffle(Object.keys(by)).slice(0,4);
  const pick = reps.map(r=>by[r][Math.floor(Math.random()*by[r].length)]);
  round++;
  document.getElementById("hint").textContent = "第 "+round+" 轮："+pick.map(d=>"报告"+d.rep).join(" / ");
  document.getElementById("list").innerHTML = pick.map((d,i)=>`
    <div class="card q" id="c${i}">
      <div class="meta"><b>${i+1}</b>　报告 ${d.rep} · 第 ${d.no} 题　${d.title}</div>
      <div class="qtext">${d.q}</div>
      <div class="self">
        <button class="btn" onclick="rev(${i})">看标准答案</button>
        <button class="btn" onclick="mark(${i},1)">我写对了</button>
        <button class="btn" onclick="mark(${i},0)">没写对</button>
      </div>
      <div class="res" id="a${i}">
        <div style="margin:10px 0 6px;color:var(--dim);font-size:12px">标准程序</div>
        <pre>${d.code.split("\n").map((l,k)=>esc(l)).join("\n")}</pre>
        <div style="margin:8px 0 4px;color:var(--dim);font-size:12px">要点</div>
        <ul style="margin:0;padding-left:20px">${d.pts.map(p=>"<li>"+p+"</li>").join("")}</ul>
      </div>
    </div>`).join("");
}
function rev(i){document.getElementById("a"+i).classList.toggle("show");}
function mark(i,ok){
  const c=document.getElementById("c"+i);
  c.classList.remove("self-ok","self-bad");
  c.classList.add(ok?"self-ok":"self-bad");
}

next();
</script>
</body>
</html>
"""

HTML = HTML.replace("__N__", str(len(data)))
HTML = HTML.replace("__Q__", str(total_q))
HTML = HTML.replace("__K__", str(total_k))
HTML = HTML.replace("__DATA__", DATA_JS)
open(OUT, "w", encoding="utf-8").write(HTML)
print("wrote", OUT, len(HTML.encode("utf-8")), "bytes")
