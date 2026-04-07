# Markdown 页码锚点部署说明

本文说明如何在服务器上部署带有 Markdown 页码锚点能力的 MinerU 改动，并尽量避免影响现有的 vLLM 服务。

## 本次改动内容

本次改动只涉及 MinerU 的 Markdown 输出逻辑：

- 在 Markdown 输出中按页插入 `[PAGE=n]` 锚点
- 支持通过配置项或环境变量启用/关闭

本次改动不涉及：

- vLLM 服务实现
- MinerU 与 vLLM 的调用协议
- 表格识别模型本身

因此，这次部署的重点是“让服务器上的 Python 环境实际使用你修改后的 MinerU 代码”。

## 是否会影响现有 vLLM

不会自动重装或重启 vLLM 服务，但有一个前提：

- 如果 MinerU 和 vLLM 共用同一个 Python 环境，重新 `pip install` 可能会连带调整该环境中的依赖版本
- 如果 vLLM 是独立服务、独立容器、独立虚拟环境，则通常不会受到影响

推荐做法是：

- 不直接覆盖现有线上环境
- 新建一个单独的 Python 虚拟环境安装修改后的 MinerU
- 继续让新的 MinerU 指向原来正在运行的 vLLM 服务地址

这样最安全。

## 推荐部署方式

### 方式一：新建独立虚拟环境，推荐

适用场景：

- 线上已有 MinerU 和 vLLM 在跑
- 希望尽量降低风险

示例步骤：

```bash
cd /path/to/MinerU
python -m venv .venv-page-anchor
source .venv-page-anchor/bin/activate
pip install --upgrade pip
pip install -e .
```

说明：

- `-e .` 表示开发模式安装
- 后续你修改这份源码后，无需重复 reinstall，环境会直接引用当前源码

如果服务器是 Windows，可改为：

```powershell
cd E:\path\to\MinerU
python -m venv .venv-page-anchor
.venv-page-anchor\Scripts\activate
pip install --upgrade pip
pip install -e .
```

### 方式二：直接安装 fork 仓库

适用场景：

- 服务器上不保留完整源码工作目录
- 只想部署一个固定版本

```bash
pip uninstall mineru
pip install git+https://github.com/westdata/MinerU.git
```

如果要固定到某个分支：

```bash
pip install git+https://github.com/westdata/MinerU.git@your-branch-name
```

### 方式三：在现有环境直接 `pip install .`

不推荐作为首选，但可以用：

```bash
pip uninstall mineru
pip install .
```

风险：

- 如果当前环境和线上 vLLM 共用依赖，可能引入版本变化

## 如何启用 Markdown 页码锚点

本次功能支持两种启用方式。

### 方式一：环境变量

```bash
export MINERU_MD_PAGE_ANCHOR=true
```

Windows PowerShell：

```powershell
$env:MINERU_MD_PAGE_ANCHOR = "true"
```

### 方式二：配置文件

在 `mineru.json` 中增加：

```json
{
  "markdown-page-anchor-enable": true
}
```

说明：

- 环境变量优先级高于配置文件
- 如果两者都没设置，默认关闭

## 配置优先级

页码锚点开关优先级如下：

1. 环境变量 `MINERU_MD_PAGE_ANCHOR`
2. 配置文件 `mineru.json` 中的 `markdown-page-anchor-enable`
3. 默认值 `false`

## 输出效果

启用后，Markdown 输出会按页插入锚点：

```md
[PAGE=1]

第一页内容

[PAGE=2]

第二页内容
```

说明：

- 仅插入页级锚点
- 不会修改表格 HTML 本身
- 不会影响 `content_list.json`

## 建议的上线流程

推荐按以下顺序执行：

1. 在服务器创建独立虚拟环境
2. 安装你 fork 的 MinerU 代码
3. 配置 `MINERU_MD_PAGE_ANCHOR=true`
4. 使用一份已知有跨页表格问题的 PDF 做回归测试
5. 确认输出 Markdown 中出现 `[PAGE=n]`
6. 再接入你们现有的大模型抽取链路验证效果

## 回滚方式

如果只想关闭该功能，不需要卸载 MinerU，直接：

- 删除环境变量 `MINERU_MD_PAGE_ANCHOR`
- 或设置为 `false`
- 或把配置文件中的 `markdown-page-anchor-enable` 改为 `false`

如果需要彻底回滚代码版本：

- 重新安装原始仓库版本
- 或切回原始 commit / tag 后重新安装

## 额外建议

如果服务器当前的 MinerU 与 vLLM 共用同一个 Python 环境，建议优先使用“独立虚拟环境 + `pip install -e .`”方式部署本次改动。

这是风险最低、后续调试也最方便的方案。
