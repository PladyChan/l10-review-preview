from pathlib import Path
import html
import re
import shutil


FILES = [
    "source/L10_测评对比草稿.md",
]

DISPLAY_TITLES = {
    "source/L10_测评对比草稿.md": "L10",
}


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def parse_table(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        row = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
        rows.append(row)
        i += 1
    if len(rows) < 2:
        return "", start
    header = rows[0]
    body = rows[2:] if all(set(c.replace(":", "").replace("-", "")) == set() for c in rows[1]) else rows[1:]
    out = ["<table><thead><tr>"]
    out.extend(f"<th>{inline(c)}</th>" for c in header)
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>")
        out.extend(f"<td>{inline(c)}</td>" for c in row)
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out), i


def md_to_html(md: str):
    lines = md.splitlines()
    out = []
    in_ul = False
    in_ol = False
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            i += 1
            continue

        if line.startswith("|"):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            table, next_i = parse_table(lines, i)
            out.append(table)
            i = next_i
            continue

        if line.startswith("#"):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            level = min(len(line) - len(line.lstrip("#")), 4)
            text = line[level:].strip()
            out.append(f'<h{level}>{inline(text)}</h{level}>')
            i += 1
            continue

        if line.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(line[2:].strip())}</li>")
            i += 1
            continue

        if re.match(r"^\d+\.\s+", line):
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            item_text = re.sub(r"^\d+\.\s+", "", line)
            out.append(f"<li>{inline(item_text)}</li>")
            i += 1
            continue

        if line.startswith(">"):
            out.append(f"<blockquote>{inline(line.lstrip('>').strip())}</blockquote>")
        else:
            out.append(f"<p>{inline(line)}</p>")
        i += 1

    if in_ul:
        out.append("</ul>")
    if in_ol:
        out.append("</ol>")
    return "\n".join(out)


sections = []
for file in FILES:
    path = Path(file)
    if path.exists():
        title = DISPLAY_TITLES.get(file, path.stem.replace("L10_", "").replace("_", " "))
        sections.append((title, file, md_to_html(path.read_text(encoding="utf-8"))))


def table(headers, rows):
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{inline(str(cell))}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def note_grid(items):
    return '<div class="note-grid">' + "".join(
        f'<div class="note"><b>{html.escape(title)}</b><p>{inline(body)}</p></div>'
        for title, body in items
    ) + "</div>"


sensor_formats = [
    ("one-inch", "一英寸", 13.2, 8.8, "typical"),
    ("l10-used", "L10 可用", 15.2, 11.4, "estimated"),
    ("m43", "标准 M43", 17.3, 13.0, "standard"),
    ("aps-c", "APS-C", 23.5, 15.6, "typical"),
    ("full-frame", "全画幅", 36.0, 24.0, "standard"),
]

l10_aspect_ratios = [
    ("4:3", "5184 x 3888", 15.2, 11.4, "默认照片比例"),
    ("3:2", "5392 x 3600", 15.8098765432, 10.5555555556, "更接近全幅 / APS-C 观看习惯"),
    ("16:9", "5632 x 3168", 16.5135802469, 9.2888888889, "更宽，仍达不到标准 M43 全宽"),
    ("1:1", "3888 x 3888", 11.4, 11.4, "方形构图"),
]


def sensor_visual():
    boxes = []
    buttons = []
    rows = []

    for sensor_id, label, width, height, note in sensor_formats:
        area = width * height
        rows.append((label, f"{width:g} x {height:g} mm", f"{area:.2f} mm²", "推算" if note == "estimated" else "常用规格"))
        boxes.append(
            f'<div class="sensor-css-box{" is-active is-compare-a" if sensor_id == "m43" else ""}{" is-compare-b" if sensor_id == "l10-used" else ""}" '
            f'data-sensor-box="{sensor_id}" style="--w-mm:{width:g}; --h-mm:{height:g}; --z:{1000 - int(area)};">'
            f'<span data-sensor-label="{sensor_id}">{html.escape(label)} · {width:g} x {height:g}</span></div>'
        )
        marker = "A" if sensor_id == "m43" else "B" if sensor_id == "l10-used" else ""
        active = sensor_id == "m43"
        buttons.append(
            f'<button class="sensor-button{" is-active is-compare-a" if active else ""}{" is-compare-b" if sensor_id == "l10-used" else ""}" type="button" '
            f'data-sensor-target="{sensor_id}" aria-pressed="{"true" if active else "false"}" '
            f'data-name="{html.escape(label)}" data-size="{width:g} x {height:g} mm" data-area="{area:.2f}" '
            f'data-note="{"按 20.4MP / 26.5MP 推算" if note == "estimated" else "传感器规格口径"}">'
            f'<em data-compare-marker>{marker}</em><strong>{html.escape(label)}</strong><span>{width:g} x {height:g} mm</span></button>'
        )

    return f"""
  <div class="sensor-controls" aria-label="选择传感器规格">
    {''.join(buttons)}
  </div>
  <figure class="sensor-figure" data-sensor-visual>
    <div class="sensor-css-stage" role="img" aria-label="一英寸、L10 可用、标准 M43、APS-C、全画幅传感器尺寸比例图">
      <div class="sensor-css-scale" aria-hidden="true"><span>0</span><span>36mm</span></div>
      {''.join(boxes)}
    </div>
    <figcaption>按毫米尺寸等比例显示。L10 可用面积按 20.4MP 有效照片 / 26.5MP 总像素，从标准 M43 面积推算；不是官方公布的物理尺寸。</figcaption>
  </figure>
  <div class="sensor-readout" aria-live="polite">
    <strong data-sensor-readout-name>L10 可用</strong>
    <span data-sensor-readout-size>15.2 x 11.4 mm</span>
    <span data-sensor-readout-area>173 mm²</span>
    <span data-sensor-readout-note>按 20.4MP / 26.5MP 推算</span>
  </div>
  <div class="sensor-compare" aria-label="传感器面积对比工具">
    <div><span>A</span><strong data-compare-a-name>标准 M43</strong></div>
    <div><span>B</span><strong data-compare-b-name>L10 可用</strong></div>
    <output data-compare-output>A（标准 M43）是 B（L10 可用）的 1.30 倍，面积大约多 30%。</output>
  </div>
  <div class="area-summary">
    <p><strong>面积换算结论：</strong>全画幅约是 APS-C 的 2.36 倍；APS-C 约是 L10 可用面积的 2.12 倍；APS-C 约是标准 M43 的 1.63 倍；L10 可用面积约是一英寸的 1.49 倍。</p>
    <p>全画幅：36 x 24 = 864mm²；APS-C：23.5 x 15.6 = 366.6mm²；标准 M43：17.3 x 13 = 224.9mm²；L10 可用：15.2 x 11.4 = 173.28mm²；一英寸：13.2 x 8.8 = 116.16mm²。</p>
    <p>L10 的传感器位置其实很清楚：它比一英寸大一档，提升有限；比标准 M43 小一圈；和 APS-C 差距明显；和全画幅差距更大。L10 的成立点，是 24-75mm 光学变焦、EVF、Real Time LUT 和完整相机体验。</p>
  </div>
  {table(["规格", "尺寸", "面积", "口径"], rows)}
"""


sensor_module = f"""
<aside class="insert-module" id="visual-sensor">
  <div class="module-kicker">VISUAL TOOL / FORMAT</div>
  <h3>画幅对比工具：L10 可用面积小于标准 M43 全面积</h3>
  <p>这块只讲尺寸关系，不直接等同于最终画质。L10 用的是 4/3 多画幅路线，但可用成像面积要和标准 M43 分开看。</p>
  {sensor_visual()}
</aside>
"""


def aspect_ratio_visual():
    standard_m43_area = 17.3 * 13.0
    standard_m43_diag = (17.3 ** 2 + 13.0 ** 2) ** 0.5
    base_area = l10_aspect_ratios[0][2] * l10_aspect_ratios[0][3]
    max_diag = max((width ** 2 + height ** 2) ** 0.5 for _, _, width, height, _ in l10_aspect_ratios)
    boxes = []
    controls = []
    rows = []
    for idx, (ratio, resolution, width, height, note) in enumerate(l10_aspect_ratios):
        pixels = int(resolution.split(" x ")[0]) * int(resolution.split(" x ")[1])
        diag = (width ** 2 + height ** 2) ** 0.5
        area = width * height
        aspect_id = ratio.replace(":", "")
        active = idx == 0
        controls.append(
            f'<button class="aspect-button{" is-active" if active else ""}" type="button" data-aspect-target="{aspect_id}" '
            f'aria-pressed="{"true" if active else "false"}" data-name="{ratio}" data-size="{width:.2f} x {height:.2f} mm" '
            f'data-area="{area:.2f}" data-resolution="{resolution}" data-note="{html.escape(note)}">'
            f'<strong>{ratio}</strong><span>{width:.2f} x {height:.2f}mm</span></button>'
        )
        boxes.append(
            f'<div class="aspect-css-box aspect-{aspect_id}{" is-active" if active else ""}" '
            f'data-aspect-box="{aspect_id}" style="--w-mm:{width:.5f}; --h-mm:{height:.5f}; --z:{20 + idx};">'
            f'<span>{ratio}</span></div>'
        )
        rows.append(
            (
                ratio,
                resolution,
                f"{pixels / 1000000:.1f}MP",
                f"{width:.2f} x {height:.2f} mm",
                f"{area:.2f} mm²",
                f"{diag:.2f} mm",
                f"{area / base_area * 100:.1f}%",
                f"{area / standard_m43_area * 100:.1f}%",
            )
        )

    return f"""
<aside class="insert-module aspect-module" id="visual-aspect">
  <div class="module-kicker">ASPECT TOOL / L10</div>
  <h3>内置比例面积示意：四种比例各自取景</h3>
  <p>这张图画 L10 自己的四个内置比例，并加上标准 M43 的 17.3 x 13.0mm 外框作为参照。尺寸按有效像素和同像素密度估算；16:9 比 4:3 更宽，但仍达不到标准 M43 全宽。</p>
  <div class="aspect-controls" aria-label="选择 L10 内置比例">
    {''.join(controls)}
  </div>
  <figure class="aspect-figure">
    <div class="aspect-css-stage" role="img" aria-label="L10 四个内置画幅比例示意">
      <div class="aspect-image-circle" style="--circle-mm:{max_diag:.5f};"><span>像场圆 约 {max_diag:.2f}mm</span></div>
      <div class="aspect-m43-frame"><span>标准 M43 17.3 x 13.0mm</span></div>
      {''.join(boxes)}
    </div>
    <figcaption>虚线外框是标准 M43 面积参照；圆形是覆盖这些比例所需的最小像场圆，按最大对角线约 {max_diag:.2f}mm 绘制，标准 M43 对角线约 {standard_m43_diag:.2f}mm。点击上方比例按钮会高亮对应画幅，并更新下方读数。</figcaption>
  </figure>
  <div class="aspect-readout" aria-live="polite">
    <strong data-aspect-readout-name>4:3</strong>
    <span data-aspect-readout-size>15.20 x 11.40 mm</span>
    <span data-aspect-readout-area>173.28 mm²</span>
    <span data-aspect-readout-resolution>5184 x 3888</span>
    <span data-aspect-readout-note>默认照片比例</span>
  </div>
  {table(["比例", "分辨率", "约像素", "约使用尺寸", "约面积", "约对角线", "相对 4:3", "相对标准 M43"], rows)}
</aside>
"""


aspect_module = aspect_ratio_visual()

aspect_advice_module = f"""
<aside class="insert-module" id="visual-aspect-advice">
  <div class="module-kicker">ASPECT / FIELD USE</div>
  <h3>多画幅不是装饰</h3>
  <p>4:3 最稳，16:9 最有电影感。这次打鹰山回来以后，我更明显感觉到，比例本身也可以和 LUT 一起参与表达。</p>
  {note_grid([
    ("4:3", "像素利用率最高，后期裁切空间最大。日常、旅行、人物、记录都稳，也是我最常用的默认比例。"),
    ("3:2", "更接近 APS-C / 全画幅用户熟悉的观看习惯，横竖构图都比较自然。"),
    ("16:9", "横屏最有电影感，适合山顶、大雾、风景和视频感场景；我会想到搭配电影感 LUT。"),
    ("1:1", "使用频率最低，裁切幅度最大；但搭配宝丽来方向的 LUT，会变成另一种即时影像感。"),
  ])}
</aside>
"""

phone_module = """
<aside class="insert-module" id="visual-phone">
  <div class="module-kicker">REFERENCE / PHONE</div>
  <h3>手机对比只看概念优势，不做手机评测</h3>
  <p>手机素材只做概念参照，重点放在 50mm / 75mm：L10 是真实光学长焦，手机可能是主摄裁切、副摄切换或算法融合。</p>
  <p>观察点放在发丝、文字、织物边缘、背景过渡和肤色有没有明显数字感。这里必须保留三个关键词：不是计算摄影的自然画面、相机的仪式感、情绪价值。</p>
</aside>
"""

s9_module = """
<aside class="insert-module" id="visual-s9">
  <div class="module-kicker">REFERENCE / S9</div>
  <h3>S9 的上限更高，但出门前决策更多</h3>
  <p>S9 画质上限、高感、宽容度和机身防抖都强于 L10。但它机身无内置 EVF、无热靴、无机械快门，4K60 需要裁切。</p>
  <p>我使用 S9 时经常要先想清楚带什么镜头：手动头、自动定焦蛋糕头、28-70mm 大光圈标变，还是 28-200mm 天涯头。L10 把大光圈标变、EVF、热靴、LUT 和固定镜头闭环放进一台低决策机器里。</p>
</aside>
"""

handling_module = f"""
<aside class="insert-module" id="visual-handling">
  <div class="module-kicker">BODY / OPERATION</div>
  <h3>L10 操控和外观细节</h3>
  <p>这部分不能只写“仪式感”三个字，要落到动作：贴近 EVF、转动变焦环、半按快门、拨轮调整曝光、LUT 键决定画面气质。</p>
  {note_grid([
    ("实体控制", "光圈环、自定义环、前后拨盘、快捷按钮、LUT 键、照片 / 视频 / 慢动作拨盘和比例拨杆都在机身上，常用操作不用频繁进菜单。"),
    ("按键拨盘", "按键和拨盘都非常紧致，反馈好，有高级感。这里可以和金属顶盖、底盖一起写。"),
    ("快门按钮", "半按 / 全按反馈会直接影响它像不像一台真正拿起来拍照的相机。"),
    ("变焦速度", "L10 的变焦不算快。我现在习惯在抬手过程中先参与一段变焦，让相机到眼前时焦段已经差不多到位。"),
    ("外观情绪", "钛合金色、金属外壳、十字纹蒙皮、正面干净设计，共同提供相机的仪式感和情绪价值。"),
  ])}
  <p>L10 裸机是一台随身变焦机；加上黑柔和 IT32 这种小闪，它就变成一套很轻的单兵拍摄组合，给日常记录多一个进入轻量创作的入口。</p>
</aside>
"""

hotel_module = f"""
<aside class="insert-module" id="visual-hotel">
  <div class="module-kicker">SHOOTING LINE / AIQUN HOTEL</div>
  <h3>爱群大酒店：同一空间从 24mm 收到 75mm</h3>
  <p>拍摄选在一家很有历史的酒店。窗外自然光和室内暖黄灯混在一起，L10 挂上一支 IT32 小闪和 1/4 黑柔，重点就变成同一个室内空间里，24/35/50/75mm 如何改变构图，以及自然光、直闪、黑柔、ISO 3200 RAW 颗粒分别能把画面带到哪里。</p>
  {table(
    ["焦段", "画面任务", "为什么适合爱群这组"],
    [
      ("24mm", "环境交代", "交代室内环境、走廊纵深和老建筑氛围，把人放进空间里。"),
      ("35mm", "半环境人像", "人物更明确，但仍保留酒店背景和光线关系。"),
      ("50mm", "半身 / 坐姿 / 桌边", "开始压缩空间，把杂乱环境收住。"),
      ("75mm", "表情 / 手部 / 服装细节", "从同一场景里提取细节，说明这是光学长焦，不是后期裁切。"),
    ],
  )}
  {note_grid([
    ("室内自然光", "晴天白平衡，让人物靠近窗边，压低 ISO，脸上的明暗过渡会更自然。"),
    ("室外直闪", "阴天光线平，自动白平衡加 TTL 直闪，无脑直闪就行，把脸、眼神光和衣服先提出来。"),
    ("室内直闪", "酒店走廊只有昏黄灯光，晴天白平衡配合直闪，保留黄色环境，也让人物从背景里跳出来。"),
    ("纯室内灯光", "不开闪，晴天白平衡，长焦端 F2.8 可能到 ISO 3200。RAW 黑白噪点不脏，可以保留接近胶片颗粒的质感。"),
    ("长焦弱光", "L10 只有镜头防抖，50mm / 75mm 昏暗室内不能按 S9 的手感去端。"),
  ])}
  <p>一台 L10、一支小闪光灯、一片 1/4 黑柔，已经足够组成一套轻便的人像单兵创作组合。不是专业棚拍方案，也不是弱光万能解，但确实让它从随身记录多走到轻量创作这一步。</p>
</aside>
"""

travel_module = f"""
<aside class="insert-module" id="visual-yunnan">
  <div class="module-kicker">TRAVEL LINE / YUNNAN</div>
  <h3>云南旅行：500g 的 L10 会不会成为负担？</h3>
  <p>端午带 L10 去芒市、腾冲、高黎贡山和打鹰山。远门旅行里 500g 左右可以接受，24-75mm 和微距比 28mm 定焦更像一份保险。</p>
  {note_grid([
    ("旅行题材", "风景、植物、昆虫、野生菌、火山口、雾气、人物、路标和局部细节会混在一起出现。"),
    ("高黎贡山", "大雨、高湿和伸缩镜头结构叠在一起，后半程内部起雾，是一次密封性错误示范。"),
    ("打鹰山", "大雾能见度只有十米左右，但画面很有电影感；这次让我想到 16:9 + 电影感 LUT，或者 1:1 + 宝丽来 LUT。"),
    ("主线判断", "GR 适合简单出门，L10 更适合远门旅行。拍得到比拍得好更重要。"),
  ])}
</aside>
"""

video_workflow_module = f"""
<aside class="insert-module" id="visual-video-workflow">
  <div class="module-kicker">WORKFLOW / VIDEO</div>
  <h3>照片、视频、快慢速视频切换</h3>
  <p>L10 的视频体验不只是看规格。照片、视频、快慢速视频之间切换很顺，而且参数互相独立；拍完照片后可以马上切到视频或慢动作，这对旅行记录和单兵拍摄很实用。</p>
  {note_grid([
    ("照片", "按静态记录来设置，优先构图、焦段、RAW 和 LUT。"),
    ("视频", "保留稳定的 16:9 和统一色彩，Cinelike A2 可以作为接近 ARRI 取向的直出色彩来用。"),
    ("慢动作", "单独服务手部动作、走动、雾气、咖啡和环境空镜，不污染照片参数。"),
  ])}
</aside>
"""


def inject_modules(body: str) -> str:
    insertions = {
        "<h3>先确认可用面积</h3>": sensor_module,
        "<h3>比例拨杆：多画幅和自定义入口</h3>": aspect_module,
        "<h3>L10 vs S9：全幅上限和低决策</h3>": s9_module,
        "<h3>爱群大酒店室内人像</h3>": hotel_module,
        "<h2>07 云南旅行：500g 的 L10 会不会成为负担？</h2>": travel_module,
        "<h2>05 视频能力</h2>": video_workflow_module,
        "<h3>外观、携带和操作</h3>": handling_module,
    }
    for marker, module in insertions.items():
        if marker in body:
            body = body.replace(marker, marker + "\n" + module, 1)
    return body


sections = [(title, file, inject_modules(body)) for title, file, body in sections]


def add_outline(body: str):
    items = []
    counter = 0

    def replace_heading(match):
        nonlocal counter
        counter += 1
        heading = match.group(1)
        anchor = f"outline-{counter:02d}"
        items.append((anchor, heading))
        return f'<h2 id="{anchor}">{heading}</h2>'

    body = re.sub(r"<h2>(.*?)</h2>", replace_heading, body)
    if not items:
        return body, ""

    def outline_label(heading):
        return re.sub(r"^\d+\s+", "", heading)

    links = "".join(
        f'<a href="#{anchor}"><span>{idx:02d}</span>{outline_label(heading)}</a>'
        for idx, (anchor, heading) in enumerate(items, 1)
    )
    outline = (
        '<details class="article-outline">'
        '<summary aria-label="文章大纲" title="文章大纲">'
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>'
        '</summary>'
        f'<nav aria-label="文章大纲">{links}</nav>'
        '</details>'
    )
    return body, outline


outlined_sections = []
outline_blocks = []
for title, file, body in sections:
    outlined_body, outline = add_outline(body)
    outlined_sections.append((title, file, outlined_body))
    if outline:
        outline_blocks.append(outline)

sections = outlined_sections
outline_controls = "\n".join(outline_blocks)

nav = "\n".join(
    f'<a href="#sec-{idx}">{html.escape(title)}</a>' for idx, (title, _, _) in enumerate(sections)
)
section_nav = f"<nav>{nav}</nav>" if len(sections) > 1 else ""
content = "\n".join(
    f'<section id="sec-{idx}">{body}</section>'
    for idx, (_, file, body) in enumerate(sections)
)

out = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Panasonic Lumix L10</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
  <script>
    (() => {{
      try {{
        const saved = localStorage.getItem("l10-theme");
        if (saved === "dark" || saved === "light") document.documentElement.dataset.theme = saved;
      }} catch (error) {{}}
    }})();
  </script>
  <style>
    :root {{
      color-scheme: dark light;
      --bg: #050505;
      --surface: #0c0c0c;
      --surface-2: #151515;
      --ink: #f2f2f2;
      --subhead: #f2f2f2;
      --body-text: #c8c8c8;
      --muted: #8a8a8a;
      --line: #2a2a2a;
      --accent: #ff2a2a;
      --ok: #e8e8e8;
      --font-display: "Space Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      --font-mono: "Space Mono", "SFMono-Regular", ui-monospace, monospace;
      --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f3f1ea;
        --surface: #fffdf6;
        --surface-2: #ece8dd;
        --ink: #111111;
        --subhead: #111111;
        --body-text: #38342f;
        --muted: #6f6b62;
        --line: #cfc8b8;
        --accent: #d71920;
        --ok: #111111;
      }}
    }}
    :root[data-theme="dark"] {{
      color-scheme: dark;
      --bg: #050505;
      --surface: #0c0c0c;
      --surface-2: #151515;
      --ink: #f2f2f2;
      --subhead: #f2f2f2;
      --body-text: #c8c8c8;
      --muted: #8a8a8a;
      --line: #2a2a2a;
      --accent: #ff2a2a;
      --ok: #e8e8e8;
    }}
    :root[data-theme="light"] {{
      color-scheme: light;
      --bg: #f3f1ea;
      --surface: #fffdf6;
      --surface-2: #ece8dd;
      --ink: #111111;
      --subhead: #111111;
      --body-text: #38342f;
      --muted: #6f6b62;
      --line: #cfc8b8;
      --accent: #d71920;
      --ok: #111111;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }}
    body {{
      margin: 0;
      font-family: var(--font-body);
      color: var(--ink);
      background: var(--bg);
      line-height: 1.7;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
      background-size: 28px 28px;
      opacity: .35;
    }}
    :root[data-theme="light"] body::before {{
      background:
        linear-gradient(rgba(0,0,0,.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,.035) 1px, transparent 1px);
      opacity: .28;
    }}
    .layout {{
      display: grid;
      grid-template-columns: clamp(220px, 18vw, 260px) minmax(0, 1fr);
      min-height: 100vh;
    }}
    .layout > aside {{
      position: sticky;
      top: 0;
      height: 100vh;
      padding: 14px 16px;
      border-right: 1px solid var(--line);
      background: var(--surface);
      overflow: visible;
    }}
    .brand {{
      font-family: var(--font-display);
      font-weight: 700;
      font-size: 18px;
      line-height: 1.08;
      letter-spacing: 0;
      margin-bottom: 0;
      text-transform: uppercase;
    }}
    .brand::before {{
      content: "";
      display: block;
      width: 28px;
      height: 7px;
      margin-bottom: 8px;
      background: var(--accent);
    }}
    .header-row {{
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: end;
    }}
    .compact-controls {{
      position: relative;
      display: grid;
      grid-template-columns: repeat(3, 34px);
      gap: 6px;
      align-items: end;
      justify-content: end;
    }}
    .icon-button,
    .article-outline summary {{
      width: 34px;
      height: 34px;
      margin: 0;
      padding: 0;
      border: 1px solid var(--line);
      border-radius: 0;
      background: var(--surface-2);
      color: var(--ink);
      display: grid;
      place-items: center;
      cursor: pointer;
    }}
    .icon-button:hover,
    .article-outline summary:hover {{
      border-color: var(--accent);
    }}
    .icon-button svg,
    .article-outline summary svg {{
      width: 17px;
      height: 17px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: square;
      stroke-linejoin: miter;
    }}
    a.icon-button {{
      text-decoration: none;
    }}
    nav a {{
      display: block;
      color: var(--muted);
      text-decoration: none;
      padding: 10px 0;
      border-top: 1px solid var(--line);
      font-family: var(--font-mono);
      font-size: 12px;
      letter-spacing: .03em;
    }}
    nav a:hover {{ color: var(--ink); }}
    main {{
      position: relative;
      width: min(100%, 1120px);
      max-width: 1120px;
      margin: 0 auto;
      padding: 48px clamp(34px, 5vw, 72px) 96px;
    }}
    section {{
      max-width: 920px;
      padding-bottom: 56px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 52px;
    }}
    .article-outline {{
      margin: 0;
      border: 0;
      background: transparent;
    }}
    .article-outline summary {{
      list-style: none;
    }}
    .article-outline summary::-webkit-details-marker {{ display: none; }}
    .article-outline[open] summary {{
      border-color: var(--accent);
      background: var(--accent);
      color: var(--bg);
    }}
    .article-outline nav {{
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      z-index: 10;
      display: grid;
      grid-template-columns: 1fr;
      width: min(72vw, 320px);
      margin: 0;
      border: 1px solid var(--line);
      background: var(--surface);
      box-shadow: 0 18px 36px rgba(0,0,0,.18);
    }}
    .article-outline nav a {{
      display: grid;
      grid-template-columns: 32px 1fr;
      gap: 8px;
      align-items: start;
      padding: 9px 10px;
      border-top: 0;
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      color: var(--body-text);
      font-family: var(--font-body);
      font-size: 14px;
      line-height: 1.35;
      letter-spacing: 0;
      text-decoration: none;
    }}
    .article-outline nav a:nth-child(2n) {{ border-right: 0; }}
    .article-outline nav a:nth-last-child(-n+2) {{ border-bottom: 0; }}
    .article-outline nav a:hover {{
      color: var(--ink);
      background: var(--surface-2);
    }}
    .article-outline nav a span {{
      color: var(--accent);
      font-family: var(--font-mono);
      font-size: 11px;
      line-height: 1.6;
    }}
    .layout > aside .article-outline nav a,
    .layout > aside .article-outline nav a:nth-child(2n),
    .layout > aside .article-outline nav a:nth-last-child(-n+2) {{
      border-right: 0;
      border-bottom: 1px solid var(--line);
    }}
    .layout > aside .article-outline nav a:last-child {{
      border-bottom: 0;
    }}
    h1 {{
      font-family: var(--font-display);
      font-size: 42px;
      line-height: 1.08;
      letter-spacing: 0;
      margin: 0 0 24px;
    }}
    h2 {{
      font-family: var(--font-display);
      font-size: 26px;
      line-height: 1.2;
      letter-spacing: 0;
      margin: 42px 0 14px;
      border-top: 1px solid var(--line);
      padding-top: 24px;
    }}
    h2::before {{
      content: "";
      display: inline-block;
      width: 18px;
      height: 8px;
      margin-right: 10px;
      background: var(--accent);
      vertical-align: middle;
    }}
    h3 {{
      font-family: var(--font-display);
      font-size: 20px;
      line-height: 1.35;
      margin: 30px 0 10px;
    }}
    h4 {{ font-size: 16px; font-weight: 700; margin: 22px 0 6px; color: var(--subhead); }}
    p, li {{ font-size: 16px; }}
    p {{ margin: 0 0 14px; color: var(--body-text); }}
    li {{ margin: 6px 0; color: var(--body-text); }}
    strong {{ color: var(--ink); }}
    ul, ol {{ padding-left: 1.4em; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0 28px;
      font-size: 14px;
      background: var(--surface);
    }}
    section > table,
    .insert-module table {{
      display: block;
      max-width: 100%;
      overflow-x: auto;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 10px 11px;
      vertical-align: top;
    }}
    th {{
      background: var(--surface-2);
      text-align: left;
      color: var(--ink);
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: .04em;
      text-transform: uppercase;
    }}
    td {{ color: var(--body-text); }}
    code {{
      background: var(--surface-2);
      padding: 1px 5px;
      border-radius: 0;
      color: var(--ink);
      font-family: var(--font-mono);
    }}
    blockquote {{
      margin: 16px 0;
      padding: 12px 16px;
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent);
      background: var(--surface);
      color: var(--ink);
    }}
    .insert-module {{
      width: min(100%, 980px);
      margin: 28px 0 30px;
      padding: 18px;
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent);
      background: var(--surface);
    }}
    .insert-module h3 {{
      margin-top: 4px;
    }}
    .module-kicker {{
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: .06em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .note-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      border: 1px solid var(--line);
      margin: 14px 0 2px;
    }}
    .note {{
      min-width: 0;
      padding: 12px;
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }}
    .note:nth-child(2n) {{ border-right: 0; }}
    .note:nth-last-child(-n+2) {{ border-bottom: 0; }}
    .note b {{
      display: block;
      color: var(--ink);
      font-family: var(--font-display);
      font-size: 15px;
      margin-bottom: 5px;
    }}
    .note p {{
      margin: 0;
      font-size: 14px;
    }}
    .sensor-bars {{
      display: grid;
      gap: 8px;
      margin: 16px 0;
    }}
    .sensor-bars div {{
      position: relative;
      min-height: 38px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      background: var(--surface-2);
      overflow: hidden;
    }}
    .sensor-bars div::before {{
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: var(--w);
      background: var(--accent);
      opacity: .42;
    }}
    .sensor-bars span,
    .sensor-bars b {{
      position: relative;
      z-index: 1;
    }}
    .sensor-bars span {{
      display: block;
      color: var(--ink);
      font-family: var(--font-display);
      font-size: 14px;
      line-height: 1.2;
    }}
    .sensor-bars b {{
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 11px;
    }}
    .sensor-controls {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      border: 1px solid var(--line);
      margin-top: 14px;
      background: var(--surface-2);
    }}
    .sensor-button {{
      min-width: 0;
      border: 0;
      border-right: 1px solid var(--line);
      border-radius: 0;
      background: transparent;
      color: var(--muted);
      padding: 10px;
      text-align: left;
      cursor: pointer;
    }}
    .sensor-button:last-child {{ border-right: 0; }}
    .sensor-button em {{
      display: inline-flex;
      width: 18px;
      height: 18px;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--line);
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 10px;
      font-style: normal;
      margin-bottom: 7px;
    }}
    .sensor-button em:empty {{ opacity: 0; }}
    .sensor-button strong {{
      display: block;
      font-family: var(--font-display);
      font-size: 15px;
      line-height: 1.1;
      color: var(--ink);
    }}
    .sensor-button span {{
      display: block;
      margin-top: 5px;
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--muted);
    }}
    .sensor-button.is-active {{ background: var(--accent); color: #fff; }}
    .sensor-button.is-active strong,
    .sensor-button.is-active span {{ color: #fff; }}
    .sensor-button.is-compare-b {{ box-shadow: inset 0 0 0 2px var(--ok); }}
    .sensor-button.is-compare-b em {{ border-color: var(--ok); color: var(--ink); }}
    .sensor-figure {{ margin: 16px 0 14px; }}
    .sensor-css-stage {{
      position: relative;
      width: 100%;
      aspect-ratio: 36 / 24;
      background: var(--surface);
      border: 1px solid var(--line);
      overflow: hidden;
    }}
    .sensor-css-stage::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px);
      background-size: calc(100% / 18) calc(100% / 12);
      pointer-events: none;
      opacity: .5;
    }}
    :root[data-theme="light"] .sensor-css-stage::before {{
      background:
        linear-gradient(rgba(0,0,0,.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,.045) 1px, transparent 1px);
    }}
    .sensor-css-scale {{
      position: absolute;
      left: 10px;
      right: 10px;
      bottom: 8px;
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 10px;
      z-index: 20;
    }}
    .sensor-css-box {{
      position: absolute;
      left: 50%;
      top: 50%;
      width: calc(var(--w-mm) / 36 * 100%);
      height: calc(var(--h-mm) / 24 * 100%);
      transform: translate(-50%, -50%);
      border: 1.5px solid var(--muted);
      background: color-mix(in srgb, var(--surface) 82%, transparent);
      opacity: .7;
      z-index: var(--z);
      transition: border-color .12s linear, border-width .12s linear, opacity .12s linear, background .12s linear;
    }}
    .sensor-css-box span {{
      position: absolute;
      left: 6px;
      top: 5px;
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 10px;
      line-height: 1.2;
      white-space: nowrap;
    }}
    .sensor-css-box.is-active,
    .sensor-css-box.is-compare-a {{
      border-color: var(--accent);
      border-width: 3px;
      opacity: 1;
    }}
    .sensor-css-box.is-compare-a span {{ color: var(--accent); }}
    .sensor-css-box.is-compare-b {{
      border-color: var(--ok);
      border-style: dashed;
      border-width: 2px;
      opacity: 1;
    }}
    .sensor-css-box.is-compare-b span {{ color: var(--ink); }}
    .sensor-readout {{
      display: grid;
      grid-template-columns: 1fr auto auto auto;
      gap: 12px;
      align-items: center;
      border: 1px solid var(--line);
      background: var(--surface);
      padding: 10px 12px;
      margin-bottom: 10px;
    }}
    .sensor-readout strong {{
      font-family: var(--font-display);
      font-size: 20px;
      line-height: 1;
    }}
    .sensor-readout span {{
      font-family: var(--font-mono);
      color: var(--muted);
      font-size: 11px;
    }}
    .sensor-compare {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      border: 1px solid var(--line);
      background: var(--surface);
      margin: 12px 0 2px;
    }}
    .sensor-compare div {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 8px;
      align-items: center;
      padding: 10px;
      border-right: 1px solid var(--line);
    }}
    .sensor-compare div:nth-child(2) {{ border-right: 0; }}
    .sensor-compare div span {{
      display: inline-flex;
      width: 22px;
      height: 22px;
      align-items: center;
      justify-content: center;
      background: var(--accent);
      color: #fff;
      font-family: var(--font-mono);
      font-size: 11px;
    }}
    .sensor-compare div:nth-child(2) span {{
      background: transparent;
      color: var(--ink);
      border: 1px dashed var(--ok);
    }}
    .sensor-compare div strong {{
      font-family: var(--font-display);
      font-size: 16px;
    }}
    .sensor-compare output {{
      grid-column: 1 / -1;
      border-top: 1px solid var(--line);
      padding: 12px;
      color: var(--ink);
      font-family: var(--font-display);
      font-size: 18px;
      line-height: 1.35;
    }}
    .sensor-compare output::before {{
      content: "A/B ";
      color: var(--accent);
      font-family: var(--font-mono);
      font-size: 11px;
      letter-spacing: .06em;
      vertical-align: 2px;
    }}
    .aspect-module {{
      border-left-color: var(--ok);
    }}
    .aspect-controls {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      border: 1px solid var(--line);
      background: var(--surface);
      margin: 14px 0 12px;
    }}
    .aspect-button {{
      min-width: 0;
      padding: 10px;
      border: 0;
      border-right: 1px solid var(--line);
      background: transparent;
      color: var(--ink);
      text-align: left;
      cursor: pointer;
    }}
    .aspect-button:last-child {{ border-right: 0; }}
    .aspect-button strong {{
      display: block;
      font-family: var(--font-display);
      font-size: 18px;
      line-height: 1;
    }}
    .aspect-button span {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 10px;
      white-space: nowrap;
    }}
    .aspect-button.is-active {{
      background: var(--accent);
      color: #fff;
    }}
    .aspect-button.is-active span {{ color: #fff; }}
    .aspect-figure {{
      margin: 16px 0 14px;
    }}
    .aspect-css-stage {{
      position: relative;
      width: 100%;
      aspect-ratio: 17.3 / 13;
      background: var(--surface);
      border: 1px solid var(--line);
      overflow: hidden;
    }}
    .aspect-css-stage::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(rgba(255,255,255,.055) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px);
      background-size: calc(100% / 17.3 * 2) calc(100% / 13 * 2);
      opacity: .45;
    }}
    .aspect-m43-frame,
    .aspect-image-circle,
    .aspect-css-box {{
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
    }}
    .aspect-css-box {{
      width: calc(var(--w-mm) / 17.3 * 100%);
      height: calc(var(--h-mm) / 13 * 100%);
    }}
    .aspect-m43-frame {{
      --w-mm: 17.3;
      --h-mm: 13;
      width: 100%;
      height: 100%;
      border: 2px dashed var(--muted);
      z-index: 1;
    }}
    .aspect-image-circle {{
      width: calc(var(--circle-mm) / 17.3 * 100%);
      aspect-ratio: 1;
      border: 1px dashed var(--line);
      border-radius: 50%;
      z-index: 0;
      opacity: .9;
    }}
    .aspect-m43-frame span,
    .aspect-image-circle span,
    .aspect-css-box span {{
      position: absolute;
      left: 7px;
      top: 6px;
      font-family: var(--font-mono);
      font-size: 10px;
      line-height: 1.2;
      white-space: nowrap;
    }}
    .aspect-m43-frame span {{ color: var(--muted); }}
    .aspect-image-circle span {{
      left: 50%;
      top: auto;
      bottom: 8px;
      transform: translateX(-50%);
      color: var(--muted);
    }}
    .aspect-css-box {{
      border: 1.5px solid var(--muted);
      background: color-mix(in srgb, var(--surface) 78%, transparent);
      opacity: .62;
      z-index: var(--z);
      transition: border-color .12s linear, border-width .12s linear, opacity .12s linear, background .12s linear;
    }}
    .aspect-css-box span {{ color: var(--muted); }}
    .aspect-css-box.is-active {{
      border-color: var(--accent);
      border-width: 3px;
      background: color-mix(in srgb, var(--accent) 11%, transparent);
      opacity: 1;
      z-index: 60;
    }}
    .aspect-css-box.is-active span {{
      color: var(--accent);
      font-weight: 700;
    }}
    .aspect-readout {{
      display: grid;
      grid-template-columns: .7fr 1fr auto auto 1.3fr;
      gap: 10px;
      align-items: center;
      border: 1px solid var(--line);
      background: var(--surface);
      padding: 10px 12px;
      margin-bottom: 12px;
    }}
    .aspect-readout strong {{
      font-family: var(--font-display);
      font-size: 20px;
      line-height: 1;
    }}
    .aspect-readout span {{
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 10px;
    }}
    figcaption {{
      margin-top: 8px;
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 11px;
      line-height: 1.6;
    }}
    @media (max-width: 820px) {{
      .layout {{ display: block; }}
      .layout > aside {{ position: relative; height: auto; padding: 12px 16px 10px; border-right: 0; border-bottom: 1px solid var(--line); overflow: visible; }}
      .brand {{ font-size: 17px; }}
      .brand::before {{ width: 26px; height: 7px; margin-bottom: 7px; }}
      .compact-controls {{ grid-template-columns: repeat(3, 32px); gap: 5px; }}
      .icon-button,
      .article-outline summary {{ width: 32px; height: 32px; }}
      .icon-button svg,
      .article-outline summary svg {{ width: 16px; height: 16px; }}
      main {{ width: 100%; padding: 18px 18px 60px; }}
      section {{ max-width: none; }}
      h1 {{ font-size: 32px; }}
      h2 {{ font-size: 22px; }}
      .article-outline nav {{ width: calc(100vw - 32px); }}
      .article-outline nav {{ grid-template-columns: 1fr; }}
      .article-outline nav a,
      .article-outline nav a:nth-child(2n),
      .article-outline nav a:nth-last-child(-n+2) {{
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }}
      .article-outline nav a:last-child {{ border-bottom: 0; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
      .insert-module {{ margin: 24px 0; padding: 14px; }}
      .note-grid {{ grid-template-columns: 1fr; }}
      .note,
      .note:nth-child(2n),
      .note:nth-last-child(-n+2) {{
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }}
      .note:last-child {{ border-bottom: 0; }}
      .sensor-controls {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .sensor-button {{ border-bottom: 1px solid var(--line); }}
      .sensor-button:nth-child(2n) {{ border-right: 0; }}
      .sensor-button:last-child {{ border-bottom: 0; }}
      .sensor-readout {{ grid-template-columns: 1fr; gap: 5px; }}
      .sensor-compare {{ grid-template-columns: 1fr; }}
      .sensor-compare div {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .aspect-controls {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .aspect-button {{ border-bottom: 1px solid var(--line); }}
      .aspect-button:nth-child(2n) {{ border-right: 0; }}
      .aspect-button:nth-last-child(-n+2) {{ border-bottom: 0; }}
      .aspect-readout {{ grid-template-columns: 1fr; gap: 5px; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside>
      <div class="header-row">
        <div class="brand">Panasonic Lumix L10</div>
        <div class="compact-controls">
          <button class="icon-button" type="button" data-theme-toggle aria-label="切换深浅色" title="切换深浅色" aria-pressed="false">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v18M12 3a9 9 0 0 1 0 18"/></svg>
          </button>
          <a class="icon-button" href="editor.html" aria-label="编辑 Markdown" title="编辑 Markdown">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4l11-11-4-4L4 16v4zM13 7l4 4"/></svg>
          </a>
          {outline_controls}
        </div>
      </div>
      {section_nav}
    </aside>
    <main>{content}</main>
  </div>
  <script>
    (() => {{
      const root = document.documentElement;
      const button = document.querySelector("[data-theme-toggle]");
      if (!button) return;
      const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
      const currentTheme = () => root.dataset.theme || (systemDark.matches ? "dark" : "light");
      const hasSavedTheme = () => {{
        try {{
          return Boolean(localStorage.getItem("l10-theme"));
        }} catch (error) {{
          return false;
        }}
      }};
      const render = () => {{
        const theme = currentTheme();
        button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
        button.setAttribute("title", theme === "dark" ? "切换到浅色" : "切换到深色");
        button.setAttribute("aria-label", theme === "dark" ? "切换到浅色" : "切换到深色");
      }};
      button.addEventListener("click", () => {{
        const next = currentTheme() === "dark" ? "light" : "dark";
        root.dataset.theme = next;
        try {{
          localStorage.setItem("l10-theme", next);
        }} catch (error) {{}}
        render();
      }});
      systemDark.addEventListener("change", () => {{
        if (!hasSavedTheme()) render();
      }});
      render();
    }})();
    (() => {{
      const buttons = Array.from(document.querySelectorAll("[data-sensor-target]"));
      const boxes = Array.from(document.querySelectorAll("[data-sensor-box]"));
      const labels = Array.from(document.querySelectorAll("[data-sensor-label]"));
      const name = document.querySelector("[data-sensor-readout-name]");
      const size = document.querySelector("[data-sensor-readout-size]");
      const area = document.querySelector("[data-sensor-readout-area]");
      const note = document.querySelector("[data-sensor-readout-note]");
      const compareAName = document.querySelector("[data-compare-a-name]");
      const compareBName = document.querySelector("[data-compare-b-name]");
      const output = document.querySelector("[data-compare-output]");
      if (!buttons.length || !name || !size || !area || !note || !compareAName || !compareBName || !output) return;

      let compareA = "m43";
      let compareB = "l10-used";
      const buttonFor = (id) => buttons.find((button) => button.dataset.sensorTarget === id);

      const selectSensor = (id) => {{
        buttons.forEach((button) => {{
          const active = button.dataset.sensorTarget === id;
          button.classList.toggle("is-active", active);
          if (active) {{
            name.textContent = button.dataset.name;
            size.textContent = button.dataset.size;
            area.textContent = `${{Number(button.dataset.area).toFixed(0)}} mm²`;
            note.textContent = button.dataset.note;
          }}
        }});
        boxes.forEach((box) => box.classList.toggle("is-active", box.dataset.sensorBox === id));
        labels.forEach((label) => label.classList.toggle("is-active", label.dataset.sensorLabel === id));
      }};

      const clearActive = () => {{
        buttons.forEach((button) => button.classList.remove("is-active"));
        boxes.forEach((box) => box.classList.remove("is-active"));
        labels.forEach((label) => label.classList.remove("is-active"));
        name.textContent = "未选择";
        size.textContent = "点击上方规格";
        area.textContent = "-";
        note.textContent = "选择两个规格后显示面积倍数";
      }};

      const renderCompare = () => {{
        const aButton = compareA ? buttonFor(compareA) : null;
        const bButton = compareB ? buttonFor(compareB) : null;
        compareAName.textContent = aButton ? aButton.dataset.name : "未选择";
        compareBName.textContent = bButton ? bButton.dataset.name : "未选择";

        if (aButton && bButton) {{
          const leftArea = Number(aButton.dataset.area);
          const rightArea = Number(bButton.dataset.area);
          const ratio = leftArea / rightArea;
          const percent = (ratio - 1) * 100;
          const direction = percent >= 0 ? "大约多" : "大约少";
          output.textContent = `A（${{aButton.dataset.name}}）是 B（${{bButton.dataset.name}}）的 ${{ratio.toFixed(2)}} 倍，面积${{direction}} ${{Math.abs(percent).toFixed(0)}}%。`;
        }} else if (aButton) {{
          output.textContent = `A（${{aButton.dataset.name}}）已选中，再点一个规格作为 B 进行对比。`;
        }} else if (bButton) {{
          output.textContent = `B（${{bButton.dataset.name}}）已选中，再点一个规格作为 A 进行对比。`;
        }} else {{
          output.textContent = "点击上方规格选择 A，再点击另一个规格选择 B。再次点击同一个规格可取消选中。";
        }}

        buttons.forEach((button) => {{
          const id = button.dataset.sensorTarget;
          const marker = button.querySelector("[data-compare-marker]");
          const selected = id === compareA || id === compareB;
          button.classList.toggle("is-compare-a", id === compareA);
          button.classList.toggle("is-compare-b", id === compareB);
          button.setAttribute("aria-pressed", selected ? "true" : "false");
          if (marker) marker.textContent = id === compareA ? "A" : id === compareB ? "B" : "";
        }});
        boxes.forEach((box) => {{
          box.classList.toggle("is-compare-a", box.dataset.sensorBox === compareA);
          box.classList.toggle("is-compare-b", box.dataset.sensorBox === compareB);
        }});
        labels.forEach((label) => {{
          label.classList.toggle("is-compare-a", label.dataset.sensorLabel === compareA);
          label.classList.toggle("is-compare-b", label.dataset.sensorLabel === compareB);
        }});

        if (aButton) selectSensor(compareA);
        else clearActive();
      }};

      buttons.forEach((button) => {{
        button.addEventListener("click", () => {{
          const id = button.dataset.sensorTarget;
          if (id === compareA) compareA = "";
          else if (id === compareB) compareB = "";
          else if (!compareA) compareA = id;
          else if (!compareB) compareB = id;
          else compareA = id;
          renderCompare();
        }});
      }});

      renderCompare();
    }})();
    (() => {{
      const buttons = Array.from(document.querySelectorAll("[data-aspect-target]"));
      const boxes = Array.from(document.querySelectorAll("[data-aspect-box]"));
      const name = document.querySelector("[data-aspect-readout-name]");
      const size = document.querySelector("[data-aspect-readout-size]");
      const area = document.querySelector("[data-aspect-readout-area]");
      const resolution = document.querySelector("[data-aspect-readout-resolution]");
      const note = document.querySelector("[data-aspect-readout-note]");
      if (!buttons.length || !name || !size || !area || !resolution || !note) return;

      const selectAspect = (id) => {{
        const activeButton = buttons.find((button) => button.dataset.aspectTarget === id);
        if (!activeButton) return;
        buttons.forEach((button) => {{
          const active = button === activeButton;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-pressed", active ? "true" : "false");
        }});
        boxes.forEach((box) => box.classList.toggle("is-active", box.dataset.aspectBox === id));
        name.textContent = activeButton.dataset.name;
        size.textContent = activeButton.dataset.size;
        area.textContent = `${{Number(activeButton.dataset.area).toFixed(2)}} mm²`;
        resolution.textContent = activeButton.dataset.resolution;
        note.textContent = activeButton.dataset.note;
      }};

      buttons.forEach((button) => {{
        button.addEventListener("click", () => selectAspect(button.dataset.aspectTarget));
      }});
      selectAspect("43");
    }})();
  </script>
</body>
</html>
"""

Path("index.html").write_text(out, encoding="utf-8")
print("index.html")
