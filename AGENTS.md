# 维护约定

本仓库是 `MHSanaei/3x-ui` 的非官方去广告版本。以最小改动同步正式 release，保留原项目功能、许可证和作者归属。

## 更新时必须保留

- 从本仓库当前 `main` 恢复整个 `.noads/`、`.github/workflows/`、`AGENTS.md`、`README.md` 和 `NOADS.md`，不能使用上游版本覆盖这些文件。
- 必须通过 `.noads/prepare.py` 在独立的上游工作目录中准备更新；不要直接合并上游到 `main`。
- 每次更新重新应用面板去广告补丁，并清理所有受版本控制的 README 中的赞助、捐款和付费推广章节；删除 `.github/FUNDING.yml` / `.yaml`。安装、面板和命令行更新地址必须指向本仓库。
- `.noads/check.py` 是发布前必需的检查。未识别的广告、补丁冲突、新密钥候选或测试失败必须停止更新；修正规则后再重试，不得跳过检查。
- `AGENTS.md` 是维护说明，自动执行依靠同步脚本和 GitHub Actions。改动去广告规则时同时更新脚本与回归测试。

## 修改范围和隐私

- 保留业务功能、用户数据、协议设置、第三方软件的许可证和技术文档链接。MTProto 用户配置中的 `adTag` 是协议功能，不能作为面板广告删除。
- 不提交真实密钥、账号密码、用户数据库、服务器配置或私人日志；新增候选必须人工核查，不得整目录排除扫描。
- 保留 GPL-3.0 许可证和上游作者归属；赞助推广清理不应移除作者署名、贡献者和正常社区工具介绍。
- 不强制推送、不改写历史，不覆盖已发布 release 的标签或文件。全部检查、八个平台构建及文件校验成功后，才允许推进 `main` 并发布。

## 验证

控制规则和文档改动：

```sh
python -m unittest discover -s .noads -p 'test_*.py'
python .noads/check.py --maintenance
git diff --check
```

`--maintenance` 只用于本仓库自检：此时 provenance 记录的仍是上次发布，允许转换脚本已更新。
对 `prepare.py` 生成的发行源码树，仍用 `python .noads/check.py --root <树> --control .` 严格校验，不得加该参数。

同步代码时沿用 `.github/workflows/noads-sync.yml` 中的密钥扫描、前端类型检查/测试/构建、Go 回归测试及八个平台构建。规则变化还必须用原始上游 release 验证准备流程，确认本仓库控制文件按字节保留、README 推广清理成功、许可证未变化。
