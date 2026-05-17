# 练习与错题查询设计稿

## 1. 背景

当前项目已经具备 Word 试卷导入、题目审阅、解析展示和题库检索能力，但还缺少“做题练习”和“错题查询”的闭环。用户希望可以：

- 按整张试卷出题
- 按题型配额出题，默认单选 `8`、填空 `8`、解答 `11`
- 支持随机出题
- 支持排除已掌握题目
- 在做题过程中可跳过题目，跳过后视为已掌握
- 维护题目级学习状态
- 提供一个错题查询界面，按“未掌握”和“做错次数”筛选

本设计只覆盖练习与错题查询，不改变现有导入、解析、审阅的主流程。

## 2. 目标

### 2.1 核心目标

- 建立题目级学习状态
- 支持整张试卷的练习会话
- 支持按题型配额抽题
- 支持随机与排除已掌握
- 支持错题查询与回看

### 2.2 成功标准

- 每道题都有独立的掌握状态
- 答对或跳过后，题目自动变为已掌握
- 答错后，题目变为未掌握，且做错次数累加
- 可按条件筛出未掌握题目和做错次数较高的题目
- 默认题型配额为：
  - 单选 `8`
  - 填空 `8`
  - 解答 `11`

## 3. 范围

### 3.1 本期实现

- 题目学习状态
- 作答历史记录
- 练习会话
- 按试卷 + 题型配额出题
- 随机出题
- 排除已掌握题目
- 跳过即已掌握
- 错题查询页
- 基础统计字段展示

### 3.2 暂不实现

- 按知识点自动推荐练习
- 间隔复习算法
- 连续正确次数策略
- 学习曲线图
- 多人共享学习记录

## 4. 术语

- `掌握状态`：题目是否已掌握，布尔值
- `做错次数`：某题累计答错的次数
- `练习会话`：一次完整的出题与答题过程
- `错题查询`：按掌握状态、做错次数筛题的页面

## 5. 数据模型

### 5.1 `question_learning_state`

每道题一条当前状态记录。

字段建议：

- `question_id`
- `mastered`，默认 `false`
- `wrong_count`，默认 `0`
- `last_result`，枚举：`correct` / `wrong` / `skip`
- `last_attempt_at`
- `updated_at`

说明：

- `mastered` 表示当前是否已掌握
- `wrong_count` 只统计答错次数
- `last_result` 用于显示最近一次练习结论

### 5.2 `question_practice_attempt`

每次作答保留一条历史。

字段建议：

- `id`
- `question_id`
- `session_id`
- `result`，枚举：`correct` / `wrong` / `skip`
- `answer_payload`，可选，保存用户作答内容
- `created_at`

说明：

- 这张表是历史事实来源
- 未来如果要做错题回放、练习轨迹、统计报表，会依赖它

### 5.3 `practice_session`

一次练习会话的配置与状态。

字段建议：

- `id`
- `paper_id`
- `mode`，例如 `paper`
- `randomized`
- `exclude_mastered`
- `single_choice_count`
- `fill_blank_count`
- `short_answer_count`
- `status`，`running` / `finished`
- `created_at`
- `updated_at`

说明：

- 练习会话保存本次出题条件
- 出题顺序也可以记录到 `meta_json` 中，或单独关联题目顺序表

### 5.4 可选：`practice_session_question`

如果需要严格保存一次会话的出题顺序，建议增加中间表：

- `session_id`
- `question_id`
- `order_no`

如果本期想先简化，也可以把题目顺序放进 `practice_session.meta_json`。

## 6. 状态规则

### 6.1 题目状态更新规则

- 答对：`mastered = true`
- 跳过：`mastered = true`
- 答错：`mastered = false`，`wrong_count = wrong_count + 1`
- 每次作答都更新 `last_result` 和 `last_attempt_at`

### 6.2 错题定义

错题查询页默认把以下题目视为“可检索对象”：

- `mastered = false`
- `wrong_count > 0`

用户也可以单独用其中一个条件筛选。

## 7. 出题规则

### 7.1 出题输入

出题接口需要支持以下参数：

- `paper_id`
- `randomized`
- `exclude_mastered`
- `single_choice_count`，默认 `8`
- `fill_blank_count`，默认 `8`
- `short_answer_count`，默认 `11`

### 7.2 题型抽取策略

按以下流程生成本次练习题目列表：

1. 读取试卷下的题目
2. 按题型分组
3. 如果开启 `exclude_mastered`，过滤掉已掌握题目
4. 按题型配额截取指定数量
5. 如果开启 `randomized`，仅在过滤后的候选集中打乱顺序
6. 合并题型结果，返回练习列表

### 7.3 数量不足处理

如果某一题型题目数量不足：

- 返回实际可用数量
- 在响应中带上缺口信息
- 前端显示“当前试卷该题型不足”

## 8. 页面设计

### 8.1 练习页

建议新增独立页面，而不是塞进审阅页。

主要区域：

- 试卷选择
- 题型配额输入
- 随机开关
- 排除已掌握开关
- 题目展示区
- 答题操作区

操作按钮：

- `提交正确`
- `提交错误`
- `跳过 / 我会了`
- `上一题`
- `下一题`

展示信息：

- 当前题号
- 当前题型
- 题目状态
- 做错次数
- 练习进度

### 8.2 错题查询页

建议单独页面或练习中心的一个 Tab。

主要筛选：

- `未掌握`
- `做错次数 >= N`

可选增强：

- 试卷筛选
- 题型筛选
- 关键词搜索

结果列表建议展示：

- 题号
- 题型
- 题干摘要
- `mastered` 状态
- `wrong_count`
- 最近一次结果

## 9. 后端接口

### 9.1 练习会话

建议新增接口：

- `POST /api/practice/sessions`
  - 创建练习会话并返回题目列表
- `GET /api/practice/sessions/{session_id}`
  - 查看会话详情

### 9.2 作答提交

建议新增接口：

- `POST /api/practice/attempts`
  - 记录一次作答
  - 更新 `question_learning_state`

### 9.3 错题查询

建议新增接口：

- `GET /api/practice/questions`
  - 按 `mastered`
  - 按 `min_wrong_count`
  - 按 `paper_id`
  - 按题型过滤
- `GET /api/practice/questions/{question_id}`
  - 返回题目详情、当前状态、最近作答历史

## 10. 模块拆分建议

### 10.1 后端

- 新增 `app/services/practice_service.py`
- 新增 `app/api/routes/practice.py`
- 新增数据库模型
- 新增迁移脚本

建议职责：

- `practice_service.py`
  - 生成练习会话
  - 更新学习状态
  - 查询错题
- `review_service.py`
  - 继续只负责审阅编辑，不掺入练习逻辑

### 10.2 前端

- 新增 `PracticePage`
- 新增 `WrongQuestionPage`
- 复用现有题目渲染组件
- 复用现有题干、选项、解析展示逻辑

## 11. 风险与边界

- 如果把“错题”做成独立列表而不是状态视图，后面会很容易和掌握状态打架
- 如果练习会话不保存题目顺序，回看时会不方便定位
- 如果答题历史不保存，后面无法解释“为什么这题已掌握”
- 如果把掌握状态做成试卷级别，会和用户需求冲突，因为你明确要求按单题保存

## 12. 测试建议

### 12.1 后端测试

- 创建会话时，题型配额正确
- 随机开关生效
- 排除已掌握生效
- 答对后 `mastered = true`
- 跳过后 `mastered = true`
- 答错后 `mastered = false` 且 `wrong_count + 1`
- 错题查询过滤正确

### 12.2 前端测试

- 练习页能按默认 `8 / 8 / 11` 出题
- 练习页能切换随机和排除已掌握
- 错题查询页能按未掌握和做错次数筛选
- 跳过按钮能更新题目状态展示

## 13. 推荐实施顺序

1. 数据库模型和迁移
2. 后端练习会话与状态更新
3. 后端错题查询接口
4. 前端练习页
5. 前端错题查询页
6. 补回归测试

