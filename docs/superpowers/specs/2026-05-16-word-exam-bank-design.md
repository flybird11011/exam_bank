# Word 题库系统设计文档

## 1. 背景

本项目的目标是建立一个考试题库系统，题目来源之一为 Word 文档。系统需要能够识别文档内容，自动拆分为试卷、大题、小题，并对题目自动分类、打标签，同时保留人工审核和修正入口。

以你提供的《2025江苏省苏州市中考真题数学试卷(解析版).docx》为例，文档中同时包含：

- 试卷标题与说明
- 大题结构
- 题干与选项
- 答案与解析
- 图片、表格、公式、嵌入对象

因此，系统不能只存纯文本，而要同时保留结构化内容、富内容块和解析追踪信息。

## 2. 设计目标

### 2.1 核心目标

- 导入 `.docx` Word 文档
- 自动识别试卷结构
- 自动切分题目
- 自动生成基础标签
- 支持人工审核与修正
- 支持题库检索与复用

### 2.2 成功标准

MVP 阶段只要满足以下条件即可认为可用：

- 一份标准 `.docx` 试卷可以导入
- 试卷能够拆成大题和小题
- 选择题答案能够识别
- 图片、表格、公式不会整体丢失
- 审核员可以修正题目并确认入库
- 题库可以按条件检索

## 3. 范围

### 3.1 本期必须实现

- Word 文件上传
- OOXML 解包与解析
- 试卷元信息识别
- 大题识别与小题切分
- 选项、答案、解析识别
- 图片、表格、公式提取
- 自动基础打标
- 审核页面
- 题库检索页
- 解析日志与错误记录

### 3.2 本期暂缓

- 自动组卷
- 智能推荐题目
- 多格式统一导入
- 自训练知识点模型
- 复杂权限体系
- 高级统计报表

## 4. 数据模型

系统采用“关系型主表 + JSON 富内容”的混合设计。

### 4.1 核心实体

- `exam_paper`
- `paper_section`
- `question`
- `question_option`
- `content_block`
- `media_asset`
- `tag`
- `question_tag`
- `parse_run`
- `parse_trace`
- `parse_warning`
- `review_log`

### 4.2 设计原则

- 题目结构使用关系型表，保证检索和统计能力
- 富内容使用 JSON 字段，保留图片、公式、表格等复杂结构
- 标签支持多对多和来源标记
- 所有解析过程都保留追踪信息，便于回溯和修正

## 5. 数据库设计

### 5.1 `exam_paper`

试卷主表，存放整套卷子的基础信息。

关键字段：

- `id`
- `title`
- `subject`
- `region`
- `exam_year`
- `exam_type`
- `source_file_name`
- `source_file_path`
- `total_questions`
- `total_score`
- `duration_minutes`
- `status`
- `meta_json`
- `created_at`
- `updated_at`

### 5.2 `paper_section`

大题表，描述一套试卷中的“选择题 / 填空题 / 解答题”等区块。

关键字段：

- `paper_id`
- `section_no`
- `title`
- `section_type`
- `question_count`
- `total_score`
- `instructions`
- `order_no`
- `meta_json`

### 5.3 `question`

题目主表，存放题干、答案、解析和追踪信息。

关键字段：

- `paper_id`
- `section_id`
- `question_no`
- `question_type`
- `stem_text`
- `stem_json`
- `answer_text`
- `answer_json`
- `analysis_text`
- `analysis_json`
- `difficulty`
- `source_start_para`
- `source_end_para`
- `confidence`
- `status`
- `meta_json`

### 5.4 `question_option`

选择题选项表。

关键字段：

- `question_id`
- `option_label`
- `option_text`
- `option_json`
- `is_correct`
- `order_no`

### 5.5 `content_block`

内容块表，用于承载题干、答案、解析中的富内容。

支持类型：

- `paragraph`
- `image`
- `table`
- `formula`
- `list_item`
- `ocr_text`

### 5.6 `media_asset`

媒体资源表，存储图片、公式截图、表格快照、嵌入对象等。

### 5.7 `tag` 与 `question_tag`

标签表和题目标签关系表。

标签维度建议包括：

- 学科
- 学段 / 年级
- 题型
- 知识点
- 难度
- 特征标签
- 来源标签

`question_tag` 需要保留来源：

- `auto`
- `rule`
- `model`
- `manual`

### 5.8 `parse_run`、`parse_trace`、`parse_warning`

用于记录解析任务、追踪原始 XML 段落、记录警告和错误。

### 5.9 `review_log`

记录人工修改历史，方便审计、回滚和规则优化。

## 6. ER 关系

主要关系如下：

- `exam_paper` 1 对多 `paper_section`
- `paper_section` 1 对多 `question`
- `question` 1 对多 `question_option`
- `question` 1 对多 `content_block`
- `question` 1 对多 `media_asset`
- `question` 多对多 `tag`，通过 `question_tag`
- `exam_paper` 1 对多 `parse_run`
- `parse_run` 1 对多 `parse_trace`
- `question`、`paper_section` 可被 `parse_trace` 追踪
- `question`、`tag` 的修改都应进入 `review_log`

## 7. Word 解析流程

### 7.1 总流程

1. 上传 `.docx`
2. 解包 OOXML
3. 读取 `document.xml` 和 relationships
4. 提取段落、表格、图片、公式
5. 标准化段落
6. 识别试卷元信息
7. 识别大题
8. 切分小题
9. 抽取选项、答案、解析
10. 生成内容块
11. 自动打标签
12. 写入草稿
13. 人工审核
14. 确认入库

### 7.2 大题识别

依据标题段识别：

- `一、选择题`
- `二、填空题`
- `三、解答题`

并映射到 `section_type`。

### 7.3 小题切分

依据题号和关键字识别：

- `^\d+\.`
- `【答案】`
- `【解析】`
- `【分析】`
- `【详解】`

### 7.4 选项切分

选择题选项按：

- `A.`
- `B.`
- `C.`
- `D.`

进行抽取，允许多段合并。

### 7.5 富内容处理

题目中图片、表格、公式不能只作为纯文本保存，必须生成 `content_block` 和 `media_asset`。

## 8. 自动分类与打标

### 8.1 标签维度

- `subject`
- `grade`
- `question_type`
- `knowledge_point`
- `difficulty`
- `feature`
- `source`

### 8.2 打标策略

- 规则层优先识别题型和结构特征
- 模型层补充知识点和难度
- 人工层最终确认

### 8.3 置信度

每个自动标签和题目解析结果都应带置信度，便于审核页高亮风险内容。

## 9. 错误与警告

### 9.1 错误分级

- `info`
- `warning`
- `error`

### 9.2 典型错误码

- `FILE_FORMAT_NOT_SUPPORTED`
- `FILE_CORRUPTED`
- `PARSER_XML_ERROR`
- `QUESTION_BOUNDARY_AMBIGUOUS`
- `QUESTION_NUMBER_SKIP`
- `OPTION_INCOMPLETE`
- `MISSING_ANSWER`
- `IMAGE_MISSING`
- `TABLE_UNPARSED`
- `FORMULA_UNPARSED`
- `VALIDATION_ERROR`

### 9.3 处理策略

- 可继续的错误标记为 `needs_review`
- 结构性错误阻断入库
- 每条警告保存建议动作和追踪信息

## 10. 审核规则

审核顺序建议为：

1. 题目边界
2. 题型
3. 答案
4. 解析
5. 标签
6. 附件

### 审核通过标准

- 题目边界正确
- 题型正确
- 答案正确或可接受
- 解析完整或可接受
- 核心标签正确
- 无严重警告

### 审核动作

- 修改题干
- 修改选项
- 修改答案
- 修改解析
- 修改题型
- 拆分题目
- 合并题目
- 添加标签
- 删除标签
- 确认入库

## 11. 后台页面

### 11.1 试卷导入页

负责上传文件、展示解析进度和解析结果概览。

### 11.2 题目审核页

用于查看、修正和确认题目，建议采用左目录、中内容、右元信息的三栏布局。

### 11.3 题库检索页

支持按学科、年份、地区、题型、知识点、难度、标签等筛选。

### 11.4 标签管理页

用于维护标签树、别名和标签统计。

### 11.5 解析日志页

用于查看解析警告、错误和追踪信息。

### 11.6 题目详情页

展示题干、选项、答案、解析、附件、标签、审核记录和原始追踪信息。

## 12. API 设计

### 12.1 导入与草稿

- `POST /api/papers/import`
- `GET /api/papers/import/{parse_run_id}`
- `POST /api/papers/drafts`
- `PUT /api/papers/drafts/{draft_id}`
- `POST /api/papers/drafts/{draft_id}/confirm`

### 12.2 审核与检索

- `GET /api/questions/review`
- `PATCH /api/questions/{question_id}`
- `GET /api/questions/search`
- `GET /api/papers/{paper_id}`

### 12.3 标签

- `POST /api/questions/{question_id}/tags`
- `DELETE /api/questions/{question_id}/tags/{tag_id}`
- `GET /api/tags`

### 12.4 日志

- `GET /api/parse-runs/{parse_run_id}/warnings`
- `GET /api/review-logs`

## 13. MVP 计划

### Phase 1

- 数据库结构
- Word 解析器
- 试卷导入接口

### Phase 2

- 审核页面
- 题目详情页
- 审核日志

### Phase 3

- 自动打标
- 标签树
- 搜索页

### Phase 4

- 错误与日志系统
- 规则优化
- 回归测试

## 14. 风险与对策

### 14.1 Word 模板不统一

对策：先支持标准 `.docx` 和你当前这类中考真题样式，再逐步扩展规则。

### 14.2 图片和公式丢失

对策：媒体单独入库，公式先可转成图片或保留对象引用。

### 14.3 题目边界切错

对策：保留 `parse_trace`，并让审核页支持拆分、合并和重解析。

### 14.4 标签混乱

对策：先采用标准标签树，同义词映射，限制自由创建。

## 15. 验收标准

### 15.1 导入验收

- 能导入标准 `.docx`
- 能识别大题结构
- 能拆出大部分题目

### 15.2 审核验收

- 能人工修正题目
- 能记录修改日志
- 能确认入库

### 15.3 检索验收

- 能按条件搜索题目
- 能查看题目详情
- 能定位来源试卷

### 15.4 标签验收

- 能自动推荐基础标签
- 能人工修正标签
- 标签来源可追溯

## 16. 结论

这套题库系统的第一版重点不是“全自动”，而是：

- 结构完整
- 可审核
- 可回溯
- 可扩展

只要这四点成立，后续就可以逐步提高自动化程度，扩展到更多学科和更多 Word 模板。
