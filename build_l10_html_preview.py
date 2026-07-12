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

        image_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line)
        if image_match:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            alt, src = image_match.groups()
            escaped_src = html.escape(src)
            escaped_alt = html.escape(alt)
            if "l10-sharpness-assets/contact-sheets/" in src and src.endswith(".jpg"):
                mobile_src = html.escape(src[:-4] + "_mobile.jpg")
                media = (
                    f'<picture><source media="(max-width: 820px)" srcset="{mobile_src}">'
                    f'<img src="{escaped_src}" alt="{escaped_alt}" loading="lazy"></picture>'
                )
            else:
                media = f'<img src="{escaped_src}" alt="{escaped_alt}" loading="lazy">'
            out.append(f'<figure class="article-image">{media}<figcaption>{inline(alt)}</figcaption></figure>')
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
    <output data-compare-output>A（标准 M43）是 B（L10 可用）的 1.30 倍；A 比 B 多约 30%，B 比 A 少约 23%。</output>
  </div>
  {table(["规格", "尺寸", "面积", "口径"], rows)}
"""


sensor_module = f"""
<aside class="insert-module" id="visual-sensor">
  <h3>画幅对比工具：L10 可用面积小于标准 M43 全面积</h3>
  <p>这块只讲尺寸关系，不直接等同于最终画质。L10 用的是 4/3 多画幅路线，但可用成像面积要和标准 M43 分开看。</p>
  {sensor_visual().lstrip()}
</aside>
"""

studio_compare_module = """
<aside class="insert-module studio-compare-module studio-compare-module--compact" id="studio-comparison">
  <div class="studio-compare-shell">
    <iframe data-studio-tool-frame title="RAW 导出 JPG 局部对比工具"></iframe>
  </div>
</aside>
"""

day_sharpness_module = """
<aside class="insert-module studio-compare-module studio-compare-module--compact" id="day-sharpness-comparison">
  <div class="studio-compare-shell day-sharpness-shell">
    <iframe data-day-sharpness-frame title="F5.6 白天锐度对比工具"></iframe>
  </div>
</aside>
"""

l10_sharpness_module = """
<aside class="insert-module studio-compare-module studio-compare-module--compact" id="l10-sharpness">
  <div class="studio-compare-shell l10-sharpness-shell">
    <iframe data-l10-sharpness-frame title="L10 镜头锐度单项工具"></iframe>
  </div>
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


def inject_modules(body: str) -> str:
    l10_results_marker = "<h3>中心：先比焦段，再比光圈</h3>"
    if l10_results_marker in body:
        body = body.replace(l10_results_marker, l10_sharpness_module + "\n" + l10_results_marker, 1)

    day_marker = "<h3>F5.6 锐度对比参数表</h3>"
    if day_marker in body:
        body = body.replace(day_marker, day_sharpness_module + "\n" + day_marker, 1)

    night_marker = "<h3>夜晚 ISO 噪点对比</h3>"
    if night_marker in body:
        body = body.replace(night_marker, night_marker + "\n" + studio_compare_module, 1)

    insertions = {
        "<h3>传感器可用面积</h3>": sensor_module,
        "<h3>比例拨杆：多画幅和自定义入口</h3>": aspect_module,
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
  <link href="https://fonts.googleapis.com/css2?family=Doto:wght@500;600;700;800&family=Space+Grotesk:wght@500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
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
      --font-doto: "Doto", "Space Mono", "SFMono-Regular", ui-monospace, monospace;
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
      font-family: var(--font-doto);
      font-weight: 800;
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
      grid-template-columns: minmax(0, 1fr);
      gap: 14px;
      align-items: start;
    }}
    .compact-controls {{
      position: relative;
      display: grid;
      grid-template-columns: repeat(3, 34px);
      gap: 6px;
      align-items: end;
      justify-content: start;
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
      font-family: var(--font-doto);
      font-weight: 700;
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
      font-family: var(--font-doto);
      font-weight: 800;
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
      font-family: var(--font-doto);
      font-weight: 700;
      font-size: 11px;
      letter-spacing: .04em;
      text-transform: uppercase;
    }}
    td {{ color: var(--body-text); }}
    .article-image {{
      margin: 18px 0 24px;
      border: 1px solid var(--line);
      background: var(--surface);
      overflow: hidden;
    }}
    .article-image img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .article-image picture {{ display: block; }}
    .article-image figcaption {{
      margin: 0;
      padding: 8px 10px;
      border-top: 1px solid var(--line);
      background: var(--surface-2);
    }}
    code {{
      background: var(--surface-2);
      padding: 1px 5px;
      border-radius: 0;
      color: var(--ink);
      font-family: var(--font-doto);
      font-weight: 700;
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
    .studio-compare-module {{
      width: min(100%, 1180px);
    }}
    .studio-compare-module--compact {{
      padding: 0;
      border-left-width: 4px;
    }}
    .studio-compare-shell {{
      width: 100%;
      height: min(84vh, 820px);
      min-height: 640px;
      border: 1px solid var(--line);
      background: var(--surface-2);
      overflow: hidden;
    }}
    .studio-compare-shell iframe {{
      display: block;
      width: 100%;
      height: 100%;
      border: 0;
      background: var(--surface);
    }}
    .day-sharpness-shell {{
      height: min(86vh, 860px);
      min-height: 680px;
    }}
    .l10-sharpness-shell {{
      height: min(86vh, 860px);
      min-height: 680px;
    }}
    .module-link {{
      margin: 10px 0 0;
      font-family: var(--font-doto);
      font-weight: 700;
      font-size: 12px;
    }}
    .module-link a {{
      color: var(--accent);
      text-decoration: none;
      border-bottom: 1px solid currentColor;
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
      font-family: var(--font-doto);
      font-weight: 700;
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
      font-family: var(--font-doto);
      font-weight: 800;
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
      font-family: var(--font-doto);
      font-weight: 700;
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
      font-family: var(--font-doto);
      font-weight: 700;
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
      font-family: var(--font-doto);
      font-weight: 700;
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
      font-family: var(--font-doto);
      font-weight: 700;
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
      font-family: var(--font-doto);
      font-weight: 800;
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
      font-family: var(--font-doto);
      font-weight: 800;
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
      font-family: var(--font-doto);
      font-weight: 800;
      font-size: 18px;
      line-height: 1;
    }}
    .aspect-button span {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-family: var(--font-doto);
      font-weight: 700;
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
      font-family: var(--font-doto);
      font-weight: 700;
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
      font-family: var(--font-doto);
      font-size: 22px;
      font-weight: 800;
      line-height: 1;
    }}
    .aspect-readout span {{
      color: var(--muted);
      font-family: var(--font-doto);
      font-weight: 700;
      font-size: 10px;
    }}
    figcaption {{
      margin-top: 8px;
      color: var(--muted);
      font-family: var(--font-doto);
      font-weight: 600;
      font-size: 11px;
      line-height: 1.6;
    }}
    @media (max-width: 820px) {{
      .layout {{ display: block; }}
      .layout > aside {{ position: relative; height: auto; padding: 12px 16px 10px; border-right: 0; border-bottom: 1px solid var(--line); overflow: visible; }}
      .brand {{ font-size: 17px; }}
      .brand::before {{ width: 26px; height: 7px; margin-bottom: 7px; }}
      .compact-controls {{ grid-template-columns: repeat(6, 32px); gap: 5px; }}
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
      .studio-compare-module--compact {{ padding: 0; }}
      .studio-compare-shell {{ height: 76vh; min-height: 560px; }}
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
  <link rel="stylesheet" href="tools/tool-ui.css">
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
          <a class="icon-button" href="#" data-studio-tool-link aria-label="图片对比工具" title="图片对比工具">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h7v7H4zM13 5h7v7h-7zM4 14h7v5H4zM13 14h7v5h-7z"/></svg>
          </a>
          <a class="icon-button" href="#" data-day-sharpness-link aria-label="白天锐度工具" title="白天锐度工具">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 18l6-6 4 4 6-10M4 20h16"/></svg>
          </a>
          <a class="icon-button" href="#" data-l10-sharpness-link aria-label="L10 镜头锐度工具" title="L10 镜头锐度工具">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h4l2-2h4l2 2h4v12H4zM12 10a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"/></svg>
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
      const resolveToolUrl = (toolPath) => {{
        const path = window.location.pathname;
        const pagesRoot = "/l10-review-preview";
        if (path === pagesRoot || path.startsWith(`${{pagesRoot}}/`)) {{
          return `${{window.location.origin}}${{pagesRoot}}/${{toolPath}}`;
        }}
        return new URL(toolPath, window.location.href.endsWith("/") ? window.location.href : new URL(".", window.location.href)).href;
      }};
      const tools = [
        ["tools/studio-comparison.html", "[data-studio-tool-link]", "[data-studio-tool-frame]"],
        ["tools/day-sharpness.html", "[data-day-sharpness-link]", "[data-day-sharpness-frame]"],
        ["tools/l10-sharpness.html", "[data-l10-sharpness-link]", "[data-l10-sharpness-frame]"],
      ];
      tools.forEach(([toolPath, linkSelector, frameSelector]) => {{
        const url = resolveToolUrl(toolPath);
        document.querySelectorAll(linkSelector).forEach((link) => {{
          link.href = url;
        }});
        document.querySelectorAll(frameSelector).forEach((frame) => {{
          frame.src = url;
        }});
      }});
    }})();
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
          const aPercent = (leftArea / rightArea - 1) * 100;
          const bPercent = (rightArea / leftArea - 1) * 100;
          const aDirection = aPercent >= 0 ? "多" : "少";
          const bDirection = bPercent >= 0 ? "多" : "少";
          output.textContent = `A（${{aButton.dataset.name}}）是 B（${{bButton.dataset.name}}）的 ${{ratio.toFixed(2)}} 倍；A 比 B ${{aDirection}}约 ${{Math.abs(aPercent).toFixed(0)}}%，B 比 A ${{bDirection}}约 ${{Math.abs(bPercent).toFixed(0)}}%。`;
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
