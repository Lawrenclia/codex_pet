# Wisdel Codex 宠物

![Wisdel 动画预览](build-output/qa/contact-sheet.png)

这是一个基于 Wisdel 桌面伴侣素材制作的自定义 Codex 动画宠物。当前版本直接像素化原始 GIF 帧，尽量保留角色的橙色眼睛、表情、黑色轮廓和小比例 Q 版剪影，而不是重新绘制角色。

## 项目内容

这个仓库保留了从源素材到最终可安装包的完整整理结果，不只是最后两个宠物文件。

| 路径 | 说明 |
| --- | --- |
| `installable-pet/` | Codex 可直接加载的最小安装包。 |
| `installable-pet/pet.json` | 宠物清单文件。 |
| `installable-pet/spritesheet.webp` | 最终 8x9 动画精灵图。 |
| `build-output/` | 完整构建产物，包括拆帧、最终图集、质检文件和预览视频。 |
| `build-output/final/` | 最终图集和对应清单。 |
| `build-output/frames/` | 按动画状态拆出的单帧 PNG。 |
| `build-output/qa/contact-sheet.png` | 全部动画行的质检总览图。 |
| `build-output/qa/videos/` | 每个状态的预览视频。 |
| `source-materials/皮肤素材/` | 制作时使用的原始 Wisdel 素材。 |
| `references/maidbit-materials/` | 制作过程中生成或保留的参考图。 |
| `tools/build_wisdel_pixel_pet.py` | 用于重新构建当前像素化版本的脚本。 |

## 安装

把可安装包复制到 Codex 本地宠物目录：

```bash
ditto installable-pet ~/.codex/pets/wisdel
```

如果宠物列表没有立刻刷新，重启 Codex 即可。安装完成后，目标目录应包含：

```text
~/.codex/pets/wisdel/
  pet.json
  spritesheet.webp
```

## 动画行

Codex 宠物使用固定的 8 列 9 行图集。当前图集的行分配如下：

| 行 | 状态 | 来源动作 |
| --- | --- | --- |
| 0 | `idle` | 平静眨眼和呼吸循环。 |
| 1 | `running-right` | 正面活跃动作，用于向右移动。 |
| 2 | `running-left` | 由向右移动行镜像得到。 |
| 3 | `waving` | 偏打招呼感的兴奋动作。 |
| 4 | `jumping` | 跳跃或惊讶动作。 |
| 5 | `failed` | 失败状态的震惊反应。 |
| 6 | `waiting` | 坐下等待循环。 |
| 7 | `running` | 任务运行中的忙碌循环。 |
| 8 | `review` | 带眼镜表情的专注审阅循环。 |

Codex 不会在任何时候随机播放所有行。普通闲置时主要播放 `idle`，其他行会在运行、等待、失败、审阅、悬停或移动等状态下触发。

## 重新构建

在仓库根目录运行：

```bash
python3 tools/build_wisdel_pixel_pet.py
```

脚本会读取 `source-materials/皮肤素材/可用素材/` 中的 GIF，保留透明通道，挑选并像素化每个状态的帧，统一角色尺寸，生成 Codex 精灵图、质检预览和最小安装包。

重新构建后，主要输出位置为：

| 路径 | 内容 |
| --- | --- |
| `build-output/final/` | 最终图集、清单和图集校验结果。 |
| `build-output/qa/` | contact sheet、审阅 JSON、运行摘要和预览视频。 |
| `installable-pet/` | 可复制到 Codex 宠物目录的安装包。 |

## 质检产物

当前保留的质检文件包括：

- `build-output/qa/contact-sheet.png`
- `build-output/qa/source-sheet-pixelized.png`
- `build-output/qa/review.json`
- `build-output/qa/run-summary.json`
- `build-output/qa/videos/`

## 备注

- 黑色轮廓来自原始透明 GIF 帧，构建时会保留。
- 构建脚本直接使用源 GIF 的 alpha 通道，不会用黑色抠图，避免破坏角色轮廓和深色服装细节。
- 当前移动行使用正面动作适配 Codex 的行布局，因为源素材里没有真正的侧面奔跑循环。
- `special0.gif` 保留在源素材中，但没有进入最终宠物，因为它包含第二个角色，整体构图也更大。

## 授权与致谢

这是一个由本地 Wisdel 素材整理制作的同人 Codex 宠物包。原始角色美术和素材版权归各自权利方所有。本仓库仅用于个人、非商业的 Codex 自定义，不是 Codex、OpenAI 或游戏官方素材发布。

感谢 [OTAXIO/digit_maid](https://github.com/OTAXIO/digit_maid) 项目提供的素材参考。
