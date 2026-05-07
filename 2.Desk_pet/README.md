# Windows Desk Pet

一个参考 Codex 桌宠 atlas 规范实现的 Windows 桌面宠物。程序本身是 Windows 桌宠，不依赖 Codex 运行；它只复用 Codex 的 `8x9`、`192x208` spritesheet 结构和状态行设计。

已生成的 Codex 桌宠包位于：

```text
codex-pet\desk-boy\
```

本机已安装到：

```text
C:\Users\love 1118\.codex\pets\desk-boy\
```

Windows 程序默认读取 `codex-pet\desk-boy\spritesheet.webp` 播放动画。

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

## 运行

```powershell
python desktop_pet.py
```

默认会从程序旁边的 `codex-pet\desk-boy` 目录读取透明 spritesheet，并播放 `idle`。

可选参数：

```powershell
python desktop_pet.py --scale 1.5
python desktop_pet.py --idle-random
python desktop_pet.py --pet-dir .\codex-pet\desk-boy
```

`--scale` 控制显示大小，默认 `1.35`。

## 操作

- 左键拖拽移动桌宠。
- 右键打开动作菜单。
- 双击切换到工作中动作。
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

`photo` 目录中的每张 PNG 是源动作条：

- 多帧横向排列，不要求统一 6 帧。
- 背景是绿色幕布，`make_codex_pet.py` 会先做边界连通绿幕抠除和边缘绿色溢出清理。
- Windows 程序不直接播放这些绿幕源图，只播放生成后的透明 `spritesheet.webp`。

新增素材时保持同样规则，并在 `make_codex_pet.py` 的动作映射里指定它对应的 Codex state。
