# Codex Desk Pet

一个基于 `photo` 目录动作条素材生成的 Codex 自定义桌宠。

已生成的 Codex 桌宠包位于：

```text
codex-pet\desk-boy\
```

本机已安装到：

```text
C:\Users\love 1118\.codex\pets\desk-boy\
```

重启 Codex 后，可以在自定义宠物中选择 `Desk Boy`。

## 重新生成 Codex 宠物包

```powershell
python make_codex_pet.py
```

生成内容：

- `codex-pet-build\spritesheet.png`
- `codex-pet-build\spritesheet.webp`
- `codex-pet-build\contact-sheet.png`
- `C:\Users\love 1118\.codex\pets\desk-boy\pet.json`
- `C:\Users\love 1118\.codex\pets\desk-boy\spritesheet.webp`

脚本会自动：

- 抠除绿色背景。
- 识别每条动作条中的主角色帧，不按固定等分硬切。
- 生成 Codex 固定 `1536x1872`、`8x9`、每格 `192x208` 的 spritesheet。
- 按 Codex 状态行填入 `idle`、`running-right`、`running-left`、`waving`、`jumping`、`failed`、`waiting`、`running`、`review`。

## 动作映射

| Codex state | 素材 |
| --- | --- |
| `idle` | `待机眨眼.png` |
| `running-right` | `监督工作.png` |
| `running-left` | `监督工作.png` 镜像 |
| `waving` | `监督工作.png` 采样 |
| `jumping` | `完成庆祝.png` |
| `failed` | `报错推手.png` |
| `waiting` | `困倦睡觉.png` |
| `running` | `敲代码.png` |
| `review` | `修Bug.png` |

## Windows EXE 版本

下面的普通 Windows 透明窗版本仍保留，但它不是 Codex 宠物格式；优先使用上面的 Codex 包。

## 运行

```powershell
python desktop_pet.py
```

默认会从程序旁边的 `photo` 目录读取素材，并播放 `待机眨眼`。

可选参数：

```powershell
python desktop_pet.py --subsample 1
python desktop_pet.py --delay 140
python desktop_pet.py --photo-dir .\photo
```

`--subsample` 是整数缩放系数，默认 `2`，也就是把原始帧缩小到一半。

## 操作

- 左键拖拽移动桌宠。
- 右键打开动作菜单。
- 双击切换到下一个动作。
- 右键菜单里的 `退出` 关闭程序。

## 打包 EXE

当前项目使用 PyInstaller 打包：

```powershell
.\build.ps1 -InstallPyInstaller
```

如果本机已经安装 PyInstaller，可以直接运行：

```powershell
.\build.ps1
```

打包完成后，EXE 位于：

```text
dist\DeskPet\DeskPet.exe
```

## 素材约定

`photo` 目录中的每张 PNG 是一条横向动作条：

- 6 帧横向排列。
- 当前素材尺寸为 `2172x724`，每帧 `362x724`。
- 背景是绿色幕布，程序会按阈值抠除绿色，并在 Windows 上把窗口裁剪成宠物轮廓。

新增素材时保持同样规则，文件名会作为右键菜单中的动作名。
