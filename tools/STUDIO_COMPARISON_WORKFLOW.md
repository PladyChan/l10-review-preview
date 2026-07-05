# Studio Comparison Reusable Workflow

这套流程用于把同场景、同机位、同焦段的 RAW 导出 JPG 整理成可交互对比工具，并生成文章正文里的上下对比预览图。

## 文件分工

- `studio-comparison-config.json`：唯一配置入口。相机组、ISO、素材前缀、IFC 锚点、边角锚点、正文预览倍率都写在这里。
- `studio-comparison.html`：交互对比工具。打开时读取 `studio-comparison-config.json`，不再手写相机配置。
- `studio_comparison_pipeline.py`：复用流程脚本。负责检查素材、复制素材、生成正文预览图、输出 Markdown 图片引用。
- `studio-assets/raw/`：交互工具读取的原始导出 JPG。
- `studio-assets/night-compare-400/`：正文预览图。当前项目沿用旧文件夹名，但图片内容是 200% 上下排预览。

## 素材目录

工具默认读取：

```text
tools/studio-assets/raw/{group_id}/{ISO}/{prefix}_{ISO}.jpg
```

当前例子：

```text
tools/studio-assets/raw/L10_35mm_vs_X100VI_35mm/ISO3200/01_L10_35mm_ISO3200.jpg
tools/studio-assets/raw/L10_35mm_vs_X100VI_35mm/ISO3200/02_X100VI_35mm_ISO3200.jpg
```

`prefix` 来自 `studio-comparison-config.json` 里的 camera 配置。

## 锚点原则

- `anchors.ifc`：每台机每个对比组共用一套 IFC 字样锚点。固定机位、固定构图时，不要按 ISO 重复量。
- `anchors.corner`：定位边角用的建筑锚点。
- `scaleBaseCamera`：尺寸归一基准。当前是 `l10`，参照图按 L10 原图宽度归一。
- `scaleBaseLabel`：正文预览图角标里的基准名称。当前显示 `L10 size x ...`。
- 工具里“回到中心”回到 IFC 锚点；“定位边角”回到 `corner` 锚点。

## 常用命令

检查素材和锚点是否齐：

```bash
python3 tools/studio_comparison_pipeline.py --check
```

生成正文上下预览图：

```bash
python3 tools/studio_comparison_pipeline.py --generate-previews
```

输出可粘进 Markdown 的图片引用：

```bash
python3 tools/studio_comparison_pipeline.py --emit-markdown
```

如果配置里给 camera 或 group 加了 `sourceDir`，可以从源目录复制素材到工具目录：

```bash
python3 tools/studio_comparison_pipeline.py --copy-assets --check --generate-previews
```

可选字段示例：

```json
{
  "id": "l10",
  "name": "Panasonic Lumix DC-L10",
  "focal": "35mm",
  "prefix": "01_L10_35mm",
  "sourceDir": "/Volumes/Media/照片/相片/L10/4机对比/RAW/L10",
  "sourcePattern": "*{iso}*.jpg"
}
```

## 复用步骤

1. 把新导出的 JPG 按机型或场景整理好。
2. 在 `studio-comparison-config.json` 里新增或修改 `groups`。
3. 填每个 camera 的 `prefix`，保证目标文件名能变成 `{prefix}_{ISO}.jpg`。
4. 给每台机填 `anchors.ifc` 和 `anchors.corner`。
5. 跑 `python3 tools/studio_comparison_pipeline.py --check`。
6. 跑 `python3 tools/studio_comparison_pipeline.py --generate-previews`。
7. 跑 `python3 build_l10_html_preview.py`。
8. 检查本地页面，再提交发布。

## 注意

- 正文预览图是阅读用的，不替代交互工具。工具仍然可以 400% 查看原图像素。
- 正文预览图当前为 200%，由 `previewZoom` 控制。
- `previewFileSuffix` 当前保留 `_400` 是为了不改现有文章引用；新项目可以改成 `_200`。
