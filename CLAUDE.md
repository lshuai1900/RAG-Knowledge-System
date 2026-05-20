# 项目背景

这是一个中文论文/文档问答 RAG 系统。

## 当前能力

- 支持上传文档
- 支持文档切分
- 使用阿里 text-embedding-v4 生成向量
- 支持向量检索
- 支持 LLM 根据检索结果回答问题

## 当前配置

- Embedding 模型：text-embedding-v4
- Embedding API Base：https://dashscope.aliyuncs.com/compatible-mode/v1
- 向量维度：1024
- 向量数据库：填写你的数据库，例如 Chroma / FAISS / Milvus
- 后端框架：填写 FastAPI / Flask / Django / Node 等
- 前端框架：填写 Vue / React / Streamlit 等

## 优化目标

优先提升：
1. 检索准确率
2. 回答引用可靠性
3. 幻觉控制
4. 系统响应速度
5. 项目可维护性

## 重要约束

- 不要泄露 API Key
- 不要把密钥写死在代码中
- 所有新增功能需要尽量保持模块化
- 修改前先说明方案
- 每次只改一个明确目标
- 修改后必须说明测试方法