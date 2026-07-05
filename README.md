# 赔率分析（Streamlit）

这个项目可以部署到 Streamlit Community Cloud，部署后会得到一个可分享链接，朋友打开就能直接用。

## 1. 上传到 GitHub

1. 在 GitHub 新建一个仓库（例如：`odds-analysis`）
2. 在本地项目目录执行：

```bash
git init
git add .
git commit -m "init odds analysis app"
git branch -M main
git remote add origin 你的仓库地址
git push -u origin main
```

## 2. 一键部署到 Streamlit Cloud

1. 打开 https://share.streamlit.io/
2. 用 GitHub 账号登录
3. 点击 `New app`
4. 选择你刚创建的仓库
5. `Main file path` 填：`app.py`
6. 点击 `Deploy`

部署完成后会得到类似：

`https://xxxx.streamlit.app`

这个链接就可以直接发给朋友使用。

## 3. 以后更新代码

每次你 `git push` 到 `main`，云端会自动重新部署。

## 4. 本地运行（可选）

```bash
streamlit run app.py
```

---

当前项目已包含云端部署必需文件：

- `requirements.txt`
- `app.py`
