#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 3 ]; then
    echo "用法: $0 <commitA> <commitB> <message>"
    echo "将 commitA 之后、commitB 及之前的提交压缩成一个新提交。"
    echo "必须提供新提交的信息。"
    exit 1
fi

A="$1"
B="$2"
MESSAGE="$3"

# 检查是否在 Git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "错误：当前目录不是 Git 仓库"
    exit 1
fi

# 检查提交是否存在
if ! git cat-file -e "$A^{commit}" 2>/dev/null; then
    echo "错误：$A 不是有效的提交"
    exit 1
fi
if ! git cat-file -e "$B^{commit}" 2>/dev/null; then
    echo "错误：$B 不是有效的提交"
    exit 1
fi

# 确保 A 是 B 的祖先
if ! git merge-base --is-ancestor "$A" "$B"; then
    echo "错误：$A 不是 $B 的祖先，无法继续。"
    exit 1
fi

# 检查工作区是否干净
if ! git diff-index --quiet HEAD --; then
    echo "错误：工作区有未提交的修改，请先提交或暂存。"
    exit 1
fi

# 保存当前分支名
BRANCH=$(git branch --show-current)
if [ -z "$BRANCH" ]; then
    echo "错误：当前处于 detached HEAD 状态，请先切换到分支。"
    exit 1
fi

echo "⚠️  即将把 $A..$B 范围内的所有提交压缩成一个新提交。"
echo "当前分支：$BRANCH"
echo "区间起点：$A"
echo "区间终点：$B"
echo "提交信息：$MESSAGE"
read -p "确认操作？输入 yes 继续: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "已取消。"
    exit 0
fi

# 软重置到 A（保留工作区和暂存区）
git reset --soft "$A"

# 提交（使用用户指定的信息）
git commit -m "$MESSAGE"

echo "✅ 完成。$A..$B 的所有提交已合并为一个新提交。"
echo "如果已经推送到远程，需要使用 git push --force 更新远程分支（谨慎操作）。"
