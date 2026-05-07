# Windows Desk Pet

一个基于 `photo` 目录动作条素材的 Windows 桌面宠物。

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
