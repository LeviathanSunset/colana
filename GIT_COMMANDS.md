# Git 命令参考手册

## 🚀 基础命令

### 初始化和配置
```bash
# 初始化仓库
git init

# 设置用户信息
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"

# 查看配置
git config --list
```

### 文件操作
```bash
# 查看状态
git status

# 添加文件到暂存区
git add filename.py          # 添加单个文件
git add .                    # 添加所有文件
git add src/                 # 添加整个目录

# 从暂存区移除
git reset filename.py        # 移除单个文件
git reset                    # 移除所有文件

# 提交更改
git commit -m "提交信息"
git commit -am "跳过暂存区直接提交"

# 查看提交历史
git log
git log --oneline           # 简洁版本
git log --graph             # 图形化显示
```

## 🌿 分支操作

```bash
# 查看分支
git branch                  # 查看本地分支
git branch -r               # 查看远程分支
git branch -a               # 查看所有分支

# 创建分支
git branch feature-name     # 创建分支
git checkout -b feature-name # 创建并切换到分支

# 切换分支
git checkout branch-name
git switch branch-name      # Git 2.23+新命令

# 合并分支
git checkout main
git merge feature-name

# 删除分支
git branch -d feature-name  # 删除已合并分支
git branch -D feature-name  # 强制删除分支
```

## 🔄 远程仓库

```bash
# 添加远程仓库
git remote add origin https://github.com/username/repo.git

# 查看远程仓库
git remote -v

# 推送到远程
git push origin main        # 推送main分支
git push -u origin main     # 首次推送并设置上游

# 从远程拉取
git pull origin main        # 拉取并合并
git fetch origin            # 只获取不合并

# 克隆仓库
git clone https://github.com/username/repo.git
```

## 📝 实用技巧

### 查看差异
```bash
git diff                    # 工作区与暂存区差异
git diff --staged           # 暂存区与最后提交差异
git diff HEAD~1             # 与上一次提交差异
```

### 撤销操作
```bash
# 撤销工作区修改
git checkout -- filename.py

# 撤销提交（保留修改）
git reset --soft HEAD~1

# 撤销提交（丢弃修改）
git reset --hard HEAD~1

# 修改最后一次提交
git commit --amend -m "新的提交信息"
```

### 储藏功能
```bash
# 储藏当前修改
git stash

# 查看储藏列表
git stash list

# 应用储藏
git stash apply             # 应用最新储藏
git stash apply stash@{0}   # 应用指定储藏

# 删除储藏
git stash drop
git stash clear             # 清空所有储藏
```

## 🏷️ 标签管理

```bash
# 创建标签
git tag v1.0.0
git tag -a v1.0.0 -m "版本1.0.0"

# 查看标签
git tag
git show v1.0.0

# 推送标签
git push origin v1.0.0
git push origin --tags      # 推送所有标签
```

## 🔍 日常工作流程

### 开发新功能
```bash
1. git checkout -b feature/new-feature
2. # 编写代码
3. git add .
4. git commit -m "添加新功能"
5. git checkout main
6. git merge feature/new-feature
7. git branch -d feature/new-feature
```

### 修复Bug
```bash
1. git checkout -b hotfix/bug-fix
2. # 修复代码
3. git add .
4. git commit -m "修复重要bug"
5. git checkout main
6. git merge hotfix/bug-fix
7. git tag v1.0.1
```

### 部署到服务器
```bash
# 在服务器上
git pull origin main
# 重启服务
```

## ⚠️ 注意事项

1. **提交信息规范**：
   - feat: 新功能
   - fix: 修复bug
   - docs: 文档更新
   - style: 格式修改
   - refactor: 重构
   - test: 测试相关

2. **文件忽略**：
   - 编辑 `.gitignore` 文件
   - 常见忽略：`*.pyc`, `__pycache__/`, `.env`, `config.json`

3. **安全提示**：
   - 永远不要提交密码、API密钥等敏感信息
   - 使用环境变量或配置文件模板
